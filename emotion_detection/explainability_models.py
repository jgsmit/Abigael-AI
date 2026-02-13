"""
Explainability and Insights Models

Tracks the reasoning behind recommendations and generates insights about
user patterns, intervention effectiveness, and confidence scores.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Avg, Count, Q
from datetime import timedelta


class ExplainabilitySignal(models.Model):
    """Records the "why" behind an intervention trigger for transparency."""
    
    intervention = models.OneToOneField(
        'emotion_detection.UserIntervention',
        on_delete=models.CASCADE,
        related_name='explainability_signal'
    )
    
    # Primary trigger reason
    trigger_reason = models.CharField(max_length=100, choices=[
        ('emotion_match', 'Matched emotional state'),
        ('stress_threshold', 'Stress level exceeded threshold'),
        ('inactivity', 'User inactivity detected'),
        ('time_window', 'Scheduled time window'),
        ('pattern_detected', 'Pattern detected in history'),
        ('biofeedback_anomaly', 'Physiological anomaly detected'),
        ('user_pattern', 'Personalized user pattern'),
        ('multi_factor', 'Multiple factors combined'),
    ])
    
    # Detailed explanation
    explanation = models.TextField(help_text="Human-readable explanation of why this intervention was triggered")
    
    # Confidence and evidence
    confidence_score = models.FloatField(default=0.5, help_text="0-1 scale: how confident is this recommendation")
    evidence_points = models.JSONField(default=list, help_text="List of evidence supporting this recommendation")
    
    # Factual data at time of triggering
    user_state_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of user state: {emotion, stress_level, sleep_quality, hr, activity_level, etc}"
    )
    
    # Rule information
    rule_code = models.CharField(max_length=100, blank=True, help_text="Reference to InterventionRule that triggered")
    rule_priority = models.IntegerField(null=True, blank=True, help_text="Priority of the matching rule")
    
    # Historical context
    historical_effectiveness = models.FloatField(
        null=True,
        blank=True,
        help_text="0-1: Historical success rate of this intervention for similar situations"
    )
    
    # Alternative recommendations
    alternatives_considered = models.JSONField(
        default=list,
        help_text="Other interventions considered but not selected"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.intervention.user.username} - {self.trigger_reason}"


class InterventionEffectiveness(models.Model):
    """Tracks effectiveness of interventions across different situations."""
    
    rule = models.OneToOneField(
        'emotion_detection.InterventionRule',
        on_delete=models.CASCADE,
        related_name='effectiveness_stats'
    )
    
    # Overall stats
    total_triggered = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    total_rated = models.IntegerField(default=0)
    
    # Success metrics
    completion_rate = models.FloatField(default=0.0, help_text="0-1: completed / triggered")
    avg_user_rating = models.FloatField(default=0.0, help_text="0-5: average rating")
    helpful_rate = models.FloatField(default=0.0, help_text="0-1: was_helpful / completed")
    
    # Effectiveness by emotion
    effectiveness_by_emotion = models.JSONField(
        default=dict,
        help_text='{"anxiety": {"success": 7, "total": 10}, ...}'
    )
    
    # Trending
    trend = models.CharField(max_length=20, choices=[
        ('improving', 'Effectiveness improving'),
        ('declining', 'Effectiveness declining'),
        ('stable', 'Effectiveness stable'),
    ], default='stable')
    
    last_calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Intervention Effectiveness"
    
    def __str__(self):
        return f"{self.rule.name} - {self.completion_rate*100:.0f}% completion"
    
    def calculate_effectiveness(self):
        """Recalculate all effectiveness metrics."""
        from emotion_detection.models import UserIntervention, JournalEntry
        
        # Get all completions for this rule
        interventions = UserIntervention.objects.filter(rule=self.rule)
        
        self.total_triggered = interventions.count()
        self.total_completed = interventions.filter(completed=True).count()
        self.total_rated = interventions.filter(user_rating__isnull=False).count()
        
        if self.total_triggered > 0:
            self.completion_rate = self.total_completed / self.total_triggered
        
        if self.total_completed > 0:
            self.helpful_rate = interventions.filter(
                completed=True,
                was_helpful=True
            ).count() / self.total_completed
            
            ratings = list(interventions.filter(
                completed=True,
                user_rating__isnull=False
            ).values_list('user_rating', flat=True))
            
            if ratings:
                self.avg_user_rating = sum(ratings) / len(ratings)
        
        # Calculate by emotion
        self.effectiveness_by_emotion = self._calculate_by_emotion()
        
        # Determine trend (last 30 vs 30 before)
        self.trend = self._calculate_trend()
        
        self.save()
    
    def _calculate_by_emotion(self) -> dict:
        """Calculate effectiveness broken down by emotion."""
        from emotion_detection.models import UserIntervention
        
        emotion_stats = {}
        interventions = UserIntervention.objects.filter(
            rule=self.rule,
            completed=True
        ).select_related('explainability_signal')
        
        for intervention in interventions:
            state = intervention.explainability_signal.user_state_snapshot if intervention.explainability_signal else {}
            emotion = state.get('emotion', 'unknown')
            
            if emotion not in emotion_stats:
                emotion_stats[emotion] = {'completed': 0, 'total': 0, 'helpful': 0}
            
            emotion_stats[emotion]['total'] += 1
            if intervention.completed:
                emotion_stats[emotion]['completed'] += 1
            if intervention.was_helpful:
                emotion_stats[emotion]['helpful'] += 1
        
        return emotion_stats
    
    def _calculate_trend(self) -> str:
        """Calculate trend by comparing old vs recent performance."""
        from emotion_detection.models import UserIntervention
        
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        two_months_ago = now - timedelta(days=60)
        
        recent = UserIntervention.objects.filter(
            rule=self.rule,
            triggered_at__gte=month_ago
        )
        
        older = UserIntervention.objects.filter(
            rule=self.rule,
            triggered_at__range=[two_months_ago, month_ago]
        )
        
        recent_rate = (recent.filter(was_helpful=True).count() / max(1, recent.count())) if recent.count() > 0 else 0.5
        older_rate = (older.filter(was_helpful=True).count() / max(1, older.count())) if older.count() > 0 else 0.5
        
        if recent_rate > older_rate * 1.1:
            return 'improving'
        elif recent_rate < older_rate * 0.9:
            return 'declining'
        return 'stable'


class UserPattern(models.Model):
    """Detected patterns in user behavior for personalized insights."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='detected_patterns')
    
    PATTERN_TYPES = [
        ('daily_stress_peak', 'Daily stress peak time'),
        ('emotion_cycle', 'Emotion cycle'),
        ('sleep_impact', 'Sleep quality impact'),
        ('intervention_response', 'Intervention response pattern'),
        ('activity_trigger', 'Activity-emotion link'),
        ('social_pattern', 'Social interaction pattern'),
        ('weather_impact', 'Weather/season impact'),
        ('routine_effect', 'Routine/habit effect'),
    ]
    
    pattern_type = models.CharField(max_length=50, choices=PATTERN_TYPES)
    description = models.TextField(help_text="Human-readable description of the pattern")
    
    # Pattern details
    details = models.JSONField(default=dict, help_text="Pattern-specific data (times, emotions, triggers, etc)")
    
    # Confidence
    confidence = models.FloatField(default=0.0, help_text="0-1: How confident is this pattern detection")
    sample_size = models.IntegerField(default=0, help_text="Number of observations supporting this pattern")
    
    # Impact and suggestions
    impact_description = models.TextField(blank=True, help_text="How this pattern affects the user")
    suggested_action = models.TextField(blank=True, help_text="Suggested action based on pattern")
    
    # Personalization recommendations
    recommended_interventions = models.JSONField(
        default=list,
        help_text="Intervention rule IDs that match this pattern"
    )
    
    # Lifecycle
    detected_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-confidence', '-detected_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_pattern_type_display()}"


