import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import xgboost as xgb
import tensorflow as tf
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q
from .autonomous_models import (
    EmotionEvent, TaskFeedback, RLModel, KnowledgeGraph, 
    AutoConfiguration, UserGoal, WeeklyReport, IndustryTrend
)
from tasks.models import Task, TaskEmotionPattern
import json
import threading
import time

class ReinforcementLearningEngine:
    """RL engine for task optimization and emotional wellbeing"""
    
    def __init__(self, user):
        self.user = user
        self.state_space_size = 50  # Emotional + contextual features
        self.action_space_size = 100  # Maximum possible tasks
        self.learning_rate = 0.001
        self.epsilon = 0.1  # Exploration rate
        self.gamma = 0.95  # Discount factor
        
        # Initialize Q-table or neural network
        self.q_model = self._initialize_q_model()
        self.scaler = StandardScaler()
        
    def _initialize_q_model(self):
        """Initialize the Q-learning model"""
        # Try to load existing model
        try:
            model_record = RLModel.objects.get(user=self.user, model_name='task_optimization')
            if model_record.weights:
                # Load XGBoost model
                model = xgb.XGBRegressor(**model_record.hyperparameters)
                model.load_model(json.dumps(model_record.weights))
                return model
        except RLModel.DoesNotExist:
            pass
        
        # Create new model
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=self.learning_rate,
            objective='reg:squarederror'
        )
        
        # Save initial model
        RLModel.objects.update_or_create(
            user=self.user,
            model_name='task_optimization',
            defaults={
                'hyperparameters': model.get_params(),
                'weights': {},
                'model_version': 1
            }
        )
        
        return model
    
    def get_state_vector(self, user):
        """Convert current state to feature vector"""
        # Get recent emotion events
        recent_emotions = EmotionEvent.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).order_by('-timestamp')[:10]
        
        # Get current task context
        current_tasks = Task.objects.filter(user=user, status='pending')
        
        # Get time features
        now = timezone.now()
        time_features = [
            now.hour / 24.0,
            now.weekday() / 6.0,
            (now.date() - user.date_joined).days / 365.0
        ]
        
        # Emotion features
        emotion_features = []
        emotion_counts = {}
        for event in recent_emotions:
            emotion_counts[event.emotion] = emotion_counts.get(event.emotion, 0) + 1
        
        # Normalize emotion counts
        total_emotions = sum(emotion_counts.values())
        if total_emotions > 0:
            for emotion in ['happy', 'sad', 'angry', 'focused', 'stressed', 'calm', 'neutral']:
                emotion_features.append(emotion_counts.get(emotion, 0) / total_emotions)
        else:
            emotion_features.extend([0.0] * 7)
        
        # Task features
        task_features = [
            current_tasks.count(),
            current_tasks.filter(priority='high').count(),
            current_tasks.filter(priority='medium').count(),
            current_tasks.filter(priority='low').count(),
        ]
        
        # Performance features
        recent_feedback = TaskFeedback.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).aggregate(
            avg_satisfaction=Avg('task_satisfaction'),
            avg_reward=Avg('reward_score')
        )
        
        performance_features = [
            recent_feedback['avg_satisfaction'] or 3.0,
            recent_feedback['avg_reward'] or 0.0,
        ]
        
        # Combine all features
        state_vector = time_features + emotion_features + task_features + performance_features
        
        # Pad to fixed size
        while len(state_vector) < self.state_space_size:
            state_vector.append(0.0)
        
        return np.array(state_vector[:self.state_space_size])
    
    def predict_q_values(self, state, available_tasks):
        """Predict Q-values for available tasks"""
        q_values = []
        
        for task in available_tasks:
            # Create task-specific features
            task_features = self._get_task_features(task)
            
            # Combine state and task features
            combined_features = np.concatenate([state, task_features])
            
            # Predict Q-value
            try:
                q_value = self.q_model.predict(combined_features.reshape(1, -1))[0]
            except:
                q_value = 0.0  # Default if model fails
            
            q_values.append(q_value)
        
        return np.array(q_values)
    
    def _get_task_features(self, task):
        """Extract features from a task"""
        features = []
        
        # Priority encoding
        priority_map = {'low': 0.0, 'medium': 0.5, 'high': 1.0}
        features.append(priority_map.get(task.priority, 0.5))
        
        # Due date urgency
        if task.due_date:
            hours_until_due = (task.due_date - timezone.now()).total_seconds() / 3600
            urgency = max(0.0, 1.0 - (hours_until_due / 168.0))  # Normalize to week
        else:
            urgency = 0.0
        features.append(urgency)
        
        # Task type (one-hot encoded)
        task_types = ['writing', 'coding', 'meeting', 'learning', 'creative', 'analytical', 'administrative']
        task_type = self._classify_task_type(task.title)
        for ttype in task_types:
            features.append(1.0 if ttype == task_type else 0.0)
        
        # Emotional requirements
        required_emotions = list(task.required_emotions.all().values_list('name', flat=True))
        emotion_types = ['focused', 'calm', 'creative', 'analytical', 'social']
        for emotion in emotion_types:
            features.append(1.0 if emotion in required_emotions else 0.0)
        
        # Pad to fixed size
        while len(features) < 20:  # Target task feature size
            features.append(0.0)
        
        return np.array(features[:20])
    
    def _classify_task_type(self, title):
        """Classify task type from title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['write', 'report', 'document', 'email']):
            return 'writing'
        elif any(word in title_lower for word in ['code', 'program', 'develop', 'debug']):
            return 'coding'
        elif any(word in title_lower for word in ['meeting', 'call', 'presentation']):
            return 'meeting'
        elif any(word in title_lower for word in ['learn', 'study', 'read', 'research']):
            return 'learning'
        elif any(word in title_lower for word in ['design', 'create', 'brainstorm']):
            return 'creative'
        elif any(word in title_lower for word in ['analyze', 'review', 'data', 'metrics']):
            return 'analytical'
        else:
            return 'administrative'
    
    def select_action(self, state, available_tasks, training=True):
        """Select best task using epsilon-greedy policy"""
        if training and np.random.random() < self.epsilon:
            # Explore: random selection
            return np.random.choice(len(available_tasks))
        else:
            # Exploit: best Q-value
            q_values = self.predict_q_values(state, available_tasks)
            return np.argmax(q_values)
    
    def update_model(self, state, action, reward, next_state, available_tasks):
        """Update Q-learning model"""
        # Get current Q-value
        current_features = np.concatenate([state, self._get_task_features(available_tasks[action])])
        current_q = self.q_model.predict(current_features.reshape(1, -1))[0]
        
        # Get max Q-value for next state
        if len(available_tasks) > 0:
            next_q_values = self.predict_q_values(next_state, available_tasks)
            max_next_q = np.max(next_q_values)
        else:
            max_next_q = 0.0
        
        # Calculate target Q-value
        target_q = reward + self.gamma * max_next_q
        
        # Update model (simplified - in practice would use proper training)
        training_data = {
            'features': current_features.tolist(),
            'target': target_q
        }
        
        # Store for batch training
        self._store_training_data(training_data)
    
    def _store_training_data(self, data):
        """Store training data for batch updates"""
        # This would typically be stored in a more efficient format
        # For now, we'll trigger immediate training
        self._batch_train([data])
    
    def _batch_train(self, training_data):
        """Perform batch training on the model"""
        if len(training_data) < 5:  # Minimum batch size
            return
        
        # Prepare training data
        X = np.array([item['features'] for item in training_data])
        y = np.array([item['target'] for item in training_data])
        
        # Train model
        self.q_model.fit(X, y)
        
        # Update model record
        model_record, created = RLModel.objects.get_or_create(
            user=self.user,
            model_name='task_optimization',
            defaults={
                'hyperparameters': self.q_model.get_params(),
                'model_version': 1
            }
        )
        
        if not created:
            model_record.episodes_trained += len(training_data)
            model_record.training_data_points += len(training_data)
            model_record.save()
    
    def calculate_reward(self, task_feedback):
        """Calculate reward signal from task feedback"""
        # Base reward from task satisfaction
        satisfaction_reward = (task_feedback.task_satisfaction - 3) * 0.2  # Centered at 0
        
        # Emotion improvement reward
        emotion_reward = task_feedback.emotion_change_rating * 0.3
        
        # Efficiency reward (faster completion = higher reward)
        avg_completion_time = TaskFeedback.objects.filter(
            user=self.user,
            task__title__icontains=self._classify_task_type(task_feedback.task.title)
        ).aggregate(avg_time=Avg('completion_time_minutes'))['avg_time'] or 60
        
        efficiency_reward = max(0, (avg_completion_time - task_feedback.completion_time_minutes) / avg_completion_time) * 0.2
        
        # Focus level reward
        focus_reward = (task_feedback.focus_level - 3) * 0.1
        
        # AI helpfulness reward
        ai_reward = (task_feedback.ai_helpfulness - 3) * 0.1
        
        # Total reward
        total_reward = satisfaction_reward + emotion_reward + efficiency_reward + focus_reward + ai_reward
        
        # Update feedback record
        task_feedback.reward_score = total_reward
        task_feedback.save()
        
        return total_reward

class AutonomousLearningManager:
    """Manages all autonomous learning processes"""
    
    def __init__(self):
        self.rl_engines = {}  # User-specific RL engines
        self.is_running = False
        self.learning_thread = None
        
    def start_learning(self):
        """Start autonomous learning processes"""
        if self.is_running:
            return
            
        self.is_running = True
        self.learning_thread = threading.Thread(target=self._learning_loop)
        self.learning_thread.daemon = True
        self.learning_thread.start()
    
    def stop_learning(self):
        """Stop autonomous learning processes"""
        self.is_running = False
        if self.learning_thread:
            self.learning_thread.join(timeout=5)
    
    def _learning_loop(self):
        """Main learning loop"""
        while self.is_running:
            try:
                # Process user feedback
                self._process_feedback_learning()
                
                # Update knowledge graphs
                self._update_knowledge_graphs()
                
                # Auto-configure parameters
                self._auto_configure_systems()
                
                # Generate weekly reports
                self._generate_weekly_reports()
                
                # Update industry trends
                self._update_industry_trends()
                
                # Sleep for 1 hour between cycles
                time.sleep(3600)
                
            except Exception as e:
                print(f"Learning loop error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _process_feedback_learning(self):
        """Process user feedback for RL training"""
        # Get unprocessed feedback
        unprocessed_feedback = TaskFeedback.objects.filter(reward_score=0.0)
        
        for feedback in unprocessed_feedback:
            user = feedback.user
            
            # Get or create RL engine for user
            if user.id not in self.rl_engines:
                self.rl_engines[user.id] = ReinforcementLearningEngine(user)
            
            rl_engine = self.rl_engines[user.id]
            
            # Calculate reward
            reward = rl_engine.calculate_reward(feedback)
            
            # Get state before and after task
            # This is simplified - in practice would need more sophisticated state tracking
            print(f"Processed feedback for {user.username}: reward={reward:.2f}")
    
    def _update_knowledge_graphs(self):
        """Update personal knowledge graphs"""
        users = User.objects.all()
        
        for user in users:
            try:
                # Update emotion-task relationships
                self._update_emotion_task_graph(user)
                
                # Update time-based patterns
                self._update_time_patterns(user)
                
                # Update performance correlations
                self._update_performance_graph(user)
                
            except Exception as e:
                print(f"Knowledge graph update error for {user.username}: {e}")
    
    def _update_emotion_task_graph(self, user):
        """Update emotion-task relationship graph"""
        # Get recent emotion-task correlations
        recent_events = EmotionEvent.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).select_related('current_task')
        
        # Build correlation matrix
        emotion_task_matrix = {}
        
        for event in recent_events:
            if event.current_task:
                task_type = self._classify_task_type(event.current_task.title)
                emotion = event.emotion
                
                key = f"{emotion}_{task_type}"
                if key not in emotion_task_matrix:
                    emotion_task_matrix[key] = {'count': 0, 'total_confidence': 0}
                
                emotion_task_matrix[key]['count'] += 1
                emotion_task_matrix[key]['total_confidence'] += event.confidence
        
        # Update knowledge graph
        for key, data in emotion_task_matrix.items():
            emotion, task_type = key.split('_', 1)
            avg_confidence = data['total_confidence'] / data['count']
            
            # Update or create graph node
            KnowledgeGraph.objects.update_or_create(
                user=user,
                entity_type='emotion_task',
                entity_name=key,
                defaults={
                    'success_rate': avg_confidence,
                    'data_points_count': data['count']
                }
            )
    
    def _classify_task_type(self, title):
        """Helper method to classify task type"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['write', 'report', 'document']):
            return 'writing'
        elif any(word in title_lower for word in ['code', 'program', 'develop']):
            return 'coding'
        elif any(word in title_lower for word in ['meeting', 'call']):
            return 'meeting'
        elif any(word in title_lower for word in ['learn', 'study', 'read']):
            return 'learning'
        else:
            return 'general'
    
    def _update_time_patterns(self, user):
        """Update time-based emotion patterns"""
        # Get emotion patterns by hour
        emotions_by_hour = {}
        
        recent_events = EmotionEvent.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=30)
        )
        
        for event in recent_events:
            hour = event.timestamp.hour
            emotion = event.emotion
            
            if hour not in emotions_by_hour:
                emotions_by_hour[hour] = {}
            
            if emotion not in emotions_by_hour[hour]:
                emotions_by_hour[hour][emotion] = 0
            
            emotions_by_hour[hour][emotion] += 1
        
        # Update knowledge graph with time patterns
        for hour, emotions in emotions_by_hour.items():
            dominant_emotion = max(emotions, key=emotions.get)
            
            KnowledgeGraph.objects.update_or_create(
                user=user,
                entity_type='time_pattern',
                entity_name=f"hour_{hour}",
                defaults={
                    'related_entities': [dominant_emotion],
                    'relationship_strength': {dominant_emotion: emotions[dominant_emotion]},
                    'data_points_count': sum(emotions.values())
                }
            )
    
    def _update_performance_graph(self, user):
        """Update performance correlation graph"""
        # Get task completion performance by emotion
        feedback_data = TaskFeedback.objects.filter(user=user)
        
        performance_by_emotion = {}
        
        for feedback in feedback_data:
            emotion = feedback.emotion_before
            performance = feedback.task_satisfaction
            
            if emotion not in performance_by_emotion:
                performance_by_emotion[emotion] = []
            
            performance_by_emotion[emotion].append(performance)
        
        # Update knowledge graph
        for emotion, performances in performance_by_emotion.items():
            avg_performance = np.mean(performances)
            
            KnowledgeGraph.objects.update_or_create(
                user=user,
                entity_type='performance',
                entity_name=f"emotion_{emotion}",
                defaults={
                    'success_rate': avg_performance / 5.0,  # Normalize to 0-1
                    'data_points_count': len(performances)
                }
            )
    
    def _auto_configure_systems(self):
        """Automatically configure system parameters"""
        users = User.objects.all()
        
        for user in users:
            try:
                # Auto-tune ML model parameters
                self._auto_tune_ml_params(user)
                
                # Auto-adjust UI preferences
                self._auto_adjust_ui(user)
                
                # Optimize scheduler thresholds
                self._optimize_scheduler(user)
                
            except Exception as e:
                print(f"Auto-configuration error for {user.username}: {e}")
    
    def _auto_tune_ml_params(self, user):
        """Auto-tune machine learning parameters"""
        # Get recent model performance
        recent_feedback = TaskFeedback.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).aggregate(
            avg_reward=Avg('reward_score'),
            feedback_count=Count('id')
        )
        
        if recent_feedback['feedback_count'] < 10:
            return  # Not enough data
        
        avg_reward = recent_feedback['avg_reward']
        
        # Adjust learning rate based on performance
        if avg_reward > 0.5:
            # Good performance - can reduce learning rate
            new_lr = 0.001
        elif avg_reward < 0.0:
            # Poor performance - increase learning rate
            new_lr = 0.01
        else:
            # Neutral performance - keep current
            new_lr = 0.005
        
        # Update configuration
        AutoConfiguration.objects.update_or_create(
            user=user,
            category='ml_model',
            parameter_name='learning_rate',
            defaults={
                'parameter_value': {'value': new_lr},
                'adjustment_reason': f'Auto-tuned based on avg reward: {avg_reward:.3f}',
                'performance_impact': avg_reward
            }
        )
    
    def _auto_adjust_ui(self, user):
        """Auto-adjust UI based on user preferences"""
        # Get AI message feedback
        ai_feedback = TaskFeedback.objects.filter(user=user).aggregate(
            avg_helpfulness=Avg('ai_helpfulness'),
            preferred_tone_count=Count('ai_tone_preference')
        )
        
        if ai_feedback['avg_helpfulness']:
            # Adjust AI tone based on feedback
            preferred_tones = TaskFeedback.objects.filter(user=user).values('ai_tone_preference').annotate(
                count=Count('ai_tone_preference')
            ).order_by('-count').first()
            
            if preferred_tones:
                AutoConfiguration.objects.update_or_create(
                    user=user,
                    category='ui_theme',
                    parameter_name='ai_tone',
                    defaults={
                        'parameter_value': {'tone': preferred_tones['ai_tone_preference']},
                        'adjustment_reason': f'Most preferred tone: {preferred_tones["ai_tone_preference"]}',
                        'performance_impact': ai_feedback['avg_helpfulness'] / 5.0
                    }
                )
    
    def _optimize_scheduler(self, user):
        """Optimize task scheduler thresholds"""
        # Get task completion patterns
        completed_tasks = TaskFeedback.objects.filter(user=user, task_satisfaction__gte=4)
        
        if completed_tasks.count() < 5:
            return
        
        # Analyze optimal task scheduling
        optimal_emotions = completed_tasks.values('emotion_before').annotate(
            count=Count('emotion_before')
        ).order_by('-count')
        
        # Update scheduler configuration
        if optimal_emotions:
            best_emotion = optimal_emotions.first()['emotion_before']
            
            AutoConfiguration.objects.update_or_create(
                user=user,
                category='scheduler',
                parameter_name='optimal_emotion_threshold',
                defaults={
                    'parameter_value': {'emotion': best_emotion, 'priority_boost': 1.2},
                    'adjustment_reason': f'Best performance emotion: {best_emotion}',
                    'performance_impact': optimal_emotions.first()['count'] / completed_tasks.count()
                }
            )
    
    def _generate_weekly_reports(self):
        """Generate AI-powered weekly reports"""
        # Get users who need reports (haven't received one this week)
        last_week = timezone.now() - timedelta(days=7)
        
        users = User.objects.annotate(
            latest_report=Max('weeklyreport__week_start')
        ).filter(
            Q(latest_report__lt=last_week) | Q(latest_report__isnull=True)
        )
        
        for user in users:
            try:
                self._generate_user_weekly_report(user)
            except Exception as e:
                print(f"Weekly report generation error for {user.username}: {e}")
    
    def _generate_user_weekly_report(self, user):
        """Generate weekly report for a specific user"""
        # Get week's data
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
        week_end = week_start + timedelta(days=6)
        
        # Emotion patterns
        emotion_events = EmotionEvent.objects.filter(
            user=user,
            timestamp__date__gte=week_start,
            timestamp__date__lte=week_end
        )
        
        emotion_counts = {}
        for event in emotion_events:
            emotion_counts[event.emotion] = emotion_counts.get(event.emotion, 0) + 1
        
        # Task performance
        completed_tasks = TaskFeedback.objects.filter(
            user=user,
            timestamp__date__gte=week_start,
            timestamp__date__lte=week_end
        )
        
        # Generate AI summary
        summary = self._generate_ai_summary(user, emotion_counts, completed_tasks)
        
        # Create report
        WeeklyReport.objects.update_or_create(
            user=user,
            week_start=week_start,
            defaults={
                'week_end': week_end,
                'summary_highlights': list(emotion_counts.keys())[:5],
                'emotion_patterns': emotion_counts,
                'productivity_insights': {
                    'tasks_completed': completed_tasks.count(),
                    'avg_satisfaction': completed_tasks.aggregate(avg=Avg('task_satisfaction'))['avg'] or 0,
                    'avg_reward': completed_tasks.aggregate(avg=Avg('reward_score'))['avg'] or 0
                },
                'ai_summary': summary,
                'recommendations': self._generate_recommendations(user, emotion_counts, completed_tasks)
            }
        )
    
    def _generate_ai_summary(self, user, emotion_counts, completed_tasks):
        """Generate AI-powered summary using OpenAI"""
        try:
            from emotion_detection.empathy_engine import empathy_engine
            
            # Create prompt for summary generation
            prompt = f"""
            Generate a weekly productivity and emotional wellbeing summary for a user.
            
            Emotion patterns this week: {emotion_counts}
            Tasks completed: {completed_tasks.count()}
            Average satisfaction: {completed_tasks.aggregate(avg=Avg('task_satisfaction'))['avg'] or 0:.1f}/5
            
            Please provide:
            1. A brief overview of their emotional patterns
            2. Key productivity insights
            3. 2-3 personalized recommendations for next week
            
            Keep it encouraging and actionable, under 150 words.
            """
            
            # Use empathy engine to generate summary
            summary = empathy_engine.generate_empathetic_message(
                'neutral', 
                context=prompt
            )
            
            return summary
            
        except Exception as e:
            print(f"AI summary generation error: {e}")
            return "This week showed interesting patterns in your emotional wellbeing and productivity. Continue focusing on tasks that match your emotional state for better results."
    
    def _generate_recommendations(self, user, emotion_counts, completed_tasks):
        """Generate personalized recommendations"""
        recommendations = []
        
        # Analyze most common emotion
        if emotion_counts:
            most_common_emotion = max(emotion_counts, key=emotion_counts.get)
            
            if most_common_emotion == 'stressed':
                recommendations.append("Consider incorporating more breaks and stress management techniques")
            elif most_common_emotion == 'focused':
                recommendations.append("Leverage your focus periods for complex, important tasks")
            elif most_common_emotion == 'calm':
                recommendations.append("Your calm state is ideal for planning and creative work")
        
        # Analyze task satisfaction
        avg_satisfaction = completed_tasks.aggregate(avg=Avg('task_satisfaction'))['avg'] or 0
        if avg_satisfaction < 3.5:
            recommendations.append("Review your task selection and consider matching tasks better to your emotional state")
        
        return recommendations
    
    def _update_industry_trends(self):
        """Update industry-wide trends"""
        # This would aggregate anonymized data across users
        # For now, create some sample trends
        industries = ['Technology', 'Healthcare', 'Education', 'Finance']
        
        for industry in industries:
            # Peak focus time trend
            IndustryTrend.objects.update_or_create(
                industry=industry,
                trend_type='peak_focus_time',
                defaults={
                    'pattern_data': {'peak_hour': 10, 'focus_duration': 120},
                    'confidence_level': 0.85,
                    'sample_size': 1000,
                    'optimization_hints': ['Schedule important tasks between 9-11 AM']
                }
            )
            
            # Productivity pattern
            IndustryTrend.objects.update_or_create(
                industry=industry,
                trend_type='productivity_pattern',
                defaults={
                    'pattern_data': {'most_productive_day': 'Tuesday', 'least_productive_day': 'Friday'},
                    'confidence_level': 0.78,
                    'sample_size': 800,
                    'optimization_hints': ['Plan heavy work for mid-week']
                }
            )

# Global learning manager instance
learning_manager = AutonomousLearningManager()
