from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Avg, Count, Q
import json
from datetime import datetime, timedelta


class MentalHealthGuardrail(models.Model):
    """Guardrail system to protect mental health (Phase 6 Roadmap)"""
    
    GUARDRAIL_TYPES = [
        ('burnout_warning', 'Burnout Early Warning'),
        ('emotional_spiral', 'Emotional Spiral Detection'),
        ('grounding_suggestion', 'Grounding Suggestions'),
        ('human_escalation', 'Human Escalation'),
        ('crisis_support', 'Crisis Support'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Guardrail info
    guardrail_type = models.CharField(max_length=30, choices=GUARDRAIL_TYPES)
    is_active = models.BooleanField(default=True)
    
    # Status
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('critical', 'Critical')],
        default='moderate'
    )
    
    # Response
    suggested_action = models.TextField()
    action_taken = models.BooleanField(default=False)
    user_responded = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'guardrail_type']),
            models.Index(fields=['triggered', 'severity']),
        ]
    
    def __str__(self):
        status = "Triggered" if self.triggered else "Active"
        return f"{self.user.username} - {self.guardrail_type} ({status})"


class BurnoutEarlyWarning(models.Model):
    """Early warning system for burnout"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Risk indicators
    overwork_days_consecutive = models.IntegerField(default=0)  # Days without adequate rest
    stress_accumulation_score = models.FloatField(default=0.0)  # 0-100
    recovery_deficit_hours = models.FloatField(default=0.0)  # Hours of rest needed
    
    # Cognitive signs
    decision_quality_declining = models.BooleanField(default=False)
    attention_span_decreasing = models.BooleanField(default=False)
    fatigue_increasing = models.BooleanField(default=False)
    emotional_volatility_high = models.BooleanField(default=False)
    
    # Behavioral signs
    break_frequency_decreased = models.BooleanField(default=False)
    sleep_quality_poor = models.BooleanField(default=False)
    social_withdrawal = models.BooleanField(default=False)
    
    # Prediction
    days_to_burnout = models.IntegerField(null=True, blank=True)
    confidence_score = models.FloatField(default=0.0)  # 0-1
    
    # Recommendation
    urgent_action_needed = models.BooleanField(default=False)
    suggested_interventions = models.JSONField(default=list)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['urgent_action_needed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Burnout Risk: {self.days_to_burnout} days"


class EmotionalSpiralDetector(models.Model):
    """Detect negative emotional spirals (downward cascades)"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Spiral detection
    spiral_detected = models.BooleanField(default=False)
    spiral_type = models.CharField(
        max_length=30,
        choices=[
            ('anxiety_spiral', 'Anxiety Spiral'),
            ('depression_cascade', 'Depression Cascade'),
            ('frustration_buildup', 'Frustration Buildup'),
            ('hopelessness_spiral', 'Hopelessness Spiral'),
        ],
        blank=True
    )
    
    # Metrics
    emotion_decline_rate = models.FloatField(default=0.0)  # Units per hour
    spiral_depth = models.FloatField(default=0.0)  # 0-100 (how bad)
    
    # Timeline
    spiral_duration_minutes = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    
    # Triggers identified
    identified_triggers = models.JSONField(default=list)  # What caused spiral
    
    # Intervention
    intervention_applied = models.CharField(
        max_length=50,
        choices=[
            ('breathing', 'Breathing Exercise'),
            ('grounding', 'Grounding Technique'),
            ('distraction', 'Healthy Distraction'),
            ('support_contact', 'Support Contact'),
            ('none', 'None Yet'),
        ],
        default='none'
    )
    intervention_effective = models.BooleanField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['spiral_detected']),
        ]
    
    def __str__(self):
        status = self.spiral_type if self.spiral_detected else "No spiral"
        return f"{self.user.username} - {status}"


