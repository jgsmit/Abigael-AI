"""
Comprehensive API endpoints for user data and metrics
Provides unified data structure for frontend consumption
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count, Q, Sum
from django.conf import settings
from django.core.mail import mail_admins
import json

from .companion_models import (
    CompanionProfile, Conversation, Message, JournalEntry,
    LifeCoachingSession, StreakTracker, Achievement, UserAchievement,
    DailyCompanionInteraction, CrisisDetection
)
from .models import EmotionEvent, BurnoutRiskAssessment
from tasks.models import Task
from .autonomous_models import EmotionEvent as AutoEmotionEvent, TaskFeedback, RLModel, FederatedLearningNode, AutoConfiguration
from .autonomous_learning import learning_manager


def _resolve_readiness_grade(score):
    """Map numeric readiness score to a simple grade for dashboards."""
    if score >= 90:
        return 'excellent'
    if score >= 75:
        return 'good'
    if score >= 60:
        return 'fair'
    return 'needs_attention'


def _get_auto_config(user, parameter_name, default):
    config = AutoConfiguration.objects.filter(
        user=user,
        category='system_health',
        parameter_name=parameter_name,
    ).first()
    if not config:
        return default
    return config.parameter_value


def _set_auto_config(user, parameter_name, value, reason='system health update'):
    AutoConfiguration.objects.update_or_create(
        user=user,
        category='system_health',
        parameter_name=parameter_name,
        defaults={
            'parameter_value': value,
            'optimization_target': 'efficiency',
            'adjustment_reason': reason,
            'is_auto_tuned': True,
        },
    )


def _persist_daily_readiness_snapshot(user, score, grade, timestamp):
    snapshots = _get_auto_config(user, 'daily_readiness_snapshots', [])
    if not isinstance(snapshots, list):
        snapshots = []

    day_key = timestamp.date().isoformat()
    snapshot = {
        'date': day_key,
        'score': score,
        'grade': grade,
        'generated_at': timestamp.isoformat(),
    }

    replaced = False
    for idx, existing in enumerate(snapshots):
        if existing.get('date') == day_key:
            snapshots[idx] = snapshot
            replaced = True
            break
    if not replaced:
        snapshots.append(snapshot)

    snapshots = sorted(snapshots, key=lambda item: item.get('date', ''))[-30:]
    _set_auto_config(user, 'daily_readiness_snapshots', snapshots, reason='daily readiness snapshot')
    return snapshots


def _evaluate_low_readiness_streak(snapshots, threshold, days_required):
    recent = sorted(snapshots, key=lambda item: item.get('date', ''), reverse=True)
    streak = 0
    for item in recent:
        if item.get('score', 0) < threshold:
            streak += 1
        else:
            break
    return streak, streak >= days_required


def _maybe_notify_admins_for_low_readiness(user, readiness_score, streak_count, threshold, days_required, now):
    if streak_count < days_required:
        return False

    state = _get_auto_config(user, 'readiness_alert_state', {})
    if not isinstance(state, dict):
        state = {}

    today = now.date().isoformat()
    last_alert_date = state.get('last_alert_date')
    if last_alert_date == today:
        return False

    subject = f'Abigael AI readiness alert for {user.username}'
    message = (
        f'User: {user.username}\n'
        f'Readiness score: {readiness_score}\n'
        f'Threshold: {threshold}\n'
        f'Consecutive days below threshold: {streak_count}\n'
        f'Required days for alert: {days_required}\n'
    )

    try:
        mail_admins(subject, message, fail_silently=True)
    except Exception:
        pass

    state.update({
        'last_alert_date': today,
        'last_alert_score': readiness_score,
        'last_alert_streak': streak_count,
    })
    _set_auto_config(user, 'readiness_alert_state', state, reason='low readiness admin alert')
    return True


def _perform_self_heal_actions(user):
    actions = []
    async_configured = bool(getattr(settings, 'CELERY_BROKER_URL', '')) and bool(getattr(settings, 'CELERY_RESULT_BACKEND', ''))

    if async_configured and not getattr(learning_manager, 'is_running', False):
        try:
            learning_manager.start_learning()
            actions.append({'action': 'start_learning_manager', 'status': 'executed'})
        except Exception as exc:
            actions.append({'action': 'start_learning_manager', 'status': 'failed', 'error': str(exc)})

    if not actions:
        actions.append({'action': 'no_op', 'status': 'not_needed'})

    _set_auto_config(user, 'last_self_heal_actions', {'actions': actions, 'at': timezone.now().isoformat()}, reason='self heal execution')
    return actions


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
        user = request.user
        profile, _ = CompanionProfile.objects.get_or_create(user=user)

        # Emotions
        current_emotion = EmotionEvent.objects.filter(user=user).order_by('-timestamp').first()
        cutoff_24h = timezone.now() - timedelta(hours=24)
        cutoff_7d = timezone.now() - timedelta(days=7)
        emotions_24h = EmotionEvent.objects.filter(user=user, timestamp__gte=cutoff_24h).order_by('-timestamp')
        emotions_7d = EmotionEvent.objects.filter(user=user, timestamp__gte=cutoff_7d)

        emotion_distribution = {}
        for emotion in emotions_7d.values('emotion').distinct():
            emotion_name = emotion['emotion']
            emotion_records = emotions_7d.filter(emotion=emotion_name)
            emotion_distribution[emotion_name] = {
                'count': emotion_records.count(),
                'average_intensity': round(emotion_records.aggregate(avg=Avg('intensity'))['avg'] or 0, 2),
            }

        burnout_assessment = BurnoutRiskAssessment.objects.filter(user=user).order_by('-timestamp').first()

        # Productivity
        total_tasks = Task.objects.filter(user=user).count()
        completed_tasks = Task.objects.filter(user=user, completed_at__isnull=False).count()
        pending_tasks = Task.objects.filter(user=user, completed_at__isnull=True).count()

        cutoff_30d = timezone.now() - timedelta(days=30)
        tasks_30d = Task.objects.filter(user=user, created_at__gte=cutoff_30d)
        completed_30d = tasks_30d.filter(completed_at__isnull=False).count()
        completion_rate_30d = (completed_30d / tasks_30d.count() * 100) if tasks_30d.count() > 0 else 0

        daily_completions = {}
        for i in range(7):
            day = (timezone.now() - timedelta(days=i)).date()
            daily_completions[day.isoformat()] = Task.objects.filter(user=user, completed_at__date=day).count()

        tasks_by_priority = {
            priority: Task.objects.filter(user=user, priority=priority).count()
            for priority in ['high', 'medium', 'low']
        }

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
                'emotion_tag': t.emotion_tag,
            }
            for t in upcoming_tasks
        ]

        # Engagement
        streak_tracker, _ = StreakTracker.objects.get_or_create(user=user)
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

        today = timezone.now().date()
        daily_interaction, _ = DailyCompanionInteraction.objects.get_or_create(user=user, date=today)

        # Companion
        recent_conversations = Conversation.objects.filter(user=user).order_by('-started_at')[:10]
        recent_journals = JournalEntry.objects.filter(user=user).order_by('-entry_date')[:10]
        recent_coaching = LifeCoachingSession.objects.filter(user=user).order_by('-session_date')[:5]

        payload = {
            'timestamp': timezone.now().isoformat(),
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
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
            },
            'emotions': {
                'current_emotion': {
                    'emotion': current_emotion.emotion if current_emotion else None,
                    'intensity': current_emotion.intensity if current_emotion else None,
                    'timestamp': current_emotion.timestamp.isoformat() if current_emotion else None,
                    'context': current_emotion.context if current_emotion else None,
                } if current_emotion else None,
            },
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
                    'risk_level': burnout_assessment.risk_level if burnout_assessment else None,
                    'risk_score': round(burnout_assessment.risk_score, 2) if burnout_assessment else None,
                    'timestamp': burnout_assessment.timestamp.isoformat() if burnout_assessment else None,
                },
            },
            'productivity': {
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
            },
            'engagement': {
                'points': streak_tracker.points_earned,
                'level': streak_tracker.level,
                'badges': streak_tracker.badges_earned,
                'streaks': {
                    'current_streak': streak_tracker.current_streak,
                    'longest_streak': streak_tracker.longest_streak,
                    'last_activity_date': streak_tracker.last_activity_date.isoformat() if streak_tracker.last_activity_date else None,
                },
                'activity_counts': {
                    'daily_checkins': streak_tracker.daily_checkins,
                    'journal_entries': streak_tracker.journal_entries,
                    'coaching_sessions': streak_tracker.coaching_sessions,
                    'conversations_completed': streak_tracker.conversations_completed,
                },
                'achievements': achievements_list,
                'daily_status': {
                    'date': today.isoformat(),
                    'morning_greeting_sent': daily_interaction.morning_greeting_sent,
                    'evening_reflection_sent': daily_interaction.evening_reflection_sent,
                },
            },
            'companion': {
                'profile': {
                    'name': profile.companion_name,
                    'personality': profile.personality_type,
                    'communication_style': profile.communication_style,
                },
                'conversations': {
                    'total': Conversation.objects.filter(user=user).count(),
                    'recent': [
                        {
                            'id': c.session_id,
                            'type': c.conversation_type,
                            'started_at': c.started_at.isoformat(),
                            'duration_minutes': c.duration_minutes,
                            'message_count': c.messages.count(),
                            'user_emotion_start': c.user_emotion_at_start,
                        }
                        for c in recent_conversations
                    ],
                },
                'recent_journals': [
                    {
                        'id': j.id,
                        'date': j.entry_date.isoformat(),
                        'primary_emotion': j.primary_emotion,
                        'emotion_intensity': j.emotion_intensity,
                        'mood': j.mood,
                        'key_moments': j.key_moments,
                        'summary': j.key_moments[:100] if j.key_moments else '',
                        'ai_insights': j.ai_insights,
                    }
                    for j in recent_journals
                ],
                'coaching': {
                    'total': LifeCoachingSession.objects.filter(user=user).count(),
                    'recent': [
                        {
                            'id': c.id,
                            'date': c.session_date.isoformat(),
                            'topic': c.topic,
                            'duration_minutes': c.duration_minutes,
                            'key_insights': c.key_insights[:100] if c.key_insights else '',
                            'action_items': c.action_items,
                        }
                        for c in recent_coaching
                    ],
                },
            }
        }

        return JsonResponse({'status': 'success', 'data': payload})
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


@login_required
def system_memory_health(request):
    """
    Operational health endpoint for memory and autonomous learning reliability.
    Returns persistence, freshness, and learning-loop readiness signals.
    """
    try:
        user = request.user

        # Storage checks
        db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        db_name = str(settings.DATABASES.get('default', {}).get('NAME', ''))
        db_exists = True
        if 'sqlite' in db_engine:
            from pathlib import Path
            db_exists = Path(db_name).exists()

        # User memory surfaces
        conversation_count = Conversation.objects.filter(user=user).count()
        message_count = Message.objects.filter(conversation__user=user).count()
        journal_count = JournalEntry.objects.filter(user=user).count()
        emotion_count = AutoEmotionEvent.objects.filter(user=user).count()
        feedback_count = TaskFeedback.objects.filter(user=user).count()
        rl_models_count = RLModel.objects.filter(user=user, is_active=True).count()

        latest_conversation = Conversation.objects.filter(user=user).order_by('-started_at').first()
        latest_journal = JournalEntry.objects.filter(user=user).order_by('-entry_time').first()
        latest_emotion = AutoEmotionEvent.objects.filter(user=user).order_by('-timestamp').first()
        latest_feedback = TaskFeedback.objects.filter(user=user).order_by('-timestamp').first()
        latest_model_training = RLModel.objects.filter(user=user).order_by('-last_training').first()

        learning_flags = {
            'autonomous_learning_enabled': bool(getattr(settings, 'AUTONOMOUS_LEARNING_ENABLED', False)),
            'federated_learning_enabled': bool(getattr(settings, 'FEDERATED_LEARNING_ENABLED', False)),
            'knowledge_graph_enabled': bool(getattr(settings, 'KNOWLEDGE_GRAPH_ENABLED', False)),
            'learning_loop_running': bool(getattr(learning_manager, 'is_running', False)),
            'celery_broker_configured': bool(getattr(settings, 'CELERY_BROKER_URL', '')),
            'celery_backend_configured': bool(getattr(settings, 'CELERY_RESULT_BACKEND', '')),
        }

        federated_node = FederatedLearningNode.objects.filter(user=user).first()

        # Reliability score (0-100)
        score = 100
        recommendations = []

        if not db_exists:
            score -= 50
            recommendations.append('Database file not found. Verify persistent storage mount.')
        if conversation_count == 0 and journal_count == 0:
            score -= 10
            recommendations.append('No stored conversation/journal memory yet. Use chat/journal to build memory.')
        if not learning_flags['learning_loop_running']:
            score -= 15
            recommendations.append('Autonomous learning loop is not running. Start background learning manager.')
        if not learning_flags['celery_broker_configured']:
            score -= 10
            recommendations.append('Celery broker is not configured. Async model training may not run.')
        if rl_models_count == 0:
            score -= 10
            recommendations.append('No active RL model for this user yet. Submit task feedback to train one.')

        score = max(0, score)

        return JsonResponse({
            'status': 'success',
            'memory_health': {
                'reliability_score': score,
                'storage': {
                    'engine': db_engine,
                    'database_exists': db_exists,
                    'database_name': db_name,
                },
                'persistence_counts': {
                    'conversations': conversation_count,
                    'messages': message_count,
                    'journal_entries': journal_count,
                    'emotion_events': emotion_count,
                    'task_feedback': feedback_count,
                    'active_rl_models': rl_models_count,
                },
                'freshness': {
                    'latest_conversation': latest_conversation.started_at.isoformat() if latest_conversation else None,
                    'latest_journal': latest_journal.entry_time.isoformat() if latest_journal else None,
                    'latest_emotion_event': latest_emotion.timestamp.isoformat() if latest_emotion else None,
                    'latest_feedback': latest_feedback.timestamp.isoformat() if latest_feedback else None,
                    'latest_model_training': latest_model_training.last_training.isoformat() if latest_model_training else None,
                },
                'learning_runtime': {
                    **learning_flags,
                    'federated_node_active': bool(federated_node and federated_node.is_active),
                    'federated_contributions': federated_node.total_contributions if federated_node else 0,
                },
                'recommendations': recommendations,
            },
            'message': 'Memory and autonomous learning status generated successfully.',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def system_readiness_report(request):
    """
    High-level operational readiness report for the user-facing AI system.
    Returns a score, graded status, failing checks, and prioritized actions.
    """
    try:
        user = request.user
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        checks = []

        # Check 1: engagement signal freshness
        latest_emotion = EmotionEvent.objects.filter(user=user).order_by('-timestamp').first()
        latest_journal = JournalEntry.objects.filter(user=user).order_by('-entry_time').first()
        engagement_recent = bool(
            (latest_emotion and latest_emotion.timestamp >= seven_days_ago) or
            (latest_journal and latest_journal.entry_time >= seven_days_ago)
        )
        checks.append({
            'name': 'fresh_user_signals',
            'passed': engagement_recent,
            'weight': 30,
            'details': 'Emotion or journal activity detected within the last 7 days.',
        })

        # Check 2: baseline memory persistence
        memory_events = Message.objects.filter(conversation__user=user).count() + JournalEntry.objects.filter(user=user).count()
        checks.append({
            'name': 'memory_persistence',
            'passed': memory_events >= 5,
            'weight': 25,
            'details': 'At least 5 persisted memory events (messages + journal entries).',
        })

        # Check 3: task system activity
        task_activity = Task.objects.filter(user=user, created_at__gte=seven_days_ago).exists()
        checks.append({
            'name': 'task_activity',
            'passed': task_activity,
            'weight': 20,
            'details': 'At least one task created in the last 7 days.',
        })

        # Check 4: autonomous learning runtime readiness
        learning_enabled = bool(getattr(settings, 'AUTONOMOUS_LEARNING_ENABLED', False))
        checks.append({
            'name': 'autonomous_learning_enabled',
            'passed': learning_enabled,
            'weight': 15,
            'details': 'AUTONOMOUS_LEARNING_ENABLED setting is active.',
        })

        # Check 5: async infrastructure presence
        async_ready = bool(getattr(settings, 'CELERY_BROKER_URL', '')) and bool(getattr(settings, 'CELERY_RESULT_BACKEND', ''))
        checks.append({
            'name': 'async_infrastructure',
            'passed': async_ready,
            'weight': 10,
            'details': 'Celery broker and result backend are both configured.',
        })

        readiness_score = sum(check['weight'] for check in checks if check['passed'])
        readiness_grade = _resolve_readiness_grade(readiness_score)
        failing_checks = [check for check in checks if not check['passed']]

        recommendations = []
        for check in failing_checks:
            if check['name'] == 'fresh_user_signals':
                recommendations.append('Collect a new journal entry or emotion event to refresh personalization context.')
            elif check['name'] == 'memory_persistence':
                recommendations.append('Increase memory depth with more conversations or journal entries.')
            elif check['name'] == 'task_activity':
                recommendations.append('Create at least one task this week to improve productivity coaching quality.')
            elif check['name'] == 'autonomous_learning_enabled':
                recommendations.append('Enable AUTONOMOUS_LEARNING_ENABLED in settings for adaptive behavior updates.')
            elif check['name'] == 'async_infrastructure':
                recommendations.append('Configure CELERY_BROKER_URL and CELERY_RESULT_BACKEND for async jobs.')

        snapshots = _persist_daily_readiness_snapshot(user, readiness_score, readiness_grade, now)
        threshold = int(getattr(settings, 'READINESS_ALERT_THRESHOLD', 60))
        days_required = int(getattr(settings, 'READINESS_ALERT_CONSECUTIVE_DAYS', 3))
        streak_count, alert_triggered = _evaluate_low_readiness_streak(snapshots, threshold, days_required)
        admin_notified = _maybe_notify_admins_for_low_readiness(
            user=user,
            readiness_score=readiness_score,
            streak_count=streak_count,
            threshold=threshold,
            days_required=days_required,
            now=now,
        )

        self_heal_suggested = bool(
            any(check['name'] == 'async_infrastructure' and check['passed'] for check in checks)
            and not bool(getattr(learning_manager, 'is_running', False))
        )

        return JsonResponse({
            'status': 'success',
            'system_readiness': {
                'score': readiness_score,
                'grade': readiness_grade,
                'checks': checks,
                'failing_checks': failing_checks,
                'recommendations': recommendations,
                'learning_manager_running': bool(getattr(learning_manager, 'is_running', False)),
                'generated_at': now.isoformat(),
                'history': snapshots,
                'alerting': {
                    'threshold': threshold,
                    'consecutive_days_required': days_required,
                    'current_low_score_streak': streak_count,
                    'alert_triggered': alert_triggered,
                    'admin_notified_now': admin_notified,
                },
                'self_heal': {
                    'suggested': self_heal_suggested,
                    'endpoint': '/emotion_detection/api/system/self-heal/',
                },
            },
            'message': 'System readiness report generated successfully.',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def _run_self_improvement_cycle(user):
    """Analyze recent outcomes and apply safe adaptive configuration updates."""
    now = timezone.now()
    since = now - timedelta(days=14)

    recent_feedback = TaskFeedback.objects.filter(user=user, timestamp__gte=since)
    feedback_count = recent_feedback.count()

    aggregates = recent_feedback.aggregate(
        avg_satisfaction=Avg('task_satisfaction'),
        avg_helpfulness=Avg('ai_helpfulness'),
        avg_reward=Avg('reward_score'),
        avg_emotion_change=Avg('emotion_change_rating'),
    ) if feedback_count else {}

    avg_satisfaction = float(aggregates.get('avg_satisfaction') or 0.0)
    avg_helpfulness = float(aggregates.get('avg_helpfulness') or 0.0)
    avg_reward = float(aggregates.get('avg_reward') or 0.0)
    avg_emotion_change = float(aggregates.get('avg_emotion_change') or 0.0)

    actions = []

    # Adaptive behavior tuning based on helpfulness signals
    if feedback_count >= 3 and avg_helpfulness < 3.5:
        _set_auto_config(
            user,
            'default_tone',
            {'value': 'empathetic', 'reason': 'low recent helpfulness'},
            reason='self improvement: tone adjustment',
        )
        actions.append({
            'action': 'adjust_default_tone',
            'status': 'executed',
            'new_value': 'empathetic',
        })

    # Adaptive exploration tuning for RL behavior
    current_exploration = _get_auto_config(user, 'rl_exploration_rate', {'value': 0.10})
    if isinstance(current_exploration, dict):
        current_value = float(current_exploration.get('value', 0.10))
    else:
        current_value = float(current_exploration or 0.10)

    if feedback_count >= 3:
        if avg_reward < 0:
            new_value = min(0.30, round(current_value + 0.05, 2))
            rationale = 'increase exploration due to negative reward trend'
        elif avg_reward > 0.2:
            new_value = max(0.05, round(current_value - 0.02, 2))
            rationale = 'reduce exploration due to stable positive reward trend'
        else:
            new_value = current_value
            rationale = 'reward trend is neutral; no change'

        _set_auto_config(
            user,
            'rl_exploration_rate',
            {'value': new_value, 'reason': rationale},
            reason='self improvement: exploration tuning',
        )
        actions.append({
            'action': 'tune_rl_exploration_rate',
            'status': 'executed',
            'previous': current_value,
            'new_value': new_value,
            'reason': rationale,
        })

    # Ensure background learner is active when possible
    async_configured = bool(getattr(settings, 'CELERY_BROKER_URL', '')) and bool(getattr(settings, 'CELERY_RESULT_BACKEND', ''))
    if async_configured and not getattr(learning_manager, 'is_running', False):
        try:
            learning_manager.start_learning()
            actions.append({'action': 'start_learning_manager', 'status': 'executed'})
        except Exception as exc:
            actions.append({'action': 'start_learning_manager', 'status': 'failed', 'error': str(exc)})

    if feedback_count == 0:
        actions.append({
            'action': 'collect_feedback',
            'status': 'required',
            'message': 'No recent feedback found. System needs more user feedback to improve itself.',
        })

    snapshot = {
        'timestamp': now.isoformat(),
        'window_days': 14,
        'feedback_count': feedback_count,
        'metrics': {
            'avg_satisfaction': round(avg_satisfaction, 3),
            'avg_helpfulness': round(avg_helpfulness, 3),
            'avg_reward': round(avg_reward, 3),
            'avg_emotion_change': round(avg_emotion_change, 3),
        },
        'actions': actions,
    }

    history = _get_auto_config(user, 'self_improvement_history', [])
    if not isinstance(history, list):
        history = []
    history.append(snapshot)
    history = history[-20:]
    _set_auto_config(user, 'self_improvement_history', history, reason='self improvement cycle')

    return snapshot, history


@login_required
def system_self_improve(request):
    """Run a self-improvement cycle so the AI can learn from its own outcomes."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        snapshot, history = _run_self_improvement_cycle(request.user)
        return JsonResponse({
            'status': 'success',
            'self_improvement': snapshot,
            'history_count': len(history),
            'message': 'Self-improvement cycle completed.',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def system_self_heal(request):
    """Trigger safe self-healing actions for runtime readiness issues."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        actions = _perform_self_heal_actions(request.user)
        return JsonResponse({
            'status': 'success',
            'actions': actions,
            'message': 'Self-healing actions evaluated.',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
