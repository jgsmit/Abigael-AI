"""
Comprehensive API endpoints for user data and metrics
Provides unified data structure for frontend consumption
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count, Q, Sum
import json

from .companion_models import (
    CompanionProfile, Conversation, Message, JournalEntry,
    LifeCoachingSession, StreakTracker, Achievement, UserAchievement,
    DailyCompanionInteraction, CrisisDetection
)
from .models import EmotionEvent, BurnoutRiskAssessment
from tasks.models import Task


@login_required
def user_profile_data(request):
    """
    Complete user profile and metadata
    Returns: user info, preferences, settings
    """
    try:
        user = request.user
        profile, _ = CompanionProfile.objects.get_or_create(user=user)
        
        return JsonResponse({
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
            },
            'profile': {
                'companion_name': profile.companion_name,
                'personality_type': profile.personality_type,
                'communication_style': profile.communication_style,
                'preferred_language': profile.preferred_language,
                'timezone': profile.timezone,
                'avatar_style': profile.avatar_style,
                'preferred_voice': profile.preferred_voice,
                'voice_speed': profile.voice_speed,
                'voice_pitch': profile.voice_pitch,
                'ai_assistance_level': profile.ai_assistance_level,
                'privacy_level': profile.privacy_level,
                'notifications_enabled': profile.notifications_enabled,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def user_emotion_data(request):
    """
    Current and historical emotion data
    Returns: current emotion, trends, patterns, mental health status
    """
    try:
        user = request.user
        
        # Current emotion
        current_emotion = EmotionEvent.objects.filter(
            user=user
        ).order_by('-timestamp').first()
        
        # Recent emotions (last 24 hours)
        cutoff_24h = timezone.now() - timedelta(hours=24)
        emotions_24h = EmotionEvent.objects.filter(
            user=user,
            timestamp__gte=cutoff_24h
        ).order_by('-timestamp')
        
        # Emotion distribution (last 7 days)
        cutoff_7d = timezone.now() - timedelta(days=7)
        emotions_7d = EmotionEvent.objects.filter(
            user=user,
            timestamp__gte=cutoff_7d
        )
        
        emotion_distribution = {}
        for emotion in emotions_7d.values('emotion').distinct():
            emotion_name = emotion['emotion']
            count = emotions_7d.filter(emotion=emotion_name).count()
            avg_intensity = emotions_7d.filter(emotion=emotion_name).aggregate(
                avg=Avg('intensity')
            )['avg'] or 0
            emotion_distribution[emotion_name] = {
                'count': count,
                'average_intensity': round(avg_intensity, 2)
            }
        
        # Mental health status
        burnout_assessment = BurnoutRiskAssessment.objects.filter(
            user=user
        ).order_by('-timestamp').first()
        
        return JsonResponse({
            'status': 'success',
            'current_emotion': {
                'emotion': current_emotion.emotion if current_emotion else None,
                'intensity': current_emotion.intensity if current_emotion else None,
                'timestamp': current_emotion.timestamp.isoformat() if current_emotion else None,
                'context': current_emotion.context if current_emotion else None,
            } if current_emotion else None,
            'emotion_trends': {
                'last_24_hours': {
                    'total_entries': emotions_24h.count(),
                    'emotions': list(emotions_24h.values('emotion', 'intensity', 'timestamp')[:20]),
                },
                'last_7_days': {
                    'distribution': emotion_distribution,
                    'total_entries': emotions_7d.count(),
                }
            },
            'mental_health': {
                'burnout_risk': {
                    'level': burnout_assessment.risk_level if burnout_assessment else None,
                    'score': round(burnout_assessment.risk_score, 2) if burnout_assessment else None,
                    'last_assessed': burnout_assessment.timestamp.isoformat() if burnout_assessment else None,
                },
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def user_productivity_data(request):
    """
    Task completion, productivity metrics, and goal progress
    Returns: tasks, completion rates, productivity trends
    """
    try:
        user = request.user
        
        # Task statistics
        total_tasks = Task.objects.filter(user=user).count()
        completed_tasks = Task.objects.filter(user=user, completed_at__isnull=False).count()
        pending_tasks = Task.objects.filter(user=user, completed_at__isnull=True).count()
        
        # Completion rate (last 30 days)
        cutoff_30d = timezone.now() - timedelta(days=30)
        tasks_30d = Task.objects.filter(user=user, created_at__gte=cutoff_30d)
        completed_30d = tasks_30d.filter(completed_at__isnull=False).count()
        completion_rate_30d = (completed_30d / tasks_30d.count() * 100) if tasks_30d.count() > 0 else 0
        
        # Daily completion trend (last 7 days)
        daily_completions = {}
        for i in range(7):
            day = (timezone.now() - timedelta(days=i)).date()
            count = Task.objects.filter(
                user=user,
                completed_at__date=day
            ).count()
            daily_completions[day.isoformat()] = count
        
        # Tasks by priority
        tasks_by_priority = {}
        for priority in ['high', 'medium', 'low']:
            count = Task.objects.filter(user=user, priority=priority).count()
            tasks_by_priority[priority] = count
        
        # Upcoming tasks
        upcoming_tasks = Task.objects.filter(
            user=user,
            completed_at__isnull=True,
            due_date__gte=timezone.now()
        ).order_by('due_date')[:10]
        
        upcoming_list = [
            {
                'id': t.id,
                'title': t.title,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'priority': t.priority,
                'emotion_tag': t.emotion_tag
            }
            for t in upcoming_tasks
        ]
        
        return JsonResponse({
            'status': 'success',
            'task_statistics': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'completion_rate_all_time': round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0,
                'completion_rate_30_days': round(completion_rate_30d, 2),
            },
            'daily_trends': {
                'last_7_days': daily_completions,
            },
            'tasks_by_priority': tasks_by_priority,
            'upcoming_tasks': upcoming_list,
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def user_engagement_data(request):
    """
    Gamification, achievements, streaks, and engagement metrics
    Returns: achievements, badges, streaks, points, level
    """
    try:
        user = request.user
        
        # Streak data
        streak_tracker, _ = StreakTracker.objects.get_or_create(user=user)
        
        # Achievements
        user_achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
        achievements_list = [
            {
                'id': ua.achievement.id,
                'name': ua.achievement.name,
                'description': ua.achievement.description,
                'icon_url': ua.achievement.icon_url if hasattr(ua.achievement, 'icon_url') else None,
                'earned_at': ua.earned_at.isoformat(),
                'points': ua.achievement.points if hasattr(ua.achievement, 'points') else 0,
            }
            for ua in user_achievements
        ]
        
        # Daily interaction summary
        today = timezone.now().date()
        daily_interaction, _ = DailyCompanionInteraction.objects.get_or_create(
            user=user, date=today
        )
        
        return JsonResponse({
            'status': 'success',
            'gamification': {
                'points': streak_tracker.points_earned,
                'level': streak_tracker.level,
                'badges': streak_tracker.badges_earned,
            },
            'streaks': {
                'current_streak': streak_tracker.current_streak,
                'longest_streak': streak_tracker.longest_streak,
                'last_activity_date': streak_tracker.last_activity_date.isoformat(),
            },
            'activity_counts': {
                'daily_checkins': streak_tracker.daily_checkins,
                'journal_entries': streak_tracker.journal_entries,
                'coaching_sessions': streak_tracker.coaching_sessions,
                'conversations_completed': streak_tracker.conversations_completed,
            },
            'achievements': {
                'total_earned': len(achievements_list),
                'achievements': achievements_list,
            },
            'daily_status': {
                'date': today.isoformat(),
                'morning_greeting_sent': daily_interaction.morning_greeting_sent,
                'evening_reflection_sent': daily_interaction.evening_reflection_sent,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def user_companion_data(request):
    """
    Companion interaction history and conversation data
    Returns: recent conversations, journals, coaching sessions
    """
    try:
        user = request.user
        
        profile, _ = CompanionProfile.objects.get_or_create(user=user)
        
        # Recent conversations
        recent_conversations = Conversation.objects.filter(
            user=user
        ).order_by('-started_at')[:10]
        
        conversations_list = [
            {
                'id': c.session_id,
                'type': c.conversation_type,
                'started_at': c.started_at.isoformat(),
                'duration_minutes': c.duration_minutes,
                'message_count': c.messages.count(),
                'user_emotion_start': c.user_emotion_at_start,
            }
            for c in recent_conversations
        ]
        
        # Recent journal entries
        recent_journals = JournalEntry.objects.filter(
            user=user
        ).order_by('-entry_date')[:10]
        
        journals_list = [
            {
                'id': j.id,
                'date': j.entry_date.isoformat(),
                'primary_emotion': j.primary_emotion,
                'emotion_intensity': j.emotion_intensity,
                'mood': j.mood,
                'summary': j.key_moments[:100] if j.key_moments else '',
                'ai_insights': j.ai_insights,
            }
            for j in recent_journals
        ]
        
        # Recent coaching sessions
        recent_coaching = LifeCoachingSession.objects.filter(
            user=user
        ).order_by('-session_date')[:5]
        
        coaching_list = [
            {
                'id': c.id,
                'date': c.session_date.isoformat(),
                'topic': c.topic,
                'duration_minutes': c.duration_minutes,
                'key_insights': c.key_insights[:100] if c.key_insights else '',
                'action_items': c.action_items,
            }
            for c in recent_coaching
        ]
        
        return JsonResponse({
            'status': 'success',
            'companion_profile': {
                'name': profile.companion_name,
                'personality': profile.personality_type,
                'communication_style': profile.communication_style,
            },
            'conversations': {
                'total': Conversation.objects.filter(user=user).count(),
                'recent': conversations_list,
            },
            'journal_entries': {
                'total': JournalEntry.objects.filter(user=user).count(),
                'recent': journals_list,
            },
            'coaching_sessions': {
                'total': LifeCoachingSession.objects.filter(user=user).count(),
                'recent': coaching_list,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def user_complete_profile(request):
    """
    Complete unified user profile combining all data
    Returns: all user data in one response for frontend initialization
    """
    try:
        # Get all user data
        profile_response = user_profile_data(request).json()
        emotion_response = user_emotion_data(request).json()
        productivity_response = user_productivity_data(request).json()
        engagement_response = user_engagement_data(request).json()
        companion_response = user_companion_data(request).json()
        
        # Combine into unified response
        complete_profile = {
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'profile': profile_response.get('profile', {}),
            'user': profile_response.get('user', {}),
            'emotions': emotion_response.get('current_emotion', {}),
            'emotion_trends': emotion_response.get('emotion_trends', {}),
            'mental_health': emotion_response.get('mental_health', {}),
            'productivity': {
                'task_statistics': productivity_response.get('task_statistics', {}),
                'daily_trends': productivity_response.get('daily_trends', {}),
                'tasks_by_priority': productivity_response.get('tasks_by_priority', {}),
                'upcoming_tasks': productivity_response.get('upcoming_tasks', []),
            },
            'engagement': {
                'gamification': engagement_response.get('gamification', {}),
                'streaks': engagement_response.get('streaks', {}),
                'activity_counts': engagement_response.get('activity_counts', {}),
                'achievements': engagement_response.get('achievements', {}),
                'daily_status': engagement_response.get('daily_status', {}),
            },
            'companion': {
                'profile': companion_response.get('companion_profile', {}),
                'conversations': companion_response.get('conversations', {}),
                'journal': companion_response.get('journal_entries', {}),
                'coaching': companion_response.get('coaching_sessions', {}),
            }
        }
        
        return JsonResponse(complete_profile)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def user_mental_health_data(request):
    """
    Mental health specific data
    Returns: crisis status, mental health metrics, support resources
    """
    try:
        user = request.user
        
        # Recent crisis assessments
        recent_crisis = CrisisDetection.objects.filter(
            user=user
        ).order_by('-detected_at')[:5]
        
        crisis_list = [
            {
                'id': c.id,
                'type': c.crisis_type,
                'severity': c.crisis_severity,
                'detected_at': c.detected_at.isoformat(),
                'action_taken': c.action_taken,
            }
            for c in recent_crisis
        ]
        
        # Burnout assessment
        burnout = BurnoutRiskAssessment.objects.filter(
            user=user
        ).order_by('-timestamp').first()
        
        return JsonResponse({
            'status': 'success',
            'mental_health_metrics': {
                'current_crisis_level': max([c.crisis_severity for c in recent_crisis], default=0),
                'burnout_risk': {
                    'level': burnout.risk_level if burnout else 'low',
                    'score': round(burnout.risk_score, 2) if burnout else 0,
                    'factors': burnout.risk_factors if burnout else [],
                },
                'recent_crises': crisis_list,
            },
            'support_resources': {
                'emergency_contact_configured': hasattr(user, 'emergency_contact'),
                'human_support_available': True,
                'crisis_hotline': True,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
