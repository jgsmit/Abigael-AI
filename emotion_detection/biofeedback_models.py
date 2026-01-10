from django.db import models
from django.contrib.auth.models import User
import json

class BiofeedbackDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    device_name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50)  # 'fitbit', 'apple_watch', 'garmin', etc.
    device_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    access_token = models.TextField(blank=True)  # OAuth token
    refresh_token = models.TextField(blank=True)
    
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
