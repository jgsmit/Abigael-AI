import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q

from tasks.models import Task
from .autonomous_models import EmotionEvent, TaskFeedback


class DopamineModel(models.Model):
    """Track dopamine-driven motivation patterns (Phase 4 Roadmap)"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Dopamine metrics
    dopamine_depletion_risk = models.FloatField(default=0.0)  # 0-100
    motivation_level = models.FloatField(default=50.0)  # 0-100
    reward_fatigue_score = models.FloatField(default=0.0)  # How numb to rewards
    
    # Contributing factors
    tasks_completed_streak = models.IntegerField(default=0)  # Consecutive tasks
    reward_received = models.BooleanField(default=False)
    reward_effectiveness = models.FloatField(default=1.0)  # How much reward motivated (0-1)
    
    # Energy curve
    energy_level = models.FloatField(default=50.0)  # 0-100
    motivation_curve = models.JSONField(default=dict)  # Hourly motivation tracking
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['motivation_level']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Motivation: {self.motivation_level:.0f}%"


class MotivationTracker(models.Model):
    """Track motivation patterns for personalization"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Individual motivation profile
    baseline_motivation = models.FloatField(default=50.0)  # User's natural level
    motivation_volatility = models.FloatField(default=0.3)  # How much it swings
    
    # What motivates this user
    prefers_small_wins = models.BooleanField(default=True)  # Small frequent vs big goals
    prefers_public_recognition = models.BooleanField(default=False)
    prefers_internal_metrics = models.BooleanField(default=True)
    
    # Reward sensitivity
    reward_sensitivity = models.FloatField(default=0.5)  # 0-1 (high = easily motivated)
    reward_variety_needed = models.BooleanField(default=False)  # Gets bored of same rewards
    
    # Dopamine depletion vulnerability
    depletion_risk_level = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High')],
        default='moderate'
    )
    typical_depletion_hours = models.IntegerField(default=6)  # Hours before depletion
    
    class Meta:
        verbose_name = "Motivation Tracker"
        verbose_name_plural = "Motivation Trackers"
    
    def __str__(self):
        return f"{self.user.username} - Motivation Profile"