class Insight(models.Model):
    """Generated insights about user's mental health and app usage."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insights')
    
    INSIGHT_CATEGORIES = [
        ('mood_trend', 'Mood Trend'),
        ('effectiveness', 'Intervention Effectiveness'),
        ('pattern', 'Behavior Pattern'),
        ('correlation', 'Correlation Found'),
        ('recommendation', 'Recommendation'),
        ('milestone', 'Milestone Achieved'),
        ('concern', 'Concern Alert'),
    ]
    
    category = models.CharField(max_length=50, choices=INSIGHT_CATEGORIES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Visual representation
    insight_type = models.CharField(max_length=50, choices=[
        ('statistic', 'Single Statistic'),
        ('trend', 'Trend Over Time'),
        ('comparison', 'Comparison'),
        ('correlation', 'Correlation'),
        ('recommendation', 'Recommendation'),
    ])
    
    # Data for visualization
    data = models.JSONField(default=dict, help_text="Data points for charts/graphs")
    
    # Confidence and relevance
    confidence = models.FloatField(default=0.5, help_text="0-1: confidence in this insight")
    relevance_score = models.FloatField(default=0.5, help_text="0-1: relevance to user")
    
    # Actionability
    is_actionable = models.BooleanField(default=False)
    suggested_action = models.TextField(blank=True)
    
    # Lifecycle
    generated_at = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField(null=True, blank=True, help_text="Period this insight covers")
    period_end = models.DateField(null=True, blank=True)
    
    # Tracking
    was_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    user_feedback = models.CharField(
        max_length=20,
        choices=[('helpful', 'Helpful'), ('not_helpful', 'Not Helpful'), ('interesting', 'Interesting')],
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class InsightExport(models.Model):
    """Tracks exports of insights for therapist/personal records."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insight_exports')
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF Report'),
        ('json', 'JSON Data'),
        ('csv', 'CSV Table'),
        ('email', 'Email Report'),
    ]
    
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    
    # Content
    title = models.CharField(max_length=200)
    insights_included = models.ManyToManyField(Insight, blank=True)
    
    # Meta
    period_start = models.DateField()
    period_end = models.DateField()
    
    # File/content
    file_url = models.URLField(blank=True, help_text="URL to download exported file")
    content = models.TextField(blank=True, help_text="Exported content for email format")
    
    # Sharing
    shared_with = models.CharField(max_length=200, blank=True, help_text="Email or name of recipient")
    is_shareable = models.BooleanField(default=False, help_text="Can be shared externally")
    share_token = models.CharField(max_length=100, blank=True, unique=True)
    
    # Lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When share link expires")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_export_format_display()} ({self.period_start})"


