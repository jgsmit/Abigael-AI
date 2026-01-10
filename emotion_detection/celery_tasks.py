from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import json

# Configure Celery
app = Celery('emofocus')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def train_rl_models(self):
    """Background task for training reinforcement learning models"""
    from .autonomous_models import RLModel, TaskFeedback, EmotionEvent
    from .autonomous_learning import ReinforcementLearningEngine
    from django.contrib.auth.models import User
    
    users = User.objects.all()
    
    for user in users:
        try:
            # Get user's RL engine
            rl_engine = ReinforcementLearningEngine(user)
            
            # Collect training data
            feedback_data = TaskFeedback.objects.filter(
                user=user,
                reward_score__isnull=False
            ).order_by('-timestamp')[:100]
            
            if len(feedback_data) < 10:
                continue  # Not enough data for training
            
            # Prepare training dataset
            X_train = []
            y_train = []
            
            for feedback in feedback_data:
                # Get state before task
                state = rl_engine.get_state_vector(user)
                
                # Get task features
                task_features = rl_engine._get_task_features(feedback.task)
                
                # Combine features
                combined_features = np.concatenate([state, task_features])
                X_train.append(combined_features)
                y_train.append(feedback.reward_score)
            
            # Train model
            if len(X_train) > 5:
                X_train = np.array(X_train)
                y_train = np.array(y_train)
                
                # Split data
                X_split, X_val, y_split, y_val = train_test_split(X_train, y_train, test_size=0.2)
                
                # Train model
                rl_engine.q_model.fit(X_split, y_split)
                
                # Evaluate
                y_pred = rl_engine.q_model.predict(X_val)
                mse = mean_squared_error(y_val, y_pred)
                
                # Update model record
                model_record, created = RLModel.objects.get_or_create(
                    user=user,
                    model_name='task_optimization',
                    defaults={
                        'hyperparameters': rl_engine.q_model.get_params(),
                        'accuracy': 1.0 - mse,  # Convert MSE to accuracy-like score
                        'episodes_trained': len(feedback_data),
                        'training_data_points': len(X_train)
                    }
                )
                
                if not created:
                    model_record.accuracy = 1.0 - mse
                    model_record.episodes_trained += len(feedback_data)
                    model_record.training_data_points += len(X_train)
                    model_record.save()
                
                print(f"Trained RL model for {user.username}: MSE={mse:.4f}")
        
        except Exception as e:
            print(f"RL training error for {user.username}: {e}")

@app.task(bind=True)
def update_emotion_prediction_models(self):
    """Update emotion prediction models with new data"""
    from .autonomous_models import EmotionEvent, RLModel
    from django.contrib.auth.models import User
    
    users = User.objects.all()
    
    for user in users:
        try:
            # Get recent emotion events
            events = EmotionEvent.objects.filter(
                user=user,
                timestamp__gte=timezone.now() - timedelta(days=7)
            )
            
            if events.count() < 20:
                continue
            
            # Prepare training data
            features = []
            labels = []
            
            for event in events:
                # Extract features from raw data
                feature_vector = []
                
                # Time-based features
                feature_vector.extend([
                    event.timestamp.hour / 24.0,
                    event.timestamp.weekday() / 6.0,
                ])
                
                # Source-specific features
                if event.source == 'facial':
                    facial_data = event.raw_features.get('facial', {})
                    feature_vector.extend([
                        facial_data.get('confidence', 0.0),
                        facial_data.get('brightness', 0.5),
                        facial_data.get('contrast', 0.5),
                    ])
                elif event.source == 'voice':
                    voice_data = event.raw_features.get('voice', {})
                    feature_vector.extend([
                        voice_data.get('pitch_mean', 0.0),
                        voice_data.get('energy', 0.0),
                        voice_data.get('tempo', 0.0),
                    ])
                elif event.source == 'typing':
                    typing_data = event.raw_features.get('typing', {})
                    feature_vector.extend([
                        typing_data.get('typing_speed', 0.0),
                        typing_data.get('rhythm_variance', 0.0),
                        typing_data.get('press_duration', 0.0),
                    ])
                
                # Pad to fixed size
                while len(feature_vector) < 10:
                    feature_vector.append(0.0)
                
                features.append(feature_vector[:10])
                labels.append(event.emotion)
            
            # Train emotion prediction model
            if len(features) > 10:
                from sklearn.preprocessing import LabelEncoder
                from sklearn.ensemble import RandomForestClassifier
                
                # Encode labels
                le = LabelEncoder()
                encoded_labels = le.fit_transform(labels)
                
                # Train model
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(features, encoded_labels)
                
                # Calculate accuracy
                accuracy = model.score(features, encoded_labels)
                
                # Save model
                model_record, created = RLModel.objects.get_or_create(
                    user=user,
                    model_name='emotion_prediction',
                    defaults={
                        'hyperparameters': model.get_params(),
                        'accuracy': accuracy,
                        'training_data_points': len(features)
                    }
                )
                
                if not created:
                    model_record.accuracy = accuracy
                    model_record.training_data_points += len(features)
                    model_record.save()
                
                print(f"Updated emotion model for {user.username}: accuracy={accuracy:.3f}")
        
        except Exception as e:
            print(f"Emotion model update error for {user.username}: {e}")

