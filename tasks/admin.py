from django.contrib import admin
from .models import EmotionTag, Task, EmotionRecord, TaskEmotionPattern

@admin.register(EmotionTag)
class EmotionTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color']
    search_fields = ['name']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'priority', 'status', 'created_at', 'due_date']
    list_filter = ['priority', 'status', 'created_at', 'due_date']
    search_fields = ['title', 'description']
    filter_horizontal = ['required_emotions', 'preferred_emotions']
    date_hierarchy = 'created_at'

@admin.register(EmotionRecord)
class EmotionRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'emotion', 'confidence', 'timestamp', 'task']
    list_filter = ['emotion', 'timestamp']
    search_fields = ['user__username', 'emotion']
    date_hierarchy = 'timestamp'

@admin.register(TaskEmotionPattern)
class TaskEmotionPatternAdmin(admin.ModelAdmin):
    list_display = ['user', 'emotion', 'task_type', 'completion_rate', 'sample_size']
    list_filter = ['emotion', 'task_type']
    search_fields = ['user__username', 'emotion', 'task_type']
