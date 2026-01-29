from django.db import models
from django.contrib.auth.models import User
import json

class CompanionProfile(models.Model):
    """User's AI companion profile and personality"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Personality traits
    personality_type = models.CharField(max_length=20, choices=[
        ('caring_friend', 'Caring Friend'),
        ('supportive_mentor', 'Supportive Mentor'),
        ('intelligent_coach', 'Intelligent Coach'),
        ('motivational_guide', 'Motivational Guide'),
        ('empathetic_listener', 'Empathetic Listener')
    ], default='caring_friend')
    
    # Voice preferences
    preferred_voice = models.CharField(max_length=50, default='friendly_warm')
    voice_speed = models.FloatField(default=1.0)  # 0.5 to 2.0
    voice_pitch = models.FloatField(default=1.0)  # 0.5 to 2.0
    
    # Avatar preferences
    avatar_style = models.CharField(max_length=30, default='friendly')
    avatar_mood = models.CharField(max_length=20, default='happy')
    avatar_customization = models.JSONField(default=dict)
    
    # Communication style
    communication_tone = models.CharField(max_length=20, choices=[
        ('formal', 'Formal'),
        ('casual', 'Casual'),
        ('playful', 'Playful'),
        ('professional', 'Professional'),
        ('spiritual', 'Spiritual')
    ], default='casual')
    
    # Memory and learning
    remembers_preferences = models.JSONField(default=dict)
    relationship_depth = models.FloatField(default=0.0)  # 0-1 scale
    interaction_count = models.IntegerField(default=0)
    
    # Companion name
    companion_name = models.CharField(max_length=50, default='Abigael')
    
    def __str__(self):
        return f"{self.user.username}'s {self.companion_name}"

class Conversation(models.Model):
    """Chat and voice conversation logs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100)
    
    # Conversation metadata
    conversation_type = models.CharField(max_length=20, choices=[
        ('text', 'Text Chat'),
        ('voice', 'Voice Chat'),
        ('video', 'Video Call')
    ])
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Emotional context
    user_emotion_at_start = models.CharField(max_length=20)
    user_emotion_at_end = models.CharField(max_length=20, blank=True)
    emotional_improvement = models.FloatField(null=True, blank=True)
    
    # AI response data
    ai_responses_count = models.IntegerField(default=0)
    empathy_score = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.user.username} - {self.conversation_type} at {self.started_at}"

class Message(models.Model):
    """Individual messages within conversations"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    # Message content
    message_type = models.CharField(max_length=10, choices=[
        ('user', 'User'),
        ('ai', 'AI Companion')
    ])
    content = models.TextField()
    
    # Timestamp and metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # AI-specific data
    if message_type == 'ai':
        emotion_detected = models.CharField(max_length=20, blank=True)
        empathy_level = models.FloatField(default=0.0)
        response_strategy = models.CharField(max_length=50, blank=True)
        personalization_applied = models.BooleanField(default=False)
    
    # User-specific data
    if message_type == 'user':
        user_emotion = models.CharField(max_length=20, blank=True)
        sentiment_score = models.FloatField(null=True, blank=True)
        crisis_indicators = models.JSONField(default=list)
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."

class JournalEntry(models.Model):
    """Memory journal for moods, events, and reflections"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Entry metadata
    entry_date = models.DateField()
    entry_time = models.DateTimeField(auto_now_add=True)
    entry_type = models.CharField(max_length=20, choices=[
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('reflection', 'Reflection'),
        ('milestone', 'Milestone')
    ])
    
    # Emotional data
    primary_emotion = models.CharField(max_length=20)
    emotion_intensity = models.FloatField(default=0.0)  # 0-1 scale
    emotion_notes = models.TextField(blank=True)
    
    # Life events
    life_events = models.JSONField(default=list)
    key_moments = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    
    # Reflections
    personal_reflection = models.TextField(blank=True)
    ai_insights = models.TextField(blank=True)
    gratitude_notes = models.TextField(blank=True)
    
    # AI analysis
    sentiment_analysis = models.JSONField(default=dict)
    pattern_recognition = models.JSONField(default=dict)
    recommendations = models.JSONField(default=list)
    
    class Meta:
        unique_together = ['user', 'entry_date']
    
    def __str__(self):
        return f"{self.user.username} - Journal {self.entry_date}"

