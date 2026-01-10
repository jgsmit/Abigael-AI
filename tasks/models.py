from django.db import models
from django.contrib.auth.models import User

class EmotionTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color code
    
    def __str__(self):
        return self.name

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    required_emotions = models.ManyToManyField(EmotionTag, related_name='tasks_requiring')
    preferred_emotions = models.ManyToManyField(EmotionTag, related_name='tasks_preferred', blank=True)
    
    def __str__(self):
        return self.title

class EmotionRecord(models.Model):
    EMOTION_CHOICES = [
        ('happy', 'Happy'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
        ('fearful', 'Fearful'),
        ('disgusted', 'Disgusted'),
        ('surprised', 'Surprised'),
        ('neutral', 'Neutral'),
        ('focused', 'Focused'),
        ('stressed', 'Stressed'),
        ('calm', 'Calm'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    confidence = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion} at {self.timestamp}"

class TaskEmotionPattern(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=20)
    task_type = models.CharField(max_length=100)  # e.g., 'writing', 'coding', 'cleaning'
    completion_rate = models.FloatField(default=0.0)
    average_time = models.FloatField(default=0.0)  # in minutes
    sample_size = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'emotion', 'task_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion} - {self.task_type}"
