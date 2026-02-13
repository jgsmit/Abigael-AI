"""Micro-intervention models for contextual nudges and brief supportive tasks."""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class InterventionRule(models.Model):
    """Rules that define when and how to trigger interventions."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Trigger conditions
    TRIGGER_TYPES = [
        ('emotion', 'User Emotion'),
        ('time_of_day', 'Time of Day'),
        ('pattern', 'Behavior Pattern'),
        ('stress_level', 'Stress Level'),
        ('no_interaction', 'Inactivity'),
        ('milestone', 'Milestone/Event'),
    ]
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES)
    trigger_condition = models.JSONField(default=dict)  # e.g., {"emotion": "sad", "intensity_min": 0.6}
    
    # Response
    intervention_type = models.CharField(max_length=30, choices=[
        ('breathing', 'Breathing Exercise'),
        ('cbt', 'CBT Task'),
        ('gratitude', 'Gratitude Prompt'),
        ('movement', 'Movement/Stretch'),
        ('music', 'Music Recommendation'),
        ('journal', 'Journal Prompt'),
        ('social', 'Social Connection'),
        ('rest', 'Rest Reminder'),
        ('hydration', 'Hydration Reminder'),
        ('meditation', 'Guided Meditation'),
    ])
    
    # Scheduling
    max_daily = models.IntegerField(default=3, help_text='Max times per day')
    cooldown_minutes = models.IntegerField(default=60, help_text='Wait between triggers')
    time_windows = models.JSONField(
        default=list,
        help_text='e.g., [{"start": "09:00", "end": "22:00"}]'
    )
    
    # Configuration
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)  # Higher = more important
    success_rate = models.FloatField(default=0.5)  # 0-1, for A/B testing
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.intervention_type})"


class InterventionContent(models.Model):
    """Content library for interventions."""
    rule = models.ForeignKey(InterventionRule, on_delete=models.CASCADE, related_name='content')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Media and instructions
    instructions = models.TextField(help_text='Step-by-step guide')
    audio_url = models.URLField(blank=True, help_text='e.g., guided meditation link')
    video_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    
    # Duration and difficulty
    duration_seconds = models.IntegerField(help_text='Estimated time in seconds')
    difficulty = models.CharField(max_length=10, choices=[
        ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')
    ], default='easy')
    
    # Effectiveness data
    completion_rate = models.FloatField(default=0.0)  # 0-1
    user_ratings = models.JSONField(default=list)  # [1-5 scores]
    
    # Accessibility
    is_active = models.BooleanField(default=True)
    variants = models.JSONField(
        default=list,
        help_text='Alternative versions for different modalities'
    )
    
    def __str__(self):
        return f"{self.title}"


class UserIntervention(models.Model):
    """Track user-specific intervention history and engagement."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interventions')
    rule = models.ForeignKey(InterventionRule, on_delete=models.CASCADE)
    content = models.ForeignKey(InterventionContent, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Delivery
    triggered_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    # Engagement
    viewed = models.BooleanField(default=False)
    started = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Feedback
    user_rating = models.IntegerField(null=True, blank=True, choices=[(i, str(i)) for i in range(1, 6)])
    feedback_text = models.TextField(blank=True)
    was_helpful = models.BooleanField(null=True, blank=True)
    
    # Context
    triggering_emotion = models.CharField(max_length=20, blank=True)
    triggering_stress_level = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['user', '-triggered_at']),
            models.Index(fields=['completed', 'triggered_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.rule.name} at {self.triggered_at}"


class InterventionTemplate(models.Model):
    """Reusable intervention templates for quick setup."""
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Template configuration
    default_rule_config = models.JSONField()
    default_content_list = models.JSONField()  # list of content configs
    
    category = models.CharField(max_length=30, choices=[
        ('mental_health', 'Mental Health'),
        ('physical', 'Physical Wellness'),
        ('social', 'Social Connection'),
        ('productivity', 'Productivity'),
        ('leisure', 'Leisure & Fun'),
    ])
    
    is_public = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
