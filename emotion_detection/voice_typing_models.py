from django.db import models
from django.contrib.auth.models import User
import json

class VoiceEmotionRecord(models.Model):
    session = models.ForeignKey('EmotionDetectionSession', on_delete=models.CASCADE, related_name='voice_records')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Voice emotion data
    emotion = models.CharField(max_length=20)
    confidence = models.FloatField(default=0.0)
    
    # Voice characteristics
    pitch_mean = models.FloatField(default=0.0)
    pitch_std = models.FloatField(default=0.0)
    energy = models.FloatField(default=0.0)
    tempo = models.FloatField(default=0.0)
    
    # Spectral features
    spectral_features = models.JSONField(default=dict)
    
    def __str__(self):
        return f"{self.session.user.username} - Voice {self.emotion} ({self.confidence:.2f})"

class TypingPattern(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_start = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - Typing Session"

class TypingEvent(models.Model):
    pattern = models.ForeignKey(TypingPattern, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Typing characteristics
    key_code = models.IntegerField()
    key_pressed = models.CharField(max_length=50)
    press_duration = models.FloatField(default=0.0)  # milliseconds
    time_since_previous = models.FloatField(default=0.0)  # milliseconds
    
    # Typing rhythm metrics
    typing_speed = models.FloatField(default=0.0)  # keys per minute
    rhythm_variance = models.FloatField(default=0.0)
    
    # Inferred emotional state
    inferred_emotion = models.CharField(max_length=20, blank=True)
    confidence = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.pattern.user.username} - {self.key_pressed} at {self.timestamp}"

class TypingEmotionProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=20)
    
    # Typing characteristics for this emotion
    avg_typing_speed = models.FloatField(default=0.0)
    avg_press_duration = models.FloatField(default=0.0)
    avg_rhythm_variance = models.FloatField(default=0.0)
    
    # Error patterns
    backspace_frequency = models.FloatField(default=0.0)
    correction_frequency = models.FloatField(default=0.0)
    
    # Sample size for reliability
    sample_size = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'emotion']
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion} Typing Profile"