class DopamineRegulationEngine:
    """
    Regulate dopamine and motivation for sustained productivity
    - Detect dopamine depletion
    - Inject small wins at optimal times
    - Rotate task difficulty
    - Adjust feedback tone
    """
    
    def __init__(self, user):
        self.user = user
        self.current_time = timezone.now()
        
    def detect_dopamine_depletion(self):
        """
        Detect if user is experiencing dopamine depletion
        Signs: motivation drops, rewards feel hollow, fatigue despite rest
        """
        # Get recent tasks and feedback
        recent_tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=self.current_time - timedelta(days=3)
        ).count()
        
        completed_tasks = Task.objects.filter(
            user=self.user,
            status='completed',
            completed_at__gte=self.current_time - timedelta(days=3)
        ).count()
        
        completion_rate = completed_tasks / max(recent_tasks, 1)
        
        # Get feedback sentiment
        recent_feedback = TaskFeedback.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(days=2)
        )
        
        if recent_feedback.exists():
            avg_satisfaction = recent_feedback.aggregate(
                Avg('task_satisfaction')
            )['task_satisfaction__avg'] or 3
        else:
            avg_satisfaction = 3
        
        # Get emotion trend
        emotion_quality = self._get_emotion_quality_trend()
        
        # Calculate depletion risk
        depletion_score = (
            (100 - (completion_rate * 100)) * 0.3 +  # Low completion = depletion
            ((5 - avg_satisfaction) * 20) * 0.3 +  # Low satisfaction = depletion
            ((5 - emotion_quality) * 20) * 0.4  # Negative emotions = depletion
        )
        
        depletion_score = min(100, max(0, depletion_score))
        
        if depletion_score > 70:
            level = 'critical'
        elif depletion_score > 50:
            level = 'high'
        elif depletion_score > 30:
            level = 'moderate'
        else:
            level = 'low'
        
        return {
            'depletion_score': depletion_score,
            'level': level,
            'completion_rate': completion_rate,
            'satisfaction': avg_satisfaction,
            'emotion_trend': emotion_quality,
            'recommendations': self._get_depletion_interventions(level)
        }
    
    def _get_emotion_quality_trend(self):
        """Get recent emotion trend (0-5, higher = better)"""
        recent_emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(days=2)
        ).order_by('-timestamp')[:20]
        
        positive_emotions = ['happy', 'excited', 'calm', 'focused', 'surprised']
        
        quality_scores = []
        for emotion in recent_emotions:
            if emotion.emotion in positive_emotions:
                quality_scores.append(4)
            elif emotion.emotion == 'neutral':
                quality_scores.append(3)
            else:
                quality_scores.append(1)
        
        return np.mean(quality_scores) if quality_scores else 3
    
    def _get_depletion_interventions(self, level):
        """Get interventions for dopamine depletion"""
        interventions = {
            'critical': [
                'Take full day off to reset',
                'Switch to enjoyable activities',
                'Social engagement recommended',
                'Sleep and rest prioritized',
                'Pause productivity focus'
            ],
            'high': [
                'Reduce workload by 40%',
                'Take 2-hour break now',
                'Enjoy favorite activity',
                'Seek social support',
                'Light tasks only'
            ],
            'moderate': [
                'Reduce workload by 20%',
                'Take hourly 10-min breaks',
                'Reward yourself with fun task',
                'Mix work with enjoyment',
                'Celebrate small wins'
            ],
            'low': [
                'Maintain current pace',
                'Celebrate completions',
                'Take planned breaks',
                'Vary task types'
            ]
        }
        
        return interventions.get(level, [])
    
    def inject_small_wins(self):
        """
        Strategically inject small wins to maintain motivation
        - Break large tasks into smaller completable chunks
        - Find quick wins in backlog
        - Celebrate progress
        """
        # Get pending large tasks
        large_tasks = Task.objects.filter(
            user=self.user,
            status='pending'
        ).order_by('-priority')
        
        recommendations = []
        
        for task in large_tasks[:5]:
            # Try to break into subtasks
            if len(task.description) > 200:  # Complex task
                subtasks = self._break_task_into_chunks(task)
                recommendations.append({
                    'task': task.title,
                    'action': 'break_into_subtasks',
                    'subtasks': subtasks,
                    'reason': 'Large tasks feel overwhelming - break into wins'
                })
            else:
                recommendations.append({
                    'task': task.title,
                    'action': 'prioritize',
                    'reason': 'Quick win available'
                })
        
        return {
            'small_wins_available': len(recommendations),
            'recommendations': recommendations,
            'benefit': 'These quick completions will boost motivation'
        }
    
    def _break_task_into_chunks(self, task):
        """Break task into smaller subtasks"""
        # This would be more sophisticated in production
        return [
            f"Step 1: {task.title[:20]}",
            f"Step 2: {task.title[20:40] or 'Continue'}",
            f"Step 3: {task.title[40:] or 'Complete'}"
        ]
    
    def rotate_task_difficulty(self):
        """
        Rotate between hard and easy tasks to maintain engagement
        - After hard task: give easy win
        - After easy task: give medium challenge
        - Pattern: hard -> easy -> medium -> hard
        """
        recent_tasks = Task.objects.filter(
            user=self.user,
            completed_at__gte=self.current_time - timedelta(days=3)
        ).order_by('-completed_at')[:10]
        
        if not recent_tasks:
            return {'recommendation': 'Start with easy task to build momentum'}
        
        # Analyze difficulty pattern
        difficulties = []
        for task in recent_tasks:
            # Estimate difficulty from description length and priority
            if len(task.description) > 300 or task.priority == 'high':
                difficulties.append('hard')
            elif len(task.description) < 100:
                difficulties.append('easy')
            else:
                difficulties.append('medium')
        
        # Suggest next task based on pattern
        if difficulties[-1] == 'hard':
            suggestion = 'Next: Easy win task'
            reason = 'Reward yourself after hard work'
        elif difficulties[-1] == 'easy':
            suggestion = 'Next: Medium challenge'
            reason = 'Build on momentum'
        else:
            suggestion = 'Next: Hard challenge'
            reason = 'Strike while confidence is high'
        
        return {
            'recent_pattern': difficulties,
            'suggestion': suggestion,
            'reason': reason,
            'expected_benefit': 'Varied difficulty maintains engagement'
        }
    
    def adjust_feedback_tone(self):
        """
        Adjust AI feedback tone based on current motivation level
        - Low motivation: More celebration, encouragement
        - High motivation: More challenge, bigger goals
        - Medium: Balanced
        """
        depletion = self.detect_dopamine_depletion()
        depletion_score = depletion['depletion_score']
        
        if depletion_score > 70:
            tone = {
                'type': 'supportive',
                'characteristics': [
                    'Celebrate every win (no matter how small)',
                    'Positive reinforcement',
                    'Gentle encouragement',
                    'No criticism',
                    'Emphasize progress'
                ],
                'example': 'Amazing! You finished that task. You\'re making real progress!'
            }
        elif depletion_score < 30:
            tone = {
                'type': 'challenging',
                'characteristics': [
                    'Acknowledge excellence',
                    'Suggest bigger goals',
                    'Highlight potential',
                    'Friendly competition angle',
                    'Growth focus'
                ],
                'example': 'Great work! You\'re clearly in a powerful state. Ready for something bigger?'
            }
        else:
            tone = {
                'type': 'balanced',
                'characteristics': [
                    'Recognize good work',
                    'Suggest next steps',
                    'Balance challenge and support',
                    'Maintain momentum'
                ],
                'example': 'Good work on that. Ready for the next one?'
            }
        
        return {
            'current_tone': tone,
            'reason': f'Motivation level: {100 - depletion_score:.0f}%',
            'activation': 'Use this tone for all AI responses'
        }
    
    def predict_motivation_crash(self):
        """
        Predict when motivation will crash based on patterns
        """
        # Get historical motivation tracking
        recent_dopamine = DopamineModel.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(days=3)
        ).order_by('-timestamp')[:20]
        
        if recent_dopamine.count() < 5:
            return {'prediction': 'insufficient_data'}
        
        motivation_levels = list(recent_dopamine.values_list('motivation_level', flat=True))
        
        # Fit simple trend
        x = np.arange(len(motivation_levels))
        y = np.array(motivation_levels)
        
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
        else:
            slope = 0
        
        current_motivation = motivation_levels[-1]
        
        if slope < -5:  # Steep decline
            return {
                'crash_predicted': True,
                'severity': 'critical',
                'hours_to_crash': max(1, current_motivation / 5),
                'recommendation': 'Intervene now with dopamine boost'
            }
        elif slope < -2:  # Gradual decline
            return {
                'crash_predicted': True,
                'severity': 'moderate',
                'hours_to_crash': current_motivation / 2,
                'recommendation': 'Plan recovery break within 2 hours'
            }
        
        return {'crash_predicted': False, 'trend': 'stable'}
    
    def personalized_reward_strategy(self):
        """
        Get personalized reward strategy based on user profile
        """
        tracker, _ = MotivationTracker.objects.get_or_create(user=self.user)
        
        if tracker.prefers_small_wins:
            strategy = {
                'type': 'frequent_small_wins',
                'frequency': 'every_2_tasks',
                'reward_size': 'small',
                'rewards': [
                    '5-minute break',
                    'Favorite snack',
                    'Quick social chat',
                    'Stretch break',
                    'Watch funny video'
                ]
            }
        else:
            strategy = {
                'type': 'milestone_based',
                'frequency': 'every_5_tasks',
                'reward_size': 'large',
                'rewards': [
                    '30-minute break',
                    'Favorite activity',
                    'Achievement badge',
                    'Social celebration',
                    'Special treat'
                ]
            }
        
        if tracker.reward_variety_needed:
            strategy['note'] = 'Rotate reward types to avoid adaptation'
        
        return strategy


