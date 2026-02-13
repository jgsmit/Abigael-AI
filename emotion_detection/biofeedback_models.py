from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class BiofeedbackDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='biofeedback_devices')
    device_name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50, choices=[
        ('fitbit', 'Fitbit'),
        ('apple_watch', 'Apple Watch'),
        ('garmin', 'Garmin'),
        ('oura_ring', 'Oura Ring'),
        ('whoop', 'WHOOP'),
        ('polar', 'Polar'),
        ('manual', 'Manual Entry'),
    ])  # 'fitbit', 'apple_watch', 'garmin', etc.
    device_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_frequency_minutes = models.IntegerField(default=60)
    access_token = models.TextField(blank=True)  # OAuth token (should be encrypted)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)  # Track last successful sync
    
    def __str__(self):
        return f"{self.user.username} - {self.device_name}"

class HeartRateRecord(models.Model):
    device = models.ForeignKey(BiofeedbackDevice, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    heart_rate = models.IntegerField()  # BPM
    resting_heart_rate = models.IntegerField(null=True, blank=True)
    heart_rate_variability = models.FloatField(null=True, blank=True)  # HRV in ms
    
    # Contextual data
    activity_type = models.CharField(max_length=50, blank=True)  # 'resting', 'active', 'sleep'
    stress_level = models.IntegerField(null=True, blank=True)  # 1-100 scale if available
    
    def __str__(self):
        return f"{self.device.user.username} - {self.heart_rate} BPM at {self.timestamp}"

class SleepRecord(models.Model):
    device = models.ForeignKey(BiofeedbackDevice, on_delete=models.CASCADE)
    sleep_date = models.DateField()
    bedtime = models.DateTimeField()
    wake_time = models.DateTimeField()
    
    # Sleep quality metrics
    total_sleep_hours = models.FloatField()
    deep_sleep_hours = models.FloatField(default=0.0)
    rem_sleep_hours = models.FloatField(default=0.0)
    light_sleep_hours = models.FloatField(default=0.0)
    
    # Sleep quality score
    sleep_score = models.IntegerField(null=True, blank=True)  # 1-100 scale
    
    # Restfulness indicators
    restful_hours = models.FloatField(default=0.0)
    restless_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.device.user.username} - Sleep {self.sleep_date}"

class ActivityRecord(models.Model):
    device = models.ForeignKey(BiofeedbackDevice, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    activity_type = models.CharField(max_length=50)  # 'walking', 'running', 'cycling', etc.
    duration_minutes = models.IntegerField()
    calories_burned = models.FloatField(default=0.0)
    
    # Intensity metrics
    steps_count = models.IntegerField(default=0)
    distance_km = models.FloatField(default=0.0)
    active_zone_minutes = models.IntegerField(default=0)
    
    # Heart rate zones
    resting_zone_minutes = models.IntegerField(default=0)
    fat_burn_zone_minutes = models.IntegerField(default=0)
    cardio_zone_minutes = models.IntegerField(default=0)
    peak_zone_minutes = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.device.user.username} - {self.activity_type} at {self.timestamp}"

class StressRecord(models.Model):
    device = models.ForeignKey(BiofeedbackDevice, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    stress_level = models.IntegerField()  # 1-100 scale
    stress_type = models.CharField(max_length=50, blank=True)  # 'physical', 'mental', 'emotional'
    
    # Physiological indicators
    heart_rate = models.IntegerField(null=True, blank=True)
    hrv = models.FloatField(null=True, blank=True)  # Heart rate variability
    skin_conductance = models.FloatField(null=True, blank=True)  # If available
    
    # Context
    during_task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.device.user.username} - Stress {self.stress_level} at {self.timestamp}"

class BiofeedbackSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Aggregated metrics for the session
    avg_heart_rate = models.FloatField(null=True, blank=True)
    max_heart_rate = models.IntegerField(null=True, blank=True)
    min_heart_rate = models.IntegerField(null=True, blank=True)
    avg_stress_level = models.FloatField(null=True, blank=True)
    
    # Session summary
    total_steps = models.IntegerField(default=0)
    total_calories = models.FloatField(default=0.0)
    active_minutes = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - Biofeedback Session"

class BiofeedbackEmotionCorrelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=20)
    
    # Biofeedback patterns for this emotion
    avg_heart_rate = models.FloatField(default=0.0)
    avg_hrv = models.FloatField(default=0.0)
    avg_stress_level = models.FloatField(default=0.0)
    
    # Typical activity patterns
    typical_activity_level = models.CharField(max_length=50, blank=True)
    typical_sleep_quality = models.FloatField(default=0.0)
    
    # Correlation strength
    correlation_strength = models.FloatField(default=0.0)  # 0-1 scale
    sample_size = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'emotion']
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion} Biofeedback Pattern"

class DailyBiofeedbackSummary(models.Model):
    """Daily aggregated summary of biofeedback data."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_biofeedback')
    date = models.DateField()
    
    # Heart rate stats
    avg_heart_rate = models.FloatField(null=True, blank=True)
    min_heart_rate = models.FloatField(null=True, blank=True)
    max_heart_rate = models.FloatField(null=True, blank=True)
    resting_heart_rate = models.FloatField(null=True, blank=True)
    heart_rate_variability = models.FloatField(null=True, blank=True)
    
    # Sleep data
    sleep_duration_hours = models.FloatField(null=True, blank=True)
    sleep_quality = models.FloatField(null=True, blank=True, help_text="0-100 scale")
    time_in_deep_sleep = models.FloatField(null=True, blank=True, help_text="minutes")
    time_in_rem_sleep = models.FloatField(null=True, blank=True, help_text="minutes")
    
    # Activity
    steps = models.IntegerField(null=True, blank=True)
    calories_burned = models.FloatField(null=True, blank=True)
    active_minutes = models.IntegerField(null=True, blank=True)
    
    # Subjective scores
    stress_level = models.FloatField(null=True, blank=True, help_text="0-100")
    energy_level = models.FloatField(null=True, blank=True, help_text="0-100")
    recovery_score = models.FloatField(null=True, blank=True, help_text="0-100")
    
    # Correlations
    hrv_trend = models.CharField(
        max_length=10,
        choices=[('improving', 'Improving'), ('declining', 'Declining'), ('stable', 'Stable')],
        default='stable'
    )
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class BiofeedbackAlert(models.Model):
    """Alert triggered by biofeedback anomalies or thresholds."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='biofeedback_alerts')
    
    ALERT_TYPES = [
        ('high_stress', 'High Stress Detected'),
        ('low_sleep', 'Insufficient Sleep'),
        ('high_hr', 'Elevated Heart Rate'),
        ('irregular_pattern', 'Irregular Pattern'),
        ('recovery_needed', 'Recovery Suggested'),
        ('anomaly', 'Data Anomaly'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_alert_type_display()}"


class BiofeedbackIntegrationConfig(models.Model):
    """User configuration for biofeedback integrations."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='biofeedback_config')
    
    # Thresholds for alerts
    high_stress_threshold = models.FloatField(default=75.0, help_text="0-100")
    high_heart_rate_threshold = models.IntegerField(default=100, help_text="BPM")
    low_sleep_threshold = models.FloatField(default=6.0, help_text="hours")
    
    # Preferences
    enable_alerts = models.BooleanField(default=True)
    enable_sleep_tracking = models.BooleanField(default=True)
    enable_stress_tracking = models.BooleanField(default=True)
    auto_trigger_interventions = models.BooleanField(default=True)
    
    # Privacy
    share_with_therapist = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Biofeedback Config"