class ConfidenceScore(models.Model):
    """Explainability for confidence scores on recommendations."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='confidence_scores')
    
    # What this confidence is about
    SCORE_SUBJECTS = [
        ('intervention_recommendation', 'Intervention Recommendation'),
        ('mood_prediction', 'Mood Prediction'),
        ('pattern_detection', 'Pattern Detection'),
        ('effectiveness_estimate', 'Effectiveness Estimate'),
        ('overall_assessment', 'Overall Assessment'),
    ]
    
    subject = models.CharField(max_length=50, choices=SCORE_SUBJECTS)
    subject_id = models.IntegerField(null=True, blank=True, help_text="ID of subject (intervention, pattern, etc)")
    
    # The score
    confidence = models.FloatField(help_text="0-1: confidence level")
    
    # Why we're confident (or not)
    factors = models.JSONField(
        default=dict,
        help_text='{
            "data_recency": 0.9,
            "sample_size": 0.7,
            "historical_consistency": 0.8,
            "personalization": 0.6
        }'
    )
    
    # Explanation
    explanation = models.TextField(help_text="Why this confidence level, in plain English")
    uncertainty_reasons = models.JSONField(
        default=list,
        help_text='["Limited historical data", "Weather could be affecting mood"]'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_subject_display()} ({self.confidence*100:.0f}%)"
    
    def explain_confidence(self) -> str:
        """Generate human-readable explanation of confidence score."""
        if self.confidence > 0.8:
            level = "Very Confident"
        elif self.confidence > 0.6:
            level = "Fairly Confident"
        elif self.confidence > 0.4:
            level = "Moderately Confident"
        else:
            level = "Low Confidence"
        
        return f"{level} ({self.confidence*100:.0f}%)\n\n{self.explanation}"