class GroundingExercise(models.Model):
    """Grounding exercises recommended during distress"""
    
    EXERCISE_TYPES = [
        ('5_4_3_2_1', '5-4-3-2-1 Grounding'),
        ('box_breathing', 'Box Breathing'),
        ('body_scan', 'Body Scan'),
        ('cold_exposure', 'Cold Water Exposure'),
        ('physical_activity', 'Physical Activity'),
        ('mindfulness', 'Mindfulness Meditation'),
        ('journaling', 'Grounding Journaling'),
        ('nature_connection', 'Nature Connection'),
        ('music_therapy', 'Music Therapy'),
        ('social_support', 'Reaching Out'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Exercise info
    exercise_type = models.CharField(max_length=30, choices=EXERCISE_TYPES)
    recommended_duration_minutes = models.IntegerField(default=5)
    
    # Instruction
    instructions = models.TextField()
    
    # Outcomes
    user_did_exercise = models.BooleanField(default=False)
    effectiveness_score = models.IntegerField(null=True, blank=True)  # 0-10 (if completed)
    
    # Context
    emotion_before = models.CharField(max_length=20, blank=True)
    emotion_after = models.CharField(max_length=20, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'exercise_type']),
            models.Index(fields=['user_did_exercise']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.exercise_type}"


class CrisisIndicator(models.Model):
    """Track crisis indicators requiring professional help"""
    
    CRISIS_LEVELS = [
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('critical', 'Critical - Immediate Help'),
    ]
    
    INDICATORS = [
        ('suicidal_ideation', 'Suicidal Thoughts'),
        ('self_harm', 'Self-Harm Indicators'),
        ('substance_abuse', 'Substance Abuse Signs'),
        ('severe_anxiety', 'Severe Anxiety Attack'),
        ('psychotic_symptoms', 'Psychotic Symptoms'),
        ('acute_depression', 'Severe Depression'),
        ('violent_ideation', 'Violent Thoughts'),
        ('extreme_isolation', 'Extreme Isolation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Detection
    indicator_type = models.CharField(max_length=30, choices=INDICATORS)
    crisis_level = models.CharField(max_length=20, choices=CRISIS_LEVELS)
    confidence = models.FloatField(default=0.0)  # 0-1 (how sure we are)
    
    # Context (general, no specifics)
    triggering_event = models.CharField(max_length=200, blank=True)
    
    # Response
    escalated_to_professional = models.BooleanField(default=False)
    professional_type = models.CharField(
        max_length=50,
        choices=[
            ('counselor', 'Counselor'),
            ('therapist', 'Therapist'),
            ('crisis_hotline', 'Crisis Hotline'),
            ('emergency', 'Emergency Services'),
            ('none', 'None Yet'),
        ],
        default='none'
    )
    
    # Follow-up
    followup_required = models.BooleanField(default=False)
    followup_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'crisis_level']),
            models.Index(fields=['escalated_to_professional']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.indicator_type} ({self.crisis_level})"


class HumanSupportEscalation(models.Model):
    """Escalation to human support team"""
    
    SUPPORT_TYPES = [
        ('peer_support', 'Peer Support'),
        ('wellness_coach', 'Wellness Coach'),
        ('mental_health_counselor', 'Mental Health Counselor'),
        ('crisis_team', 'Crisis Team'),
        ('emergency', 'Emergency'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Escalation info
    reason = models.CharField(max_length=30, choices=SUPPORT_TYPES)
    urgency = models.CharField(
        max_length=20,
        choices=[('low', 'Can wait'), ('moderate', 'Soon'), ('high', 'Today'), ('critical', 'Now')],
        default='moderate'
    )
    
    # Support assignment
    assigned_support_person = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_assignments'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Contact
    contact_attempted = models.BooleanField(default=False)
    contact_successful = models.BooleanField(default=False)
    
    # Outcome
    resolved = models.BooleanField(default=False)
    resolution_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'urgency']),
            models.Index(fields=['resolved']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.reason} ({self.urgency})"


class MentalHealthGuardrailEngine:
    """Engine that manages mental health guardrails"""
    
    def __init__(self, user):
        self.user = user
        self.current_time = timezone.now()
    
    def check_all_guardrails(self):
        """Check all mental health guardrails"""
        results = {
            'burnout_warning': self.check_burnout_warning(),
            'emotional_spiral': self.check_emotional_spiral(),
            'crisis_indicators': self.check_crisis_indicators(),
            'critical_actions': []
        }
        
        # Add critical actions if needed
        if results['burnout_warning']['triggered']:
            results['critical_actions'].append('burnout_intervention')
        if results['emotional_spiral']['detected']:
            results['critical_actions'].append('grounding_exercise')
        if results['crisis_indicators']['detected']:
            results['critical_actions'].append('professional_escalation')
        
        return results
    
    def check_burnout_warning(self):
        """Check for burnout early warning signs"""
        seven_days_ago = self.current_time - timedelta(days=7)
        
        # Check indicators
        overwork_days = self._count_overwork_days()
        stress_accumulation = self._calculate_stress_accumulation()
        recovery_deficit = self._calculate_recovery_deficit()
        
        # Cognitive signs
        decision_quality_declining = self._check_decision_quality_decline()
        attention_decreasing = self._check_attention_span_decrease()
        
        # Create warning if needed
        warning_score = (
            (overwork_days * 10) +
            (stress_accumulation * 0.5) +
            (recovery_deficit) +
            (decision_quality_declining * 20) +
            (attention_decreasing * 15)
        )
        
        triggered = warning_score > 50
        
        if triggered:
            days_to_burnout = max(1, int(warning_score / 10))
        else:
            days_to_burnout = None
        
        return {
            'triggered': triggered,
            'warning_score': warning_score,
            'days_to_burnout': days_to_burnout,
            'overwork_days': overwork_days,
            'stress_level': stress_accumulation,
            'urgent_interventions': [
                'Take immediate rest day',
                'Reduce workload by 50%',
                'Schedule professional consultation',
                'Activate recovery mode'
            ] if triggered else []
        }
    
    def _count_overwork_days(self):
        """Count consecutive days of overwork (>10 hours or high stress)"""
        from tasks.models import Task
        from django.db.models import Q, Count
        
        cutoff = self.current_time - timedelta(days=7)
        overwork_days = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff
        ).dates('created_at', 'day').count()
        
        return min(overwork_days, 7)
    
    def _calculate_stress_accumulation(self):
        """Calculate accumulated stress (0-100)"""
        from emotion_detection.models import EmotionEvent
        from emotion_detection.cognitive_models import CognitiveState
        
        cutoff = self.current_time - timedelta(days=7)
        
        stress_emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=cutoff,
            emotion__in=['stressed', 'anxious', 'angry', 'frustrated']
        ).count()
        
        high_load_states = CognitiveState.objects.filter(
            user=self.user,
            timestamp__gte=cutoff,
            cognitive_load_score__gt=75
        ).count() if hasattr(CognitiveState, '_meta') else 0
        
        total_records = max(1, CognitiveState.objects.filter(
            user=self.user,
            timestamp__gte=cutoff
        ).count())
        
        stress_percentage = min(100.0, ((stress_emotions + high_load_states) / total_records) * 100)
        return stress_percentage
    
    def _calculate_recovery_deficit(self):
        """Calculate hours of recovery needed based on sleep and workload"""
        from tasks.models import Task
        
        cutoff = self.current_time - timedelta(days=7)
        
        total_tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff
        ).count()
        
        completed_tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff,
            completed_at__isnull=False
        ).count()
        
        # Base recovery: 1 hour per 10 incomplete tasks
        incomplete_tasks = total_tasks - completed_tasks
        deficit = (incomplete_tasks / 10.0) if incomplete_tasks > 0 else 0
        
        if total_tasks > 50:
            deficit += 4.0  # High workload = more recovery
        
        return min(48.0, deficit)
    
    def _check_decision_quality_decline(self):
        """Check if decision quality is declining"""
        from emotion_detection.cognitive_models import DecisionDegradationTracker
        
        recent = DecisionDegradationTracker.objects.filter(
            user=self.user
        ).order_by('-timestamp')[:10]
        
        if len(recent) < 3:
            return False
        
        recent_quality = sum([r.decision_quality_score for r in recent[:3]]) / 3
        previous_quality = sum([r.decision_quality_score for r in recent[3:6]]) / 3 if len(recent) >= 6 else recent_quality
        
        return (previous_quality - recent_quality) > 5
    
    def _check_attention_span_decrease(self):
        """Check if attention span is decreasing"""
        from emotion_detection.cognitive_models import AttentionSpanMetrics
        
        recent = AttentionSpanMetrics.objects.filter(
            user=self.user
        ).order_by('-timestamp')[:10]
        
        if len(recent) < 3:
            return False
        
        recent_decay = sum([r.decay_rate_percent for r in recent[:3]]) / 3
        previous_decay = sum([r.decay_rate_percent for r in recent[3:6]]) / 3 if len(recent) >= 6 else recent_decay
        
        return (recent_decay - previous_decay) > 2.0
    
    def check_emotional_spiral(self):
        """Check for negative emotional spirals"""
        recent_emotions = self._get_recent_emotions(hours=4)
        
        if len(recent_emotions) < 3:
            return {'detected': False}
        
        # Analyze emotion trajectory
        is_spiraling = self._analyze_emotion_trajectory(recent_emotions)
        
        if is_spiraling:
            spiral_type = self._identify_spiral_type(recent_emotions)
            decline_rate = self._calculate_decline_rate(recent_emotions)
            
            return {
                'detected': True,
                'spiral_type': spiral_type,
                'decline_rate': decline_rate,
                'depth': len(recent_emotions) * decline_rate,
                'intervention': self._get_spiral_intervention(spiral_type)
            }
        
        return {'detected': False}
    
    def _get_recent_emotions(self, hours=4):
        """Get recent emotion history"""
        from emotion_detection.models import EmotionEvent
        
        cutoff = self.current_time - timedelta(hours=hours)
        emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=cutoff
        ).order_by('timestamp').values_list('emotion', 'intensity', 'timestamp')
        
        return list(emotions)
    
    def _analyze_emotion_trajectory(self, emotions):
        """Check if emotions are declining in negative direction"""
        if len(emotions) < 3:
            return False
        
        emotion_scores = {
            'excited': 2, 'happy': 1, 'calm': 0, 'focused': 1, 'engaged': 1,
            'neutral': 5, 'tired': 6, 'bored': 6,
            'stressed': 7, 'anxious': 8, 'angry': 9, 'sad': 8, 'depressed': 10, 'hopeless': 10
        }
        
        scores = [emotion_scores.get(e[0], 5) * ((e[1] or 5) / 10.0) for e in emotions]
        
        recent_avg = sum(scores[-3:]) / 3
        older_avg = sum(scores[:-3]) / 3 if len(scores) > 3 else recent_avg
        
        return recent_avg > (older_avg + 1.0)
    
    def _identify_spiral_type(self, emotions):
        """Identify what type of spiral based on emotion patterns"""
        if not emotions:
            return 'anxiety_spiral'
        
        emotion_list = [e[0] for e in emotions]
        total = len(emotion_list)
        
        if emotion_list.count('anxious') > total * 0.5:
            return 'anxiety_spiral'
        elif emotion_list.count('sad') > total * 0.5 or 'depressed' in emotion_list:
            return 'depression_cascade'
        elif emotion_list.count('angry') > total * 0.4:
            return 'frustration_buildup'
        elif 'hopeless' in emotion_list or emotion_list.count('depressed') > total * 0.6:
            return 'hopelessness_spiral'
        
        return 'anxiety_spiral'
    
    def _calculate_decline_rate(self, emotions):
        """Calculate how fast emotions are worsening (points per hour)"""
        if len(emotions) < 2:
            return 0.0
        
        emotion_scores = {
            'excited': 2, 'happy': 1, 'calm': 0, 'focused': 1, 'engaged': 1,
            'neutral': 5, 'tired': 6, 'bored': 6,
            'stressed': 7, 'anxious': 8, 'angry': 9, 'sad': 8, 'depressed': 10, 'hopeless': 10
        }
        
        first_score = emotion_scores.get(emotions[0][0], 5)
        last_score = emotion_scores.get(emotions[-1][0], 5)
        
        first_time = emotions[0][2]
        last_time = emotions[-1][2]
        hours_elapsed = max(0.25, (last_time - first_time).total_seconds() / 3600)
        
        decline_rate = (last_score - first_score) / hours_elapsed
        return max(0, decline_rate)
    
    def _get_spiral_intervention(self, spiral_type):
        """Get intervention for spiral type"""
        interventions = {
            'anxiety_spiral': 'Box breathing exercise',
            'depression_cascade': 'Social connection and movement',
            'frustration_buildup': 'Physical release activity',
            'hopelessness_spiral': 'Professional support immediately'
        }
        return interventions.get(spiral_type, 'Grounding exercise')
    
    def check_crisis_indicators(self):
        """Check for crisis-level indicators"""
        keywords_found = self._scan_for_crisis_keywords()
        behavioral_changes = self._detect_behavioral_changes()
        severity = self._calculate_crisis_severity(keywords_found, behavioral_changes)
        
        detected = severity > 0.5
        
        if detected:
            # Create crisis indicator record
            self._escalate_to_crisis_team(severity)
        
        return {
            'detected': detected,
            'severity': severity,
            'keywords': keywords_found,
            'behavioral_changes': behavioral_changes,
            'recommended_action': 'CALL CRISIS HOTLINE' if detected else 'None'
        }
    
    def _scan_for_crisis_keywords(self):
        """Scan user input for crisis keywords in recent entries"""
        from tasks.models import Task
        
        crisis_keywords = {
            'suicidal': ['suicide', 'kill myself', 'end it'],
            'self_harm': ['cut', 'hurt myself', 'harm'],
            'substance_abuse': ['drugs', 'pills', 'alcohol'],
            'violent': ['kill', 'hurt someone', 'attack'],
        }
        
        cutoff = self.current_time - timedelta(hours=24)
        tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff
        ).values_list('title', 'description')
        
        found_keywords = {}
        
        for title, desc in tasks:
            full_text = f"{title} {desc or ''}".lower()
            for category, keywords in crisis_keywords.items():
                for keyword in keywords:
                    if keyword in full_text:
                        if category not in found_keywords:
                            found_keywords[category] = []
                        found_keywords[category].append(keyword)
        
        return found_keywords
    
    def _detect_behavioral_changes(self):
        """Detect sudden behavioral changes vs historical patterns"""
        from tasks.models import Task
        
        cutoff_recent = self.current_time - timedelta(days=2)
        cutoff_historical = self.current_time - timedelta(days=30)
        
        recent_tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff_recent
        ).count()
        
        recent_completion = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff_recent,
            completed_at__isnull=False
        ).count()
        
        historical_tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff_historical
        ).count()
        
        historical_completion = Task.objects.filter(
            user=self.user,
            created_at__gte=cutoff_historical,
            completed_at__isnull=False
        ).count()
        
        changes = []
        
        if historical_tasks > 0:
            historical_rate = historical_completion / historical_tasks
            recent_rate = recent_completion / recent_tasks if recent_tasks > 0 else 0
            if recent_rate < (historical_rate * 0.5):
                changes.append('sudden_low_productivity')
            if recent_tasks > (historical_tasks / 15) * 3:
                changes.append('sudden_high_task_creation')
        
        last_interaction = Task.objects.filter(
            user=self.user
        ).order_by('-updated_at').first()
        
        if last_interaction and (self.current_time - last_interaction.updated_at).days > 7:
            changes.append('prolonged_inactivity')
        
        return changes
    
    def _calculate_crisis_severity(self, keywords, behaviors):
        """Calculate severity (0-1) based on crisis indicators"""
        severity = 0.0
        
        if keywords.get('suicidal'):
            severity += 0.9
        if keywords.get('self_harm'):
            severity += 0.8
        if keywords.get('violent'):
            severity += 0.85
        if keywords.get('substance_abuse'):
            severity += 0.6
        
        if 'sudden_low_productivity' in behaviors:
            severity += 0.15
        if 'prolonged_inactivity' in behaviors:
            severity += 0.2
        if 'sudden_high_task_creation' in behaviors:
            severity += 0.1
        
        return min(1.0, severity)
    
    def _escalate_to_crisis_team(self, severity):
        """Escalate to crisis team"""
        # Create escalation record
        HumanSupportEscalation.objects.create(
            user=self.user,
            reason='crisis_team',
            urgency='critical' if severity > 0.8 else 'high'
        )
    
    def recommend_grounding_exercise(self, emotion_state=None):
        """Recommend personalized grounding exercise"""
        exercises = GroundingExercise.objects.filter(user=self.user)
        
        if exercises.exists():
            # Recommend most effective exercise
            most_effective = exercises.filter(
                user_did_exercise=True
            ).order_by('-effectiveness_score').first()
            
            if most_effective:
                return {
                    'exercise': most_effective.exercise_type,
                    'reason': 'Your most effective grounding technique',
                    'duration': most_effective.recommended_duration_minutes
                }
        
        # Default recommendations
        defaults = {
            'stressed': '5_4_3_2_1',
            'anxious': 'box_breathing',
            'sad': 'body_scan',
            'angry': 'physical_activity'
        }
        
        exercise_type = defaults.get(emotion_state, 'mindfulness')
        
        return {
            'exercise': exercise_type,
            'reason': f'Good for {emotion_state} state',
            'duration': 5
        }
