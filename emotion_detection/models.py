from django.db import models
from django.contrib.auth.models import User
import json

class EmotionDetectionSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.start_time}"

class EmotionSnapshot(models.Model):
    session = models.ForeignKey(EmotionDetectionSession, on_delete=models.CASCADE, related_name='snapshots')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Raw emotion data from FER model
    emotions = models.JSONField(default=dict)  # {'happy': 0.8, 'sad': 0.1, ...}
    dominant_emotion = models.CharField(max_length=20)
    confidence = models.FloatField(default=0.0)
    
    # Additional metrics
    face_detected = models.BooleanField(default=True)
    face_coordinates = models.JSONField(default=dict)  # {'x': 100, 'y': 150, 'w': 200, 'h': 200}
    
    def __str__(self):
        return f"{self.session.user.username} - {self.dominant_emotion} ({self.confidence:.2f})"

class EmotionAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Daily emotion statistics
    dominant_emotions = models.JSONField(default=dict)  # emotion -> count
    average_confidence = models.FloatField(default=0.0)
    total_detections = models.IntegerField(default=0)
    
    # Productivity correlation
    tasks_completed = models.IntegerField(default=0)
    productivity_score = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"

class EmotionTrend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=20)
    trend_data = models.JSONField(default=list)  # List of {timestamp, value} pairs
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'emotion']
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion} trend"