@app.task(bind=True)
def federated_learning_aggregation(self):
    """Aggregate federated learning updates"""
    from .autonomous_models import FederatedModelUpdate, FederatedLearningNode, RLModel
    from django.contrib.auth.models import User
    
    # Get pending updates
    pending_updates = FederatedModelUpdate.objects.filter(is_accepted=False)
    
    if pending_updates.count() < 3:
        return  # Need minimum updates for aggregation
    
    # Group updates by model name
    model_updates = {}
    for update in pending_updates:
        if update.model_name not in model_updates:
            model_updates[update.model_name] = []
        model_updates[update.model_name].append(update)
    
    # Aggregate updates for each model
    for model_name, updates in model_updates.items():
        try:
            # Simple federated averaging
            aggregated_weights = {}
            total_weight = 0
            
            for update in updates:
                weight = update.contribution_size
                update_weights = update.weight_updates
                
                for key, value in update_weights.items():
                    if key not in aggregated_weights:
                        aggregated_weights[key] = 0
                    aggregated_weights[key] += value * weight
                
                total_weight += weight
            
            # Normalize weights
            if total_weight > 0:
                for key in aggregated_weights:
                    aggregated_weights[key] /= total_weight
            
            # Create global model update
            global_update = FederatedModelUpdate.objects.create(
                node=FederatedLearningNode.objects.get_or_create(
                    node_id='global_aggregator',
                    defaults={'organization': 'Global'}
                )[0],
                model_name=model_name,
                weight_updates=aggregated_weights,
                contribution_size=sum(u.contribution_size for u in updates),
                quality_score=np.mean([u.quality_score for u in updates]),
                is_accepted=True
            )
            
            # Mark individual updates as processed
            updates.update(is_accepted=True)
            
            print(f"Aggregated {len(updates)} updates for model {model_name}")
        
        except Exception as e:
            print(f"Federated aggregation error for {model_name}: {e}")

@app.task(bind=True)
def auto_hyperparameter_tuning(self):
    """Automatically tune hyperparameters based on performance"""
    from .autonomous_models import RLModel, AutoConfiguration
    from django.contrib.auth.models import User
    from sklearn.model_selection import GridSearchCV
    import xgboost as xgb
    
    users = User.objects.all()
    
    for user in users:
        try:
            # Get current model
            model_record = RLModel.objects.filter(
                user=user,
                model_name='task_optimization',
                is_active=True
            ).first()
            
            if not model_record or model_record.training_data_points < 50:
                continue
            
            # Check if performance is declining
            recent_accuracy = model_record.accuracy
            if recent_accuracy > 0.7:
                continue  # Good performance, no tuning needed
            
            # Get training data
            from .autonomous_learning import ReinforcementLearningEngine
            rl_engine = ReinforcementLearningEngine(user)
            
            # Collect training data
            feedback_data = TaskFeedback.objects.filter(
                user=user,
                reward_score__isnull=False
            ).order_by('-timestamp')[:100]
            
            if len(feedback_data) < 20:
                continue
            
            # Prepare dataset
            X_train = []
            y_train = []
            
            for feedback in feedback_data:
                state = rl_engine.get_state_vector(user)
                task_features = rl_engine._get_task_features(feedback.task)
                combined_features = np.concatenate([state, task_features])
                X_train.append(combined_features)
                y_train.append(feedback.reward_score)
            
            X_train = np.array(X_train)
            y_train = np.array(y_train)
            
            # Define parameter grid
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2],
                'subsample': [0.8, 0.9, 1.0]
            }
            
            # Perform grid search
            xgb_model = xgb.XGBRegressor(objective='reg:squarederror')
            grid_search = GridSearchCV(
                estimator=xgb_model,
                param_grid=param_grid,
                cv=3,
                scoring='neg_mean_squared_error',
                n_jobs=-1
            )
            
            grid_search.fit(X_train, y_train)
            
            # Get best parameters
            best_params = grid_search.best_params_
            best_score = -grid_search.best_score_
            
            # Update model with new parameters
            new_model = xgb.XGBRegressor(**best_params, objective='reg:squarederror')
            new_model.fit(X_train, y_train)
            
            # Update model record
            model_record.hyperparameters = best_params
            model_record.accuracy = 1.0 - best_score  # Convert MSE to accuracy
            model_record.model_version += 1
            model_record.save()
            
            # Store configuration
            AutoConfiguration.objects.update_or_create(
                user=user,
                category='ml_model',
                parameter_name='xgb_params',
                defaults={
                    'parameter_value': best_params,
                    'adjustment_reason': f'Auto-tuned via grid search, new accuracy: {1.0 - best_score:.3f}',
                    'performance_impact': (1.0 - best_score) - recent_accuracy
                }
            )
            
            print(f"Auto-tuned hyperparameters for {user.username}: new accuracy={1.0 - best_score:.3f}")
        
        except Exception as e:
            print(f"Hyperparameter tuning error for {user.username}: {e}")

