from django.db import models
from django.contrib.auth.models import User
import json
import numpy as np

class EmotionEvent(models.Model):
    """Unified emotion event table for all sensors"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Emotion data
    emotion = models.CharField(max_length=20)
    confidence = models.FloatField(default=0.0)
    
    # Source information
    source = models.CharField(max_length=20)  # 'facial', 'voice', 'typing', 'biofeedback'
    source_confidence = models.FloatField(default=0.0)
    
    # Contextual data
    current_task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    context_data = models.JSONField(default=dict)  # Additional sensor-specific data
    
    # Raw sensor data for ML training
    raw_features = models.JSONField(default=dict)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['emotion', 'timestamp']),
            models.Index(fields=['source', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion} ({self.source}) at {self.timestamp}"

class TaskFeedback(models.Model):
    """User feedback on task completion and emotional state"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Feedback ratings
    task_satisfaction = models.IntegerField(choices=[(1, 'Very Dissatisfied'), (2, 'Dissatisfied'), (3, 'Neutral'), (4, 'Satisfied'), (5, 'Very Satisfied')])
    emotion_before = models.CharField(max_length=20)
    emotion_after = models.CharField(max_length=20)
    emotion_change_rating = models.IntegerField(choices=[(-2, 'Much Worse'), (-1, 'Worse'), (0, 'Same'), (1, 'Better'), (2, 'Much Better')])
    
    # Performance metrics
    completion_time_minutes = models.FloatField()
    perceived_difficulty = models.IntegerField(choices=[(1, 'Very Easy'), (2, 'Easy'), (3, 'Medium'), (4, 'Hard'), (5, 'Very Hard')])
    focus_level = models.IntegerField(choices=[(1, 'Very Distracted'), (2, 'Distracted'), (3, 'Neutral'), (4, 'Focused'), (5, 'Very Focused')])
    
    # AI message feedback
    ai_helpfulness = models.IntegerField(choices=[(1, 'Not Helpful'), (2, 'Slightly Helpful'), (3, 'Neutral'), (4, 'Helpful'), (5, 'Very Helpful')])
    ai_tone_preference = models.CharField(max_length=20, choices=[('formal', 'Formal'), ('casual', 'Casual'), ('motivational', 'Motivational'), ('empathetic', 'Empathetic')])
    
    # Calculated reward for RL
    reward_score = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.user.username} - {self.task.title} feedback"

class RLModel(models.Model):
    """Reinforcement Learning model storage"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=50)
    model_version = models.IntegerField(default=1)
    
    # Model parameters (stored as JSON)
    weights = models.JSONField(default=dict)
    hyperparameters = models.JSONField(default=dict)
    
    # Performance metrics
    accuracy = models.FloatField(default=0.0)
    reward_total = models.FloatField(default=0.0)
    episodes_trained = models.IntegerField(default=0)
    
    # Training metadata
    last_training = models.DateTimeField(auto_now=True)
    training_data_points = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'model_name']
    
    def __str__(self):
        return f"{self.user.username} - {self.model_name} v{self.model_version}"

class FederatedLearningNode(models.Model):
    """Federated learning participant node"""
    node_id = models.CharField(max_length=100, unique=True)
    organization = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Node statistics
    total_contributions = models.IntegerField(default=0)
    last_contribution = models.DateTimeField(null=True, blank=True)
    
    # Privacy settings
    data_retention_days = models.IntegerField(default=30)
    anonymization_level = models.CharField(max_length=20, choices=[('basic', 'Basic'), ('standard', 'Standard'), ('strict', 'Strict')], default='standard')
    
    def __str__(self):
        return f"Node {self.node_id}"

class FederatedModelUpdate(models.Model):
    """Federated learning model updates"""
    node = models.ForeignKey(FederatedLearningNode, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=50)
    
    # Update data (anonymized)
    weight_updates = models.JSONField(default=dict)
    performance_metrics = models.JSONField(default=dict)
    
    # Metadata
    contribution_size = models.IntegerField(default=0)  # Number of data points
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Quality assessment
    quality_score = models.FloatField(default=0.0)
    is_accepted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.node.node_id} - {self.model_name} update"

class KnowledgeGraph(models.Model):
    """Personal emotional productivity knowledge graph"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Graph nodes and relationships
    entity_type = models.CharField(max_length=20)  # 'emotion', 'task_type', 'time_period', 'context'
    entity_name = models.CharField(max_length=100)
    
    # Relationships
    related_entities = models.JSONField(default=list)  # List of related entity IDs
    relationship_strength = models.JSONField(default=dict)  # Strength of each relationship
    relationship_type = models.JSONField(default=dict)  # Type of each relationship
    
    # Performance data
    success_rate = models.FloatField(default=0.0)
    average_completion_time = models.FloatField(default=0.0)
    emotion_improvement_score = models.FloatField(default=0.0)
    
    # Graph metrics
    centrality_score = models.FloatField(default=0.0)
    cluster_membership = models.CharField(max_length=50, blank=True)
    
    # Temporal data
    last_updated = models.DateTimeField(auto_now=True)
    data_points_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'entity_type', 'entity_name']
    
    def __str__(self):
        return f"{self.user.username} - {self.entity_type}:{self.entity_name}"

