from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Task, EmotionTag, EmotionRecord, TaskEmotionPattern
from emotion_detection.emotion_detector import emotion_detector, get_emotion_recommendations
import json

@login_required
def dashboard(request):
    """Main dashboard showing tasks and emotion-based recommendations"""
    user_tasks = Task.objects.filter(user=request.user).exclude(status='completed')
    
    # Get current emotion
    current_emotion_data = emotion_detector.get_current_emotion()
    current_emotion = current_emotion_data['emotion'] if current_emotion_data else None
    
    # Get recommendations
    recommendations = get_emotion_recommendations(current_emotion, user_tasks)
    
    # Get recent emotion records
    recent_emotions = EmotionRecord.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    # Get task statistics
    total_tasks = Task.objects.filter(user=request.user).count()
    completed_tasks = Task.objects.filter(user=request.user, status='completed').count()
    pending_tasks = Task.objects.filter(user=request.user, status='pending').count()
    
    context = {
        'tasks': user_tasks,
        'recommendations': recommendations,
        'current_emotion': current_emotion,
        'current_emotion_data': current_emotion_data,
        'recent_emotions': recent_emotions,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'emotion_tags': EmotionTag.objects.all(),
    }
    
    return render(request, 'tasks/dashboard.html', context)

@login_required
def task_list(request):
    """List all tasks with filtering options"""
    tasks = Task.objects.filter(user=request.user)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    # Filter by priority
    priority_filter = request.GET.get('priority')
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    # Filter by emotion tag
    emotion_filter = request.GET.get('emotion')
    if emotion_filter:
        tasks = tasks.filter(required_emotions__name=emotion_filter)
    
    context = {
        'tasks': tasks.order_by('-created_at'),
        'emotion_tags': EmotionTag.objects.all(),
    }
    
    return render(request, 'tasks/task_list.html', context)

@login_required
def create_task(request):
    """Create a new task"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        due_date_str = request.POST.get('due_date')
        required_emotions = request.POST.getlist('required_emotions')
        preferred_emotions = request.POST.getlist('preferred_emotions')
        
        task = Task.objects.create(
            title=title,
            description=description,
            priority=priority,
            user=request.user
        )
        
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
                task.save()
            except ValueError:
                pass
        
        # Add emotion tags
        if required_emotions:
            task.required_emotions.set(EmotionTag.objects.filter(id__in=required_emotions))
        if preferred_emotions:
            task.preferred_emotions.set(EmotionTag.objects.filter(id__in=preferred_emotions))
        
        return redirect('task_list')
    
    context = {
        'emotion_tags': EmotionTag.objects.all(),
    }
    
    return render(request, 'tasks/create_task.html', context)

@login_required
def update_task(request, task_id):
    """Update task status and details"""
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    if request.method == 'POST':
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority', task.priority)
        task.status = request.POST.get('status', task.status)
        
        due_date_str = request.POST.get('due_date')
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # Handle completion
        if task.status == 'completed' and not task.completed_at:
            task.completed_at = timezone.now()
            
            # Record emotion pattern
            current_emotion_data = emotion_detector.get_current_emotion()
            if current_emotion_data:
                emotion = current_emotion_data['emotion']
                task_type = _classify_task_type(task.title)
                
                pattern, created = TaskEmotionPattern.objects.get_or_create(
                    user=request.user,
                    emotion=emotion,
                    task_type=task_type
                )
                
                # Update pattern statistics
                if not created:
                    pattern.sample_size += 1
                    pattern.completion_rate = ((pattern.completion_rate * (pattern.sample_size - 1)) + 1) / pattern.sample_size
                    pattern.save()
        
        task.save()
        
        # Update emotion tags
        required_emotions = request.POST.getlist('required_emotions')
        preferred_emotions = request.POST.getlist('preferred_emotions')
        
        if required_emotions:
            task.required_emotions.set(EmotionTag.objects.filter(id__in=required_emotions))
        if preferred_emotions:
            task.preferred_emotions.set(EmotionTag.objects.filter(id__in=preferred_emotions))
        
        return redirect('task_list')
    
    context = {
        'task': task,
        'emotion_tags': EmotionTag.objects.all(),
    }
    
    return render(request, 'tasks/update_task.html', context)

@login_required
def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    return redirect('task_list')

@login_required
def start_emotion_detection(request):
    """Start emotion detection via AJAX"""
    if request.method == 'POST':
        emotion_detector.start_detection(request.user)
        return JsonResponse({'status': 'success', 'message': 'Emotion detection started'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def stop_emotion_detection(request):
    """Stop emotion detection via AJAX"""
    if request.method == 'POST':
        emotion_detector.stop_detection()
        return JsonResponse({'status': 'success', 'message': 'Emotion detection stopped'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_current_emotion(request):
    """Get current emotion via AJAX"""
    emotion_data = emotion_detector.get_current_emotion()
    if emotion_data:
        return JsonResponse({'status': 'success', 'emotion': emotion_data})
    return JsonResponse({'status': 'error', 'message': 'No emotion data available'})

@login_required
def emotion_analytics(request):
    """Show emotion analytics and patterns"""
    # Get emotion records for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    emotion_records = EmotionRecord.objects.filter(
        user=request.user,
        timestamp__gte=thirty_days_ago
    ).order_by('-timestamp')
    
    # Calculate emotion statistics
    emotion_counts = {}
    for record in emotion_records:
        emotion_counts[record.emotion] = emotion_counts.get(record.emotion, 0) + 1
    
    # Get task emotion patterns
    patterns = TaskEmotionPattern.objects.filter(user=request.user)
    
    context = {
        'emotion_records': emotion_records[:50],  # Last 50 records
        'emotion_counts': emotion_counts,
        'patterns': patterns,
    }
    
    return render(request, 'tasks/emotion_analytics.html', context)

def _classify_task_type(title):
    """Simple task classification based on keywords"""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['write', 'report', 'document', 'email']):
        return 'writing'
    elif any(word in title_lower for word in ['code', 'program', 'develop', 'debug']):
        return 'coding'
    elif any(word in title_lower for word in ['clean', 'organize', 'arrange']):
        return 'cleaning'
    elif any(word in title_lower for word in ['meeting', 'call', 'presentation']):
        return 'communication'
    elif any(word in title_lower for word in ['learn', 'study', 'read', 'research']):
        return 'learning'
    else:
        return 'general'
