from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class ExtendedLifeEvent(models.Model):
    """Extended life events with comprehensive event types and AI support"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Comprehensive event categories
    event_category = models.CharField(max_length=30, choices=[
        ('professional', 'Professional'),
        ('personal', 'Personal'),
        ('social', 'Social'),
        ('health', 'Health & Wellness'),
        ('financial', 'Financial'),
        ('educational', 'Educational'),
        ('creative', 'Creative'),
        ('spiritual', 'Spiritual'),
        ('recreational', 'Recreational'),
        ('family', 'Family'),
        ('relationship', 'Relationship'),
        ('community', 'Community')
    ])
    
    # Detailed event types
    event_type = models.CharField(max_length=40, choices=[
        # Professional Events
        ('meeting', 'Business Meeting'),
        ('interview', 'Job Interview'),
        ('presentation', 'Presentation'),
        ('networking', 'Networking Event'),
        ('conference', 'Conference'),
        ('workshop', 'Workshop'),
        ('training', 'Training Session'),
        ('performance_review', 'Performance Review'),
        ('client_call', 'Client Call'),
        ('team_building', 'Team Building'),
        
        # Personal Events
        ('therapy_session', 'Therapy Session'),
        ('meditation', 'Meditation Session'),
        ('exercise', 'Exercise/Workout'),
        ('meal_planning', 'Meal Planning'),
        ('home_organization', 'Home Organization'),
        ('shopping', 'Shopping Trip'),
        ('personal_reflection', 'Personal Reflection'),
        ('goal_setting', 'Goal Setting Session'),
        ('habit_formation', 'Habit Formation'),
        ('self_care', 'Self-Care Activity'),
        
        # Social Events
        ('date', 'Date'),
        ('party', 'Party/Gathering'),
        ('dinner_with_friends', 'Dinner with Friends'),
        ('coffee_meeting', 'Coffee Meeting'),
        ('social_sports', 'Social Sports'),
        ('book_club', 'Book Club'),
        ('game_night', 'Game Night'),
        ('volunteer_event', 'Volunteer Event'),
        ('community_meeting', 'Community Meeting'),
        ('reunion', 'Reunion'),
        
        # Health & Wellness
        ('doctor_appointment', 'Doctor Appointment'),
        ('dental_appointment', 'Dental Appointment'),
        ('specialist_visit', 'Specialist Visit'),
        ('medical_test', 'Medical Test'),
        ('vaccination', 'Vaccination'),
        ('health_screening', 'Health Screening'),
        ('mental_health_check', 'Mental Health Check'),
        ('fitness_class', 'Fitness Class'),
        ('yoga_session', 'Yoga Session'),
        ('massage', 'Massage Therapy'),
        
        # Financial Events
        ('budget_review', 'Budget Review'),
        ('investment_meeting', 'Investment Meeting'),
        ('tax_preparation', 'Tax Preparation'),
        ('bank_appointment', 'Bank Appointment'),
        ('loan_application', 'Loan Application'),
        ('financial_planning', 'Financial Planning'),
        ('purchase_decision', 'Major Purchase Decision'),
        ('bill_payment', 'Bill Payment Session'),
        ('salary_negotiation', 'Salary Negotiation'),
        ('insurance_review', 'Insurance Review'),
        
        # Educational Events
        ('class', 'Class/Lecture'),
        ('study_session', 'Study Session'),
        ('exam', 'Exam/Test'),
        ('tutoring', 'Tutoring Session'),
        ('research', 'Research Session'),
        ('online_course', 'Online Course'),
        ('skill_learning', 'Skill Learning'),
        ('language_practice', 'Language Practice'),
        ('certification', 'Certification Exam'),
        ('academic_advising', 'Academic Advising'),
        
        # Creative Events
        ('art_session', 'Art/Creative Session'),
        ('music_practice', 'Music Practice'),
        ('writing_session', 'Writing Session'),
        ('photography', 'Photography Session'),
        ('crafting', 'Crafting/Hobby'),
        ('creative_workshop', 'Creative Workshop'),
        ('performance', 'Performance/Show'),
        ('exhibition', 'Exhibition/Show'),
        ('brainstorming', 'Brainstorming Session'),
        ('creative_collaboration', 'Creative Collaboration'),
        
        # Spiritual Events
        ('religious_service', 'Religious Service'),
        ('meditation_retreat', 'Meditation Retreat'),
        ('spiritual_counseling', 'Spiritual Counseling'),
        ('prayer_session', 'Prayer Session'),
        ('spiritual_study', 'Spiritual Study'),
        ('mindfulness_practice', 'Mindfulness Practice'),
        ('spiritual_community', 'Spiritual Community Event'),
        ('retreat', 'Spiritual Retreat'),
        ('ceremony', 'Ceremony/Ritual'),
        ('spiritual_guidance', 'Spiritual Guidance'),
        
        # Recreational Events
        ('sports_game', 'Sports Game'),
        ('hiking', 'Hiking/Outdoor Activity'),
        ('movie_theater', 'Movie Theater'),
        ('concert', 'Concert'),
        ('museum_visit', 'Museum Visit'),
        ('park_visit', 'Park Visit'),
        ('vacation', 'Vacation'),
        ('day_trip', 'Day Trip'),
        ('recreational_class', 'Recreational Class'),
        ('leisure_activity', 'Leisure Activity'),
        
        # Family Events
        ('family_dinner', 'Family Dinner'),
        ('family_celebration', 'Family Celebration'),
        ('parent_teacher_meeting', 'Parent-Teacher Meeting'),
        ('family_counseling', 'Family Counseling'),
        ('family_outing', 'Family Outing'),
        ('holiday_gathering', 'Holiday Gathering'),
        ('family_game_night', 'Family Game Night'),
        ('family_project', 'Family Project'),
        ('childcare', 'Childcare Activity'),
        ('family_tradition', 'Family Tradition Event'),
        
        # Relationship Events
        ('anniversary', 'Anniversary'),
        ('relationship_counseling', 'Relationship Counseling'),
        ('couples_activity', 'Couples Activity'),
        ('relationship_checkin', 'Relationship Check-in'),
        ('date_night', 'Date Night'),
        ('relationship_milestone', 'Relationship Milestone'),
        ('conflict_resolution', 'Conflict Resolution Session'),
        ('relationship_planning', 'Relationship Planning'),
        ('intimacy_building', 'Intimacy Building Activity'),
        ('relationship_celebration', 'Relationship Celebration'),
        
        # Community Events
        ('neighborhood_meeting', 'Neighborhood Meeting'),
        ('local_event', 'Local Community Event'),
        ('civic_engagement', 'Civic Engagement'),
        ('charity_event', 'Charity Event'),
        ('community_service', 'Community Service'),
        ('local_government', 'Local Government Meeting'),
        ('community_class', 'Community Class'),
        ('public_speaking', 'Public Speaking Event'),
        ('community_leadership', 'Community Leadership Activity'),
        ('neighborhood_help', 'Neighborhood Help Activity')
    ])
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Timing details
    event_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    reminder_minutes = models.IntegerField(default=30)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Location and context
    location = models.CharField(max_length=200, blank=True)
    virtual_meeting = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True)
    participants = models.JSONField(default=list)
    
    # Preparation requirements
    preparation_needed = models.TextField(blank=True)
    preparation_completed = models.BooleanField(default=False)
    materials_needed = models.JSONField(default=list)
    dress_code = models.CharField(max_length=100, blank=True)
    
    # Emotional and psychological context
    expected_emotion = models.CharField(max_length=20, default='neutral')
    anxiety_level = models.IntegerField(choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Moderate'),
        (4, 'High'), (5, 'Very High')
    ], default=2)
    
    confidence_level = models.IntegerField(choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Moderate'),
        (4, 'High'), (5, 'Very High')
    ], default=3)
    
    importance_level = models.IntegerField(choices=[
        (1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Very High'), (5, 'Critical')
    ], default=3)
    
    # Outcome tracking
    actual_emotion_before = models.CharField(max_length=20, blank=True)
    actual_emotion_after = models.CharField(max_length=20, blank=True)
    outcome_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Poor'), (2, 'Poor'), (3, 'Average'), 
        (4, 'Good'), (5, 'Very Good'), (6, 'Excellent')
    ])
    
    outcome_notes = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    unexpected_outcomes = models.TextField(blank=True)
    
    # AI assistance and analysis
    ai_preparation_advice = models.TextField(blank=True)
    ai_followup_insights = models.TextField(blank=True)
    ai_improvement_suggestions = models.TextField(blank=True)
    ai_emotional_support = models.TextField(blank=True)
    ai_success_probability = models.FloatField(null=True, blank=True)
    
    # Health and wellness tracking
    physical_energy_before = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Moderate'),
        (4, 'High'), (5, 'Very High')
    ])
    
    physical_energy_after = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Moderate'),
        (4, 'High'), (5, 'Very High')
    ])
    
    stress_level_before = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Moderate'),
        (4, 'High'), (5, 'Very High')
    ])
    
    stress_level_after = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Very Low'), (2, 'Low'), (3, 'Moderate'),
        (4, 'High'), (5, 'Very High')
    ])
    
    # Financial tracking
    cost_involved = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    financial_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    return_on_investment = models.FloatField(null=True, blank=True)
    
    # Learning and growth
    skills_practiced = models.JSONField(default=list)
    knowledge_gained = models.TextField(blank=True)
    personal_growth_areas = models.JSONField(default=list)
    
    # Social and relationship impact
    relationships_affected = models.JSONField(default=list)
    social_connections_made = models.JSONField(default=list)
    community_impact = models.TextField(blank=True)
    
    # Status and completion
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('preparing', 'Preparing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
        ('no_show', 'No Show')
    ], default='scheduled')
    
    attendance_confirmed = models.BooleanField(default=False)
    follow_up_required = models.BooleanField(default=False)
    follow_up_completed = models.BooleanField(default=False)
    
    # Recurrence and patterns
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.JSONField(default=dict)
    related_events = models.JSONField(default=list)
    
    # External integrations
    calendar_event_id = models.CharField(max_length=100, blank=True)
    video_conference_id = models.CharField(max_length=100, blank=True)
    external_links = models.JSONField(default=list)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['event_date']
        indexes = [
            models.Index(fields=['user', 'event_date']),
            models.Index(fields=['event_category', 'event_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.get_event_type_display()})"

class EventTemplate(models.Model):
    """Pre-defined event templates for quick creation"""
    name = models.CharField(max_length=100)
    event_category = models.CharField(max_length=30, choices=ExtendedLifeEvent.event_category.choices)
    event_type = models.CharField(max_length=40, choices=ExtendedLifeEvent.event_type.choices)
    
    # Template content
    default_title = models.CharField(max_length=200)
    default_description = models.TextField(blank=True)
    default_duration = models.IntegerField(default=60)
    default_reminder = models.IntegerField(default=30)
    
    # Preparation templates
    preparation_checklist = models.JSONField(default=list)
    common_materials = models.JSONField(default=list)
    typical_dress_code = models.CharField(max_length=100, blank=True)
    
    # Emotional preparation
    common_anxieties = models.JSONField(default=list)
    confidence_boosters = models.JSONField(default=list)
    success_indicators = models.JSONField(default=list)
    
    # Follow-up questions
    standard_followup_questions = models.JSONField(default=list)
    success_metrics = models.JSONField(default=list)
    
    # AI prompts
    preparation_prompt_template = models.TextField(blank=True)
    followup_prompt_template = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_event_type_display()}"

class EventOutcomePattern(models.Model):
    """Tracks patterns in event outcomes for better predictions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_category = models.CharField(max_length=30)
    event_type = models.CharField(max_length=40)
    
    # Pattern data
    total_events = models.IntegerField(default=0)
    average_outcome = models.FloatField(null=True, blank=True)
    success_rate = models.FloatField(default=0.0)
    
    # Emotional patterns
    common_before_emotions = models.JSONField(default=list)
    common_after_emotions = models.JSONField(default=list)
    emotion_improvement_rate = models.FloatField(default=0.0)
    
    # Context patterns
    optimal_times = models.JSONField(default=list)
    optimal_durations = models.JSONField(default=list)
    success_factors = models.JSONField(default=list)
    failure_factors = models.JSONField(default=list)
    
    # Predictions
    predicted_success_probability = models.FloatField(default=0.5)
    confidence_level = models.FloatField(default=0.0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'event_category', 'event_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} patterns"

class EventResource(models.Model):
    """Resources and materials for different event types"""
    event_category = models.CharField(max_length=30)
    event_type = models.CharField(max_length=40)
    
    resource_type = models.CharField(max_length=30, choices=[
        ('article', 'Article'),
        ('video', 'Video'),
        ('book', 'Book'),
        ('template', 'Template'),
        ('checklist', 'Checklist'),
        ('exercise', 'Exercise'),
        ('meditation', 'Meditation'),
        ('tool', 'Tool'),
        ('app', 'App'),
        ('service', 'Service')
    ])
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    
    # Resource details
    difficulty_level = models.IntegerField(choices=[
        (1, 'Beginner'), (2, 'Intermediate'), (3, 'Advanced')
    ])
    time_required = models.IntegerField(help_text="Minutes to complete")
    
    # Usage tracking
    usage_count = models.IntegerField(default=0)
    average_rating = models.FloatField(null=True, blank=True)
    
    # Tags and categorization
    tags = models.JSONField(default=list)
    target_emotions = models.JSONField(default=list)
    benefits = models.JSONField(default=list)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.get_event_type_display()}"