class MotivationCoach:
    """Coach user toward sustained high motivation"""
    
    def __init__(self, user):
        self.user = user
        self.engine = DopamineRegulationEngine(user)
        
    def get_motivation_report(self):
        """Get comprehensive motivation status"""
        depletion = self.engine.detect_dopamine_depletion()
        crash_prediction = self.engine.predict_motivation_crash()
        small_wins = self.engine.inject_small_wins()
        difficulty_rotation = self.engine.rotate_task_difficulty()
        tone = self.engine.adjust_feedback_tone()
        reward_strategy = self.engine.personalized_reward_strategy()
        
        return {
            'depletion_analysis': depletion,
            'crash_prediction': crash_prediction,
            'small_wins_strategy': small_wins,
            'difficulty_rotation': difficulty_rotation,
            'feedback_tone': tone,
            'reward_strategy': reward_strategy
        }
    
    def suggest_next_action(self):
        """Suggest single best action to improve motivation"""
        depletion = self.engine.detect_dopamine_depletion()
        
        if depletion['level'] == 'critical':
            return {
                'action': 'rest',
                'duration_hours': 4,
                'reason': 'Motivation critically low - rest required'
            }
        elif depletion['level'] == 'high':
            return {
                'action': 'small_win',
                'task_type': 'quick_and_easy',
                'reason': 'Motivate with quick completion'
            }
        else:
            difficulty = self.engine.rotate_task_difficulty()
            return {
                'action': 'next_task',
                'suggestion': difficulty['suggestion'],
                'reason': difficulty['reason']
            }