@app.task(bind=True)
def generate_goal_recommendations(self):
    """Generate long-term goal recommendations"""
    from .autonomous_models import UserGoal, KnowledgeGraph
    from django.contrib.auth.models import User
    from datetime import date, timedelta
    
    users = User.objects.all()
    
    for user in users:
        try:
            # Get user's knowledge graph data
            performance_data = KnowledgeGraph.objects.filter(
                user=user,
                entity_type='performance'
            )
            
            # Get task completion patterns
            from tasks.models import Task, TaskEmotionPattern
            patterns = TaskEmotionPattern.objects.filter(user=user)
            
            if patterns.count() < 5:
                continue
            
            # Analyze patterns to predict goals
            best_performing_emotions = performance_data.filter(
                success_rate__gt=0.7
            ).order_by('-success_rate')[:3]
            
            # Generate goal recommendations based on patterns
            goals = []
            
            # Career goals based on performance patterns
            if patterns.filter(task_type='coding', completion_rate__gt=0.8).exists():
                goals.append({
                    'title': 'Master Advanced Programming Skills',
                    'category': 'career',
                    'description': 'Based on your high performance in coding tasks, consider advancing your programming expertise',
                    'target_months': 6,
                    'confidence': 0.8
                })
            
            # Learning goals based on emotional patterns
            if best_performing_emotions.filter(entity_name__contains='focused').exists():
                goals.append({
                    'title': 'Develop Deep Work Habits',
                    'category': 'learning',
                    'description': 'Your focused state leads to high productivity - cultivate this skill systematically',
                    'target_months': 3,
                    'confidence': 0.75
                })
            
            # Health goals based on stress patterns
            stress_patterns = performance_data.filter(entity_name__contains='stressed')
            if stress_patterns.exists() and stress_patterns.aggregate(avg=Avg('success_rate'))['avg'] < 0.5:
                goals.append({
                    'title': 'Implement Stress Management Routine',
                    'category': 'health',
                    'description': 'Your performance suffers under stress - develop coping mechanisms',
                    'target_months': 2,
                    'confidence': 0.85
                })
            
            # Productivity goals
            avg_completion_rate = patterns.aggregate(avg=Avg('completion_rate'))['avg'] or 0
            if avg_completion_rate > 0.7:
                goals.append({
                    'title': 'Optimize Task Management System',
                    'category': 'productivity',
                    'description': 'Build on your strong task completion patterns with advanced productivity techniques',
                    'target_months': 4,
                    'confidence': 0.7
                })
            
            # Create goal records
            for goal_data in goals:
                target_date = date.today() + timedelta(days=goal_data['target_months'] * 30)
                
                UserGoal.objects.update_or_create(
                    user=user,
                    goal_title=goal_data['title'],
                    defaults={
                        'goal_description': goal_data['description'],
                        'goal_category': goal_data['category'],
                        'target_date': target_date,
                        'prediction_confidence': goal_data['confidence'],
                        'prediction_basis': {
                            'performance_patterns': len(performance_data),
                            'task_patterns': len(patterns),
                            'avg_completion_rate': avg_completion_rate
                        }
                    }
                )
            
            print(f"Generated {len(goals)} goal recommendations for {user.username}")
        
        except Exception as e:
            print(f"Goal recommendation error for {user.username}: {e}")

@app.task(bind=True)
def cleanup_old_data(self):
    """Clean up old data to maintain system performance"""
    from .autonomous_models import EmotionEvent, TaskFeedback
    from django.utils import timezone
    
    # Delete emotion events older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_events = EmotionEvent.objects.filter(timestamp__lt=cutoff_date).delete()[0]
    
    # Archive old feedback (keep for 1 year)
    feedback_cutoff = timezone.now() - timedelta(days=365)
    archived_feedback = TaskFeedback.objects.filter(timestamp__lt=feedback_cutoff).delete()[0]
    
    print(f"Cleaned up {deleted_events} old emotion events and {archived_feedback} feedback records")

# Schedule periodic tasks
app.conf.beat_schedule = {
    'train-rl-models': {
        'task': 'emotion_detection.celery_tasks.train_rl_models',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'update-emotion-models': {
        'task': 'emotion_detection.celery_tasks.update_emotion_prediction_models',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    'federated-aggregation': {
        'task': 'emotion_detection.celery_tasks.federated_learning_aggregation',
        'schedule': crontab(hour=4, minute=0),  # 4 AM daily
    },
    'hyperparameter-tuning': {
        'task': 'emotion_detection.celery_tasks.auto_hyperparameter_tuning',
        'schedule': crontab(hour=5, minute=0, day_of_week=1),  # 5 AM Monday
    },
    'goal-recommendations': {
        'task': 'emotion_detection.celery_tasks.generate_goal_recommendations',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),  # 6 AM Monday
    },
    'cleanup-data': {
        'task': 'emotion_detection.celery_tasks.cleanup_old_data',
        'schedule': crontab(hour=1, minute=0, day_of_week=0),  # 1 AM Sunday
    },
}