class AutoConfiguration(models.Model):
    """Self-configuration parameters"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Configuration categories
    category = models.CharField(max_length=50)  # 'ml_model', 'ui_theme', 'scheduler', 'cache'
    parameter_name = models.CharField(max_length=100)
    parameter_value = models.JSONField(default=dict)
    
    # Auto-tuning metadata
    last_adjusted = models.DateTimeField(auto_now=True)
    adjustment_reason = models.TextField(blank=True)
    performance_impact = models.FloatField(default=0.0)
    
    # Optimization settings
    optimization_target = models.CharField(max_length=50, choices=[('accuracy', 'Accuracy'), ('speed', 'Speed'), ('satisfaction', 'Satisfaction'), ('efficiency', 'Efficiency')])
    is_auto_tuned = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'category', 'parameter_name']
    
    def __str__(self):
        return f"{self.user.username} - {self.category}.{self.parameter_name}"

class UserGoal(models.Model):
    """Long-term user goals predicted by the system"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Goal details
    goal_title = models.CharField(max_length=200)
    goal_description = models.TextField(blank=True)
    goal_category = models.CharField(max_length=50)  # 'career', 'health', 'learning', 'productivity'
    
    # Temporal information
    target_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    
    # Prediction confidence
    prediction_confidence = models.FloatField(default=0.0)
    prediction_basis = models.JSONField(default=dict)  # Data used for prediction
    
    # Progress tracking
    current_progress = models.FloatField(default=0.0)  # 0-100%
    milestone_tasks = models.JSONField(default=list)  # Related tasks
    completion_probability = models.FloatField(default=0.0)
    
    # System recommendations
    recommended_actions = models.JSONField(default=list)
    optimal_emotional_states = models.JSONField(default=list)
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.goal_title}"

class WeeklyReport(models.Model):
    """AI-generated weekly knowledge reports"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start = models.DateField()
    week_end = models.DateField()
    
    # Report content
    summary_highlights = models.JSONField(default=list)
    emotion_patterns = models.JSONField(default=dict)
    productivity_insights = models.JSONField(default=dict)
    recommendations = models.JSONField(default=list)
    
    # Generated content
    ai_summary = models.TextField()
    personalized_tips = models.JSONField(default=list)
    trend_analysis = models.JSONField(default=dict)
    
    # Engagement metrics
    was_read = models.BooleanField(default=False)
    user_rating = models.IntegerField(null=True, blank=True, choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')])
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'week_start']
    
    def __str__(self):
        return f"{self.user.username} - Report {self.week_start}"

class IndustryTrend(models.Model):
    """Aggregated industry-wide patterns"""
    industry = models.CharField(max_length=100)
    trend_type = models.CharField(max_length=50)  # 'peak_focus_time', 'productivity_pattern', 'emotion_correlation'
    
    # Trend data
    pattern_data = models.JSONField(default=dict)
    confidence_level = models.FloatField(default=0.0)
    sample_size = models.IntegerField(default=0)
    
    # Temporal information
    observation_period = models.CharField(max_length=20)  # 'daily', 'weekly', 'monthly'
    last_updated = models.DateTimeField(auto_now=True)
    
    # Applicability
    applicable_roles = models.JSONField(default=list)
    optimization_hints = models.JSONField(default=list)
    
    def __str__(self):
        return f"{self.industry} - {self.trend_type}"
