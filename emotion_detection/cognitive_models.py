from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json
import numpy as np
from datetime import datetime, timedelta

class CognitiveState(models.Model):
    """Advanced cognitive state tracking (Phase 2 Roadmap)"""
    
    COGNITIVE_STATE_CHOICES = [
        ('focused', 'Focused'),
        ('overloaded', 'Overloaded'),
        ('drained', 'Drained'),
        ('flow', 'Flow State'),
        ('anxious', 'Anxious'),
        ('bored', 'Bored'),
        ('saturated', 'Mentally Saturated'),
        ('recovering', 'Recovery-Needed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Cognitive state classification
    cognitive_state = models.CharField(max_length=20, choices=COGNITIVE_STATE_CHOICES)
    confidence = models.FloatField(default=0.0)  # 0-1 confidence score
    
    # Cognitive load metrics (0-100 scale)
    cognitive_load_score = models.FloatField(default=0.0)  # Overall load
    
    # Component metrics
    typing_error_rate = models.FloatField(default=0.0)  # % of errors in typing
    task_switch_frequency = models.IntegerField(default=0)  # Number of switches per hour
    speech_hesitation_score = models.FloatField(default=0.0)  # Hesitation intensity (0-1)
    reaction_time_ms = models.IntegerField(default=0)  # Milliseconds to respond
    heart_rate_variability = models.FloatField(default=0.0)  # HRV score (higher = better)
    
    # Mental state indicators
    attention_span_minutes = models.IntegerField(default=0)  # Minutes before degradation
    mental_fatigue_score = models.FloatField(default=0.0)  # 0-100 (emotional fatigue)
    decision_degradation_score = models.FloatField(default=0.0)  # Decision quality decline
    focus_stability = models.FloatField(default=0.0)  # 0-1 (how stable focus is)
    
    # Recovery metrics
    recovery_needed = models.BooleanField(default=False)
    recovery_priority = models.IntegerField(default=0)  # 1-10 priority score
    
    # Related data
    current_task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    related_emotion = models.CharField(max_length=20, blank=True)  # Associated emotion
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['cognitive_state', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.cognitive_state} (Load: {self.cognitive_load_score:.0f}%)"


class BurnoutRisk(models.Model):
    """Burnout prediction and risk tracking"""
    
    BURNOUT_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Burnout risk metrics
    burnout_risk_score = models.FloatField(default=0.0)  # 0-100
    burnout_level = models.CharField(max_length=20, choices=BURNOUT_LEVEL_CHOICES, default='low')
    
    # Contributing factors
    stress_accumulation = models.FloatField(default=0.0)  # Cumulative stress level
    task_overload_days = models.IntegerField(default=0)  # Consecutive overload days
    recovery_deficit = models.FloatField(default=0.0)  # Recovery time needed
    work_life_balance_score = models.FloatField(default=0.5)  # 0-1 (1 = perfect balance)
    
    # Trend analysis
    trend_direction = models.CharField(
        max_length=10, 
        choices=[('improving', 'Improving'), ('stable', 'Stable'), ('worsening', 'Worsening')],
        default='stable'
    )
    days_to_critical = models.IntegerField(null=True, blank=True)  # Days until critical if worsening
    
    # Recommendations
    recommended_actions = models.JSONField(default=list)  # List of recommended recovery actions
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['burnout_level', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Burnout Risk: {self.burnout_level} ({self.burnout_risk_score:.0f}%)"


class CognitiveLoadHistory(models.Model):
    """Historical tracking of cognitive load patterns"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Daily metrics
    peak_load_score = models.FloatField(default=0.0)
    average_load_score = models.FloatField(default=0.0)
    min_load_score = models.FloatField(default=0.0)
    
    # Time distribution
    time_in_overload = models.IntegerField(default=0)  # Minutes over threshold
    time_in_focus = models.IntegerField(default=0)  # Minutes focused
    time_in_flow = models.IntegerField(default=0)  # Minutes in flow state
    
    # Recovery tracking
    recovery_time_taken = models.IntegerField(default=0)  # Minutes spent recovering
    recovery_effectiveness = models.FloatField(default=0.0)  # How effective recovery was
    
    # Productivity correlation
    tasks_completed = models.IntegerField(default=0)
    task_completion_rate = models.FloatField(default=0.0)  # % of planned tasks
    
    class Meta:
        unique_together = ['user', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.date} (Avg Load: {self.average_load_score:.0f}%)"


class FlowStateMetrics(models.Model):
    """Flow state detection and tracking"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Flow indicators
    typing_rhythm_stability = models.FloatField(default=0.0)  # 0-1 (regular = flow)
    blink_rate = models.FloatField(default=0.0)  # Blinks per minute (reduced = flow)
    hrv_stability = models.FloatField(default=0.0)  # Heart rate variability stability
    silence_score = models.FloatField(default=0.0)  # No interruptions score
    
    # Flow characteristics
    depth_score = models.FloatField(default=0.0)  # 0-100 (depth of flow)
    duration_minutes = models.IntegerField(default=0)  # How long flow lasted
    task_completed = models.BooleanField(default=False)
    task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Recovery after flow
    recovery_time_needed = models.IntegerField(default=0)  # Minutes to recover
    suggested_break_type = models.CharField(max_length=50, blank=True)  # Type of break
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['user', 'end_time']),
        ]
    
    def __str__(self):
        duration = self.duration_minutes if self.end_time else "ongoing"
        return f"{self.user.username} - Flow State ({duration} min)"


class AttentionSpanMetrics(models.Model):
    """Track individual attention span and decay patterns"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Attention metrics
    focus_duration_minutes = models.IntegerField(default=0)  # How long they focused
    focus_decay_rate = models.FloatField(default=0.0)  # % per minute before degradation
    concentration_quality = models.FloatField(default=0.0)  # 0-1 (quality of focus)
    
    # Task-specific metrics
    task_type = models.CharField(max_length=50, blank=True)  # e.g., 'coding', 'writing'
    task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Recovery data
    time_to_recover = models.IntegerField(default=0)  # Minutes needed to refocus
    recovery_method = models.CharField(max_length=50, blank=True)  # What helped recovery
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['task_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Focus: {self.focus_duration_minutes}min"


class MentalFatigueTracker(models.Model):
    """Distinct from emotional fatigue - tracks mental/cognitive fatigue"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Mental fatigue components
    decision_fatigue_score = models.FloatField(default=0.0)  # 0-100
    cognitive_fatigue_score = models.FloatField(default=0.0)  # 0-100
    emotional_fatigue_score = models.FloatField(default=0.0)  # 0-100
    physical_fatigue_score = models.FloatField(default=0.0)  # 0-100
    
    # Overall composite
    total_fatigue_score = models.FloatField(default=0.0)  # 0-100 weighted average
    
    # Causes identified
    primary_cause = models.CharField(max_length=50, blank=True)  # e.g., 'too many decisions'
    contributing_factors = models.JSONField(default=list)
    
    # Recovery recommendations
    recovery_priority = models.IntegerField(default=0)  # 1-10
    recommended_recovery = models.JSONField(default=dict)  # {type: hours_needed}
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['total_fatigue_score']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Mental Fatigue: {self.total_fatigue_score:.0f}%"


class CognitiveUserDNA(models.Model):
    """User's unique cognitive profile - learning how they work best"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Work preferences
    best_work_hours = models.JSONField(default=dict)  # {hour: productivity_score}
    worst_work_hours = models.JSONField(default=dict)
    optimal_session_length_minutes = models.IntegerField(default=90)
    
    # Stress & recovery
    stress_tolerance_threshold = models.FloatField(default=70.0)  # 0-100
    burnout_risk_baseline = models.FloatField(default=0.2)  # Individual baseline
    recovery_speed_hours = models.FloatField(default=8.0)  # How fast they bounce back
    
    # Focus patterns
    average_focus_decay_rate = models.FloatField(default=0.05)  # % per minute
    typical_attention_span_minutes = models.IntegerField(default=45)
    focus_regain_difficulty = models.CharField(
        max_length=20,
        choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('hard', 'Hard')],
        default='moderate'
    )
    
    # Emotional volatility
    emotional_stability_score = models.FloatField(default=0.5)  # 0-1 (how stable)
    mood_swing_frequency = models.CharField(
        max_length=20,
        choices=[('rare', 'Rare'), ('occasional', 'Occasional'), ('frequent', 'Frequent')],
        default='occasional'
    )
    
    # Peak performance conditions
    ideal_workload = models.CharField(
        max_length=20,
        choices=[('light', 'Light'), ('moderate', 'Moderate'), ('heavy', 'Heavy')],
        default='moderate'
    )
    preferred_task_type = models.CharField(max_length=50, blank=True)
    optimal_social_contact = models.CharField(
        max_length=20,
        choices=[('solitary', 'Solitary'), ('pairs', 'Pairs'), ('groups', 'Groups')],
        default='solitary'
    )
    
    # Data quality
    samples_collected = models.IntegerField(default=0)
    data_quality_score = models.FloatField(default=0.0)  # 0-1
    
    class Meta:
        verbose_name = "Cognitive User DNA"
        verbose_name_plural = "Cognitive User DNAs"
    
    def __str__(self):
        return f"{self.user.username}'s Cognitive Profile"


class DecisionDegradationTracker(models.Model):
    """Track quality of decision-making over time"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Decision metrics
    decision_quality_score = models.FloatField(default=100.0)  # 0-100 (100 = perfect)
    decision_speed = models.IntegerField(default=0)  # Seconds to make decision
    
    # Degradation indicators
    clarity_score = models.FloatField(default=100.0)  # Clear thinking
    rationality_score = models.FloatField(default=100.0)  # Logical vs emotional
    risk_assessment_quality = models.FloatField(default=100.0)  # Accuracy of risk eval
    
    # Context
    fatigue_level = models.FloatField(default=0.0)  # 0-100
    stress_level = models.FloatField(default=0.0)  # 0-100
    cognitive_load = models.FloatField(default=0.0)  # 0-100
    
    # Outcome tracking
    decision = models.TextField(max_length=500, blank=True)
    predicted_outcome_quality = models.CharField(
        max_length=20,
        choices=[('poor', 'Poor'), ('fair', 'Fair'), ('good', 'Good'), ('excellent', 'Excellent')],
        default='good'
    )
    actual_outcome_quality = models.CharField(
        max_length=20,
        choices=[('poor', 'Poor'), ('fair', 'Fair'), ('good', 'Good'), ('excellent', 'Excellent')],
        null=True, blank=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['decision_quality_score']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Decision Quality: {self.decision_quality_score:.0f}%"
