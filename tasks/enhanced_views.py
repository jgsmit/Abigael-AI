from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Task, EmotionTag, EmotionRecord, TaskEmotionPattern
from emotion_detection.emotion_detector import emotion_detector, get_emotion_recommendations
from emotion_detection.voice_detector import voice_detector
from emotion_detection.typing_detector import typing_detector
from emotion_detection.empathy_engine import empathy_engine
from emotion_detection.analytics_visualizer import analytics_visualizer
from emotion_detection.biofeedback_integrator import biofeedback_integrator
from emotion_detection.biofeedback_models import BiofeedbackDevice
import json

@login_required
def dashboard(request):
    """Enhanced dashboard with multi-modal emotion detection"""
    user_tasks = Task.objects.filter(user=request.user).exclude(status='completed')
    
    # Get comprehensive emotion state from all sensors
    emotion_state = empathy_engine.get_comprehensive_emotion_state(request.user)
    current_emotion = emotion_state.get('combined', 'neutral')
    current_emotion_data = emotion_state
    
    # Get recommendations
    recommendations = get_emotion_recommendations(current_emotion, user_tasks)
    
    # Get recent emotion records from all sources
    recent_emotions = EmotionRecord.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    # Get task statistics
    total_tasks = Task.objects.filter(user=request.user).count()
    completed_tasks = Task.objects.filter(user=request.user, status='completed').count()
    pending_tasks = Task.objects.filter(user=request.user, status='pending').count()
    
    # Get biofeedback data if available
    stress_level = biofeedback_integrator.get_current_stress_level(request.user)
    energy_level = biofeedback_integrator.get_energy_level(request.user)
    
    # Generate empathetic message
    empathetic_message = empathy_engine.generate_empathetic_message(
        current_emotion, 
        current_task=recommendations[0] if recommendations else None
    )
    
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
        'empathetic_message': empathetic_message,
        'stress_level': stress_level,
        'energy_level': energy_level,
        'biofeedback_available': BiofeedbackDevice.objects.filter(user=request.user, is_active=True).exists(),
    }
    
    return render(request, 'tasks/dashboard.html', context)

@login_required
def start_multimodal_detection(request):
    """Start all emotion detection methods"""
    if request.method == 'POST':
        try:
            # Start facial emotion detection
            emotion_detector.start_detection(request.user)
            
            # Start voice detection
            voice_detector.start_voice_detection(request.user)
            
            # Start typing pattern monitoring
            typing_detector.start_monitoring(request.user)
            
            # Start biofeedback sync if devices available
            devices = BiofeedbackDevice.objects.filter(user=request.user, is_active=True)
            if devices.exists():
                biofeedback_integrator.start_sync(request.user)
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Multi-modal emotion detection started'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Error starting detection: {str(e)}'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def stop_multimodal_detection(request):
    """Stop all emotion detection methods"""
    if request.method == 'POST':
        try:
            emotion_detector.stop_detection()
            voice_detector.stop_voice_detection()
            typing_detector.stop_monitoring()
            biofeedback_integrator.stop_sync()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Multi-modal emotion detection stopped'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Error stopping detection: {str(e)}'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_comprehensive_emotion(request):
    """Get comprehensive emotion state from all sensors"""
    emotion_state = empathy_engine.get_comprehensive_emotion_state(request.user)
    
    if emotion_state['combined']:
        return JsonResponse({'status': 'success', 'emotion': emotion_state})
    return JsonResponse({'status': 'error', 'message': 'No emotion data available'})