class LifeCoachingSession(models.Model):
    """Life coaching and mentorship sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Session details
    coaching_area = models.CharField(max_length=30, choices=[
        ('fitness', 'Fitness & Health'),
        ('career', 'Career Development'),
        ('studies', 'Education & Learning'),
        ('productivity', 'Productivity & Time Management'),
        ('relationships', 'Relationships'),
        ('mental_health', 'Mental Health'),
        ('personal_growth', 'Personal Growth'),
        ('spiritual', 'Spiritual Wellness')
    ])
    
    session_date = models.DateTimeField(auto_now_add=True)
    session_duration = models.IntegerField(default=30)  # minutes
    
    # Coaching content
    goals_discussed = models.JSONField(default=list)
    challenges_identified = models.JSONField(default=list)
    strategies_provided = models.JSONField(default=list)
    action_items = models.JSONField(default=list)
    
    # Progress tracking
    progress_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')
    ])
    
    # AI coach notes
    ai_coaching_notes = models.TextField(blank=True)
    personalized_advice = models.TextField(blank=True)
    follow_up_needed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.coaching_area} coaching"

class StreakTracker(models.Model):
    """Gamification: tracks user consistency and engagement"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Streak data
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField()
    
    # Activity types
    daily_checkins = models.IntegerField(default=0)
    journal_entries = models.IntegerField(default=0)
    coaching_sessions = models.IntegerField(default=0)
    conversations_completed = models.IntegerField(default=0)
    
    # Rewards and achievements
    points_earned = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    badges_earned = models.JSONField(default=list)
    
    # Motivation data
    motivation_score = models.FloatField(default=0.0)
    engagement_rate = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.user.username} - {self.current_streak} day streak"

class Achievement(models.Model):
    """Gamification: achievements and rewards"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    points_value = models.IntegerField(default=0)
    
    # Achievement criteria
    achievement_type = models.CharField(max_length=20, choices=[
        ('streak', 'Streak Based'),
        ('journal', 'Journal Based'),
        ('coaching', 'Coaching Based'),
        ('conversation', 'Conversation Based'),
        ('milestone', 'Milestone Based')
    ])
    
    criteria = models.JSONField(default=dict)  # Requirements to unlock
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    """Link between users and earned achievements"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    
    earned_date = models.DateTimeField(auto_now_add=True)
    progress = models.FloatField(default=0.0)  # 0-1 for partial progress
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"

class HumanSupportAgent(models.Model):
    """Human support agents for the Abigael Assist Team"""
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=30, choices=[
        ('peer_support', 'Peer Support Agent'),
        ('wellness_coach', 'Wellness Coach'),
        ('aa_mentor', 'AA-Style Mentor'),
        ('crisis_specialist', 'Crisis Specialist')
    ])
    
    # Availability
    is_available = models.BooleanField(default=True)
    max_concurrent_sessions = models.IntegerField(default=3)
    current_sessions = models.IntegerField(default=0)
    
    # Expertise
    specialties = models.JSONField(default=list)
    languages_spoken = models.JSONField(default=lambda: ['English'])
    
    # Contact methods
    preferred_contact_methods = models.JSONField(default=list)
    response_time_minutes = models.IntegerField(default=30)
    
    def __str__(self):
        return f"{self.name} - {self.role}"

class SupportSession(models.Model):
    """Human support sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    agent = models.ForeignKey(HumanSupportAgent, on_delete=models.CASCADE)
    
    # Session details
    session_type = models.CharField(max_length=20, choices=[
        ('chat', 'Chat'),
        ('voice', 'Voice Call'),
        ('video', 'Video Call')
    ])
    
    scheduled_time = models.DateTimeField()
    duration_minutes = models.IntegerField()
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ])
    
    # Session content
    topics_discussed = models.JSONField(default=list)
    user_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')
    ])
    
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.agent.name} session"

class CrisisDetection(models.Model):
    """Crisis detection and escalation system"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Detection data
    detected_at = models.DateTimeField(auto_now_add=True)
    crisis_type = models.CharField(max_length=30, choices=[
        ('emotional_crisis', 'Emotional Crisis'),
        ('mental_health', 'Mental Health Concern'),
        ('addiction', 'Addiction Issue'),
        ('suicidal_ideation', 'Suicidal Ideation'),
        ('abuse', 'Abuse Situation')
    ])
    
    # Trigger data
    trigger_keywords = models.JSONField(default=list)
    emotion_indicators = models.JSONField(default=dict)
    behavioral_patterns = models.JSONField(default=list)
    
    # Escalation
    severity_level = models.IntegerField(choices=[
        (1, 'Low Concern'),
        (2, 'Moderate Concern'),
        (3, 'High Concern'),
        (4, 'Urgent'),
        (5, 'Emergency')
    ])
    
    escalated_to_human = models.BooleanField(default=False)
    human_contact_made = models.BooleanField(default=False)
    resolution_status = models.CharField(max_length=20, default='pending')
    
    def __str__(self):
        return f"{self.user.username} - {self.crisis_type} ({self.severity_level})"

class DailyCompanionInteraction(models.Model):
    """Daily companion system: greetings, reminders, reflections"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Daily interactions
    morning_greeting_sent = models.BooleanField(default=False)
    morning_greeting_response = models.TextField(blank=True)
    
    evening_reflection_sent = models.BooleanField(default=False)
    evening_reflection_response = models.TextField(blank=True)
    
    # Reminders
    reminders_sent = models.JSONField(default=list)
    reminder_responses = models.JSONField(default=list)
    
    # Daily insights
    daily_insight = models.TextField(blank=True)
    user_mood_summary = models.JSONField(default=dict)
    
    # Engagement metrics
    interaction_quality = models.FloatField(default=0.0)
    user_satisfaction = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - Daily companion {self.date}"
