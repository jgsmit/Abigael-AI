from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class LifeEvent(models.Model):
    """Life events for comprehensive life management"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Event details
    event_type = models.CharField(max_length=30, choices=[
        ('meeting', 'Meeting'),
        ('date', 'Date'),
        ('appointment', 'Appointment'),
        ('social_event', 'Social Event'),
        ('family_event', 'Family Event'),
        ('work_event', 'Work Event'),
        ('personal_goal', 'Personal Goal'),
        ('health_appointment', 'Health Appointment'),
        ('interview', 'Interview'),
        ('presentation', 'Presentation'),
        ('travel', 'Travel'),
        ('celebration', 'Celebration')
    ])
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Timing
    event_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    reminder_minutes = models.IntegerField(default=30)
    
    # Location and context
    location = models.CharField(max_length=200, blank=True)
    participants = models.JSONField(default=list)  # For meetings, dates, etc.
    
    # Preparation and follow-up
    preparation_needed = models.TextField(blank=True)
    preparation_completed = models.BooleanField(default=False)
    
    # Emotional context
    expected_emotion = models.CharField(max_length=20, default='neutral')
    actual_emotion_before = models.CharField(max_length=20, blank=True)
    actual_emotion_after = models.CharField(max_length=20, blank=True)
    
    # Outcome tracking
    outcome_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Poor'), (2, 'Poor'), (3, 'Average'), 
        (4, 'Good'), (5, 'Very Good'), (6, 'Excellent')
    ])
    
    outcome_notes = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    
    # AI assistance
    ai_preparation_advice = models.TextField(blank=True)
    ai_followup_insights = models.TextField(blank=True)
    ai_improvement_suggestions = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('preparing', 'Preparing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='scheduled')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['event_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.event_date.date()})"

class EventPreparation(models.Model):
    """AI-generated preparation for events"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    life_event = models.ForeignKey(LifeEvent, on_delete=models.CASCADE)
    
    # Preparation content
    preparation_type = models.CharField(max_length=30, choices=[
        ('meeting_prep', 'Meeting Preparation'),
        ('date_prep', 'Date Preparation'),
        ('interview_prep', 'Interview Preparation'),
        ('presentation_prep', 'Presentation Preparation'),
        ('social_prep', 'Social Event Preparation')
    ])
    
    # AI-generated content
    talking_points = models.JSONField(default=list)
    conversation_starters = models.JSONField(default=list)
    confidence_boosters = models.JSONField(default=list)
    anxiety_reduction_tips = models.JSONField(default=list)
    
    # Contextual advice
    outfit_suggestions = models.JSONField(default=list)
    topic_suggestions = models.JSONField(default=list)
    timing_advice = models.TextField(blank=True)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.life_event.title} prep"

class EventFollowUp(models.Model):
    """Post-event analysis and support"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    life_event = models.ForeignKey(LifeEvent, on_delete=models.CASCADE)
    
    # Follow-up timing
    follow_up_triggered = models.BooleanField(default=False)
    follow_up_time = models.DateTimeField(null=True, blank=True)
    
    # User feedback
    user_feeling = models.CharField(max_length=20, blank=True)
    user_satisfaction = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Dissatisfied'), (2, 'Dissatisfied'), (3, 'Neutral'),
        (4, 'Satisfied'), (5, 'Very Satisfied')
    ])
    
    user_feedback = models.TextField(blank=True)
    
    # AI analysis
    ai_emotion_analysis = models.JSONField(default=dict)
    ai_performance_insights = models.TextField(blank=True)
    ai_improvement_areas = models.JSONField(default=list)
    ai_encouragement = models.TextField(blank=True)
    
    # Recommendations
    recommended_actions = models.JSONField(default=list)
    recommended_resources = models.JSONField(default=list)
    recommended_music = models.JSONField(default=list)
    
    # Support escalation
    needs_human_support = models.BooleanField(default=False)
    support_type_requested = models.CharField(max_length=30, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.life_event.title} follow-up"

class MusicRecommendation(models.Model):
    """Mood-based music recommendations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Recommendation context
    current_emotion = models.CharField(max_length=20)
    activity_context = models.CharField(max_length=30, choices=[
        ('working', 'Working'),
        ('relaxing', 'Relaxing'),
        ('exercising', 'Exercising'),
        ('socializing', 'Socializing'),
        ('studying', 'Studying'),
        ('commuting', 'Commuting'),
        ('preparing_event', 'Preparing for Event'),
        ('post_event', 'After Event')
    ])
    
    # Music details
    genre = models.CharField(max_length=50)
    mood = models.CharField(max_length=30)
    energy_level = models.IntegerField(choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Medium'),
        (4, 'High'), (5, 'Very High')
    ])
    
    # Recommendation data
    song_suggestions = models.JSONField(default=list)
    playlist_recommendations = models.JSONField(default=list)
    artist_recommendations = models.JSONField(default=list)
    
    # User feedback
    user_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Disliked'), (2, 'Neutral'), (3, 'Liked'), (4, 'Loved')
    ])
    
    user_skipped = models.BooleanField(default=False)
    user_listened_duration = models.IntegerField(default=0)  # minutes
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.genre} for {self.current_emotion}"

