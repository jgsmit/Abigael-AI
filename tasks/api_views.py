"""
Task and productivity API endpoints
Provides comprehensive task data for frontend consumption
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, Avg
import json

from .models import Task, EmotionTag, TaskEmotionPattern, EmotionRecord


@login_required
def get_all_tasks(request):
    """
    Get all user tasks with filtering and sorting
    Query params: status, priority, emotion_tag, sort_by
    """
    try:
        user = request.user
        
        # Get filter parameters
        status_filter = request.GET.get('status')
        priority_filter = request.GET.get('priority')
        emotion_filter = request.GET.get('emotion')
        sort_by = request.GET.get('sort_by', '-created_at')
        
        # Base query
        tasks = Task.objects.filter(user=user)
        
        # Apply filters
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        if priority_filter:
            tasks = tasks.filter(priority=priority_filter)
        if emotion_filter:
            tasks = tasks.filter(emotion_tag=emotion_filter)
        
        # Sort
        valid_sort = ['-created_at', 'created_at', 'due_date', '-updated_at', 'priority']
        if sort_by not in valid_sort:
            sort_by = '-created_at'
        tasks = tasks.order_by(sort_by)
        
        # Format response
        tasks_list = [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'status': t.status,
                'priority': t.priority,
                'emotion_tag': t.emotion_tag,
                'created_at': t.created_at.isoformat(),
                'updated_at': t.updated_at.isoformat(),
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'duration_hours': t.duration_hours,
            }
            for t in tasks[:100]  # Limit to 100 per request
        ]
        
        return JsonResponse({
            'status': 'success',
            'total_count': tasks.count(),
            'tasks': tasks_list
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_task_details(request, task_id):
    """Get detailed information about a specific task"""
    try:
        user = request.user
        task = Task.objects.get(id=task_id, user=user)
        
        # Get emotion pattern for this task
        emotion_pattern = TaskEmotionPattern.objects.filter(
            user=user, task=task
        ).first()
        
        return JsonResponse({
            'status': 'success',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'emotion_tag': task.emotion_tag,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'duration_hours': task.duration_hours,
                'estimated_duration': task.estimated_duration if hasattr(task, 'estimated_duration') else None,
                'emotion_pattern': {
                    'emotion_before': emotion_pattern.emotion_before if emotion_pattern else None,
                    'emotion_after': emotion_pattern.emotion_after if emotion_pattern else None,
                    'emotional_impact': emotion_pattern.emotional_impact if emotion_pattern else None,
                } if emotion_pattern else None,
            }
        })
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_task_analytics(request):
    """
    Get comprehensive task analytics and insights
    Returns: completion rates, patterns, trends, recommendations
    """
    try:
        user = request.user
        
        # Time-based splits
        cutoff_7d = timezone.now() - timedelta(days=7)
        cutoff_30d = timezone.now() - timedelta(days=30)
        cutoff_90d = timezone.now() - timedelta(days=90)
        
        # Completion statistics
        total_tasks = Task.objects.filter(user=user).count()
        completed_tasks = Task.objects.filter(user=user, completed_at__isnull=False).count()
        pending_tasks = Task.objects.filter(user=user, completed_at__isnull=True).count()
        
        completed_7d = Task.objects.filter(
            user=user, completed_at__gte=cutoff_7d
        ).count()
        completed_30d = Task.objects.filter(
            user=user, completed_at__gte=cutoff_30d
        ).count()
        completed_90d = Task.objects.filter(
            user=user, completed_at__gte=cutoff_90d
        ).count()
        
        # Priority distribution
        priority_distribution = Task.objects.filter(user=user).values('priority').annotate(count=Count('id'))
        
        # Status distribution
        status_distribution = Task.objects.filter(user=user).values('status').annotate(count=Count('id'))
        
        # Emotion-task relationships
        emotion_patterns = TaskEmotionPattern.objects.filter(user=user).values(
            'emotion_before', 'emotion_after'
        ).annotate(count=Count('id'))
        
        # Average duration by priority
        duration_by_priority = Task.objects.filter(user=user).values('priority').annotate(
            avg_duration=Avg('duration_hours'),
            count=Count('id')
        )
        
        # Task completion by day of week
        tasks_by_weekday = {}
        for i in range(7):
            day = (timezone.now() - timedelta(days=i)).date()
            completed = Task.objects.filter(
                user=user,
                completed_at__date=day
            ).count()
            tasks_by_weekday[day.isoformat()] = completed
        
        return JsonResponse({
            'status': 'success',
            'overview': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'overall_completion_rate': round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0,
            },
            'time_based': {
                'last_7_days': {
                    'completed': completed_7d,
                    'completion_rate': round(completed_7d / max(1, Task.objects.filter(user=user, created_at__gte=cutoff_7d).count()) * 100, 2),
                },
                'last_30_days': {
                    'completed': completed_30d,
                    'completion_rate': round(completed_30d / max(1, Task.objects.filter(user=user, created_at__gte=cutoff_30d).count()) * 100, 2),
                },
                'last_90_days': {
                    'completed': completed_90d,
                    'completion_rate': round(completed_90d / max(1, Task.objects.filter(user=user, created_at__gte=cutoff_90d).count()) * 100, 2),
                },
            },
            'distribution': {
                'by_priority': [
                    {'priority': item['priority'], 'count': item['count']}
                    for item in priority_distribution
                ],
                'by_status': [
                    {'status': item['status'], 'count': item['count']}
                    for item in status_distribution
                ],
            },
            'patterns': {
                'emotion_transitions': list(emotion_patterns),
                'completion_by_weekday': tasks_by_weekday,
                'avg_duration_by_priority': [
                    {
                        'priority': item['priority'],
                        'avg_duration': round(item['avg_duration'], 1),
                        'count': item['count']
                    }
                    for item in duration_by_priority
                ],
            },
            'insights': _generate_task_insights(user),
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_task_recommendations(request):
    """
    Get AI-powered task recommendations based on user patterns
    Returns: suggested next tasks, optimal timing, emotional context
    """
    try:
        user = request.user
        
        # Get pending tasks
        pending_tasks = Task.objects.filter(
            user=user, completed_at__isnull=True
        ).order_by('priority', 'due_date')[:10]
        
        # Analyze emotion patterns
        recent_emotions = EmotionRecord.objects.filter(
            user=user
        ).order_by('-timestamp')[:10]
        
        current_emotion = recent_emotions.first().emotion if recent_emotions else 'neutral'
        
        recommendations = []
        for task in pending_tasks:
            # Check if there's an emotional pattern for this task
            pattern = TaskEmotionPattern.objects.filter(
                user=user, task=task
            ).first()
            
            match_score = 0
            context = ""
            
            if pattern:
                # If user typically feels good after this task, recommend it
                if pattern.emotion_after == 'happy' or pattern.emotion_after == 'proud':
                    match_score += 0.8
                    context = "This task makes you feel good!"
                # If user feels motivated, recommend high-priority tasks
                elif current_emotion == 'focused' and task.priority == 'high':
                    match_score += 0.9
                    context = "Perfect timing for this task - you're focused!"
                # If user is stressed, recommend easy wins
                elif current_emotion == 'stressed' and task.priority == 'low':
                    match_score += 0.7
                    context = "Quick win to reduce stress"
            else:
                # Default scoring
                match_score = 0.5
            
            recommendations.append({
                'task_id': task.id,
                'title': task.title,
                'priority': task.priority,
                'match_score': round(match_score, 2),
                'recommended_now': match_score > 0.7,
                'context': context,
                'emotional_readiness': current_emotion,
            })
        
        # Sort by match score
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        
        return JsonResponse({
            'status': 'success',
            'current_emotion': current_emotion,
            'recommendations': recommendations[:5],  # Top 5 recommendations
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def _generate_task_insights(user):
    """Generate insights about task completion patterns"""
    insights = []
    
    total_tasks = Task.objects.filter(user=user).count()
    completed_tasks = Task.objects.filter(user=user, completed_at__isnull=False).count()
    
    if total_tasks == 0:
        return insights
    
    completion_rate = completed_tasks / total_tasks
    
    if completion_rate > 0.8:
        insights.append("Excellent completion rate! You're very productive.")
    elif completion_rate > 0.6:
        insights.append("Good progress. Keep maintaining this pace.")
    elif completion_rate > 0.4:
        insights.append("You're making progress. Consider breaking tasks into smaller steps.")
    else:
        insights.append("Consider focusing on fewer tasks to improve completion rate.")
    
    # Check for procrastination patterns
    pending_high_priority = Task.objects.filter(
        user=user,
        priority='high',
        completed_at__isnull=True
    ).count()
    
    if pending_high_priority > 3:
        insights.append(f"You have {pending_high_priority} high-priority tasks pending. Consider starting one today.")
    
    # Check overdue tasks
    overdue = Task.objects.filter(
        user=user,
        due_date__lt=timezone.now(),
        completed_at__isnull=True
    ).count()
    
    if overdue > 0:
        insights.append(f"You have {overdue} overdue task(s). These might need immediate attention.")
    
    return insights