@login_required
def get_empathetic_message(request):
    """Get AI-powered empathetic message"""
    if request.method == 'POST':
        try:
            emotion = request.POST.get('emotion', 'neutral')
            task_id = request.POST.get('task_id')
            context = request.POST.get('context', '')
            
            current_task = None
            if task_id:
                current_task = get_object_or_404(Task, id=task_id, user=request.user)
            
            message = empathy_engine.generate_empathetic_message(
                emotion, current_task=current_task, context=context
            )
            
            return JsonResponse({'status': 'success', 'message': message})
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Error generating message: {str(e)}'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def suggest_break(request):
    """Get break suggestion based on current state"""
    if request.method == 'POST':
        emotion = request.POST.get('emotion', 'neutral')
        suggestion = empathy_engine.suggest_break(emotion)
        return JsonResponse({'status': 'success', 'suggestion': suggestion})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def emotion_analytics(request):
    """Enhanced emotion analytics with advanced visualizations"""
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
    
    # Generate advanced visualizations
    timeline_chart = analytics_visualizer.generate_emotion_timeline_chart(request.user, days=7)
    distribution_pie = analytics_visualizer.generate_emotion_distribution_pie(request.user, days=30)
    productivity_heatmap = analytics_visualizer.generate_productivity_heatmap(request.user, days=30)
    energy_curve = analytics_visualizer.generate_energy_curve_chart(request.user, days=7)
    multimodal_comparison = analytics_visualizer.generate_multimodal_comparison(request.user, days=7)
    
    # Get productivity insights
    insights = empathy_engine.analyze_productivity_pattern(request.user, time_period_hours=24)
    
    context = {
        'emotion_records': emotion_records[:50],  # Last 50 records
        'emotion_counts': emotion_counts,
        'patterns': patterns,
        'timeline_chart': timeline_chart,
        'distribution_pie': distribution_pie,
        'productivity_heatmap': productivity_heatmap,
        'energy_curve': energy_curve,
        'multimodal_comparison': multimodal_comparison,
        'insights': insights,
    }
    
    return render(request, 'tasks/emotion_analytics.html', context)

@login_required
def biofeedback_settings(request):
    """Manage biofeedback device settings"""
    if request.method == 'POST':
        device_type = request.POST.get('device_type')
        device_name = request.POST.get('device_name')
        access_token = request.POST.get('access_token', '')
        
        if device_type and device_name:
            device = biofeedback_integrator.register_device(
                request.user, device_type, device_name, access_token
            )
            
            if device:
                return JsonResponse({
                    'status': 'success', 
                    'message': f'{device_name} registered successfully'
                })
        
        return JsonResponse({'status': 'error', 'message': 'Invalid device information'})
    
    # Get existing devices
    devices = BiofeedbackDevice.objects.filter(user=request.user)
    
    context = {
        'devices': devices,
    }
    
    return render(request, 'tasks/biofeedback_settings.html', context)

@login_required
def motivation_chat(request):
    """AI-powered motivation and coaching interface"""
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        current_emotion = request.POST.get('current_emotion', 'neutral')
        
        # Generate empathetic response
        response = empathy_engine.generate_empathetic_message(
            current_emotion, context=user_message
        )
        
        return JsonResponse({'status': 'success', 'response': response})
    
    # Get current emotion state for initial message
    emotion_state = empathy_engine.get_comprehensive_emotion_state(request.user)
    current_emotion = emotion_state.get('combined', 'neutral')
    
    # Generate initial empathetic message
    initial_message = empathy_engine.generate_empathetic_message(current_emotion)
    
    context = {
        'current_emotion': current_emotion,
        'initial_message': initial_message,
    }
    
    return render(request, 'tasks/motivation_chat.html', context)

# Keep existing views...
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
        
        # Handle completion with enhanced emotion tracking
        if task.status == 'completed' and not task.completed_at:
            task.completed_at = timezone.now()
            
            # Get comprehensive emotion state
            emotion_state = empathy_engine.get_comprehensive_emotion_state(request.user)
            current_emotion = emotion_state.get('combined', 'neutral')
            
            # Record emotion pattern
            task_type = _classify_task_type(task.title)
            
            pattern, created = TaskEmotionPattern.objects.get_or_create(
                user=request.user,
                emotion=current_emotion,
                task_type=task_type
            )
            
            # Update pattern statistics
            if not created:
                pattern.sample_size += 1
                pattern.completion_rate = ((pattern.completion_rate * (pattern.sample_size - 1)) + 1) / pattern.sample_size
                pattern.save()
            
            # Generate completion message
            completion_message = empathy_engine.generate_motivation_message(task_completed=True)
            
            # Store completion message in session for display
            request.session['completion_message'] = completion_message
        
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