class RelationshipInsight(models.Model):
    """Relationship and social interaction insights"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Relationship context
    relationship_type = models.CharField(max_length=30, choices=[
        ('romantic', 'Romantic'),
        ('friendship', 'Friendship'),
        ('family', 'Family'),
        ('professional', 'Professional'),
        ('acquaintance', 'Acquaintance')
    ])
    
    person_name = models.CharField(max_length=100)
    interaction_context = models.CharField(max_length=200, blank=True)
    
    # Interaction tracking
    interaction_date = models.DateTimeField()
    interaction_type = models.CharField(max_length=20, choices=[
        ('date', 'Date'),
        ('meeting', 'Meeting'),
        ('conversation', 'Conversation'),
        ('conflict', 'Conflict'),
        ('celebration', 'Celebration'),
        ('support', 'Support Session')
    ])
    
    # Emotional analysis
    user_emotion_before = models.CharField(max_length=20, blank=True)
    user_emotion_after = models.CharField(max_length=20, blank=True)
    perceived_other_emotion = models.CharField(max_length=20, blank=True)
    
    # AI insights
    ai_relationship_analysis = models.TextField(blank=True)
    ai_communication_tips = models.JSONField(default=list)
    ai_conflict_resolution = models.JSONField(default=list)
    ai_connection_suggestions = models.JSONField(default=list)
    
    # Growth tracking
    relationship_strength_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Weak'), (2, 'Weak'), (3, 'Average'),
        (4, 'Strong'), (5, 'Very Strong')
    ])
    
    improvement_areas = models.JSONField(default=list)
    growth_moments = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.person_name} ({self.relationship_type})"

class SocialSkillDevelopment(models.Model):
    """Social skill tracking and improvement"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Skill categories
    skill_category = models.CharField(max_length=30, choices=[
        ('communication', 'Communication'),
        ('empathy', 'Empathy'),
        ('confidence', 'Confidence'),
        ('listening', 'Active Listening'),
        ('conflict_resolution', 'Conflict Resolution'),
        ('body_language', 'Body Language'),
        ('conversation_starting', 'Conversation Starting'),
        ('storytelling', 'Storytelling'),
        ('humor', 'Humor')
    ])
    
    # Skill assessment
    current_level = models.IntegerField(choices=[
        (1, 'Beginner'), (2, 'Novice'), (3, 'Intermediate'),
        (4, 'Advanced'), (5, 'Expert')
    ])
    
    target_level = models.IntegerField(choices=[
        (1, 'Beginner'), (2, 'Novice'), (3, 'Intermediate'),
        (4, 'Advanced'), (5, 'Expert')
    ])
    
    # Progress tracking
    practice_sessions = models.IntegerField(default=0)
    improvement_notes = models.TextField(blank=True)
    
    # AI coaching
    ai_skill_assessment = models.TextField(blank=True)
    ai_practice_exercises = models.JSONField(default=list)
    ai_improvement_plan = models.TextField(blank=True)
    
    # Milestones
    milestones_achieved = models.JSONField(default=list)
    next_milestone = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.skill_category} (Level {self.current_level})"
