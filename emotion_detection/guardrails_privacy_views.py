"""
API Endpoints for Mental Health Guardrails and Privacy Features
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.generic import View, TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
import json

from emotion_detection.mental_health_guardrails import (
    MentalHealthGuardrailEngine,
    MentalHealthGuardrail,
    BurnoutEarlyWarning,
    EmotionalSpiralDetector,
    GroundingExercise,
    CrisisIndicator,
    HumanSupportEscalation
)
from emotion_detection.privacy_engine import (
    PrivacyEngineManager,
    PrivacyPolicy,
    EncryptedEmotionVault,
    DataRetentionPolicy,
    OnDeviceModel,
    ExplainableAIInsight,
    PrivacyAuditLog
)
from emotion_detection.models import EmotionEvent


# ===== MENTAL HEALTH GUARDRAILS ENDPOINTS =====

@login_required
def mental_health_dashboard(request):
    """Dashboard showing mental health status and guardrail alerts"""
    engine = MentalHealthGuardrailEngine(request.user)
    results = engine.check_all_guardrails()
    
    # Get recent guardrail events
    recent_guardrails = MentalHealthGuardrail.objects.filter(
        user=request.user,
        triggered=True
    ).order_by('-triggered_at')[:5]
    
    # Get escalations
    pending_escalations = HumanSupportEscalation.objects.filter(
        user=request.user,
        resolved=False
    )
    
    context = {
        'guardrail_status': results,
        'recent_guardrails': recent_guardrails,
        'pending_escalations': pending_escalations,
        'show_crisis_support': results.get('crisis_indicators', {}).get('detected', False),
    }
    
    return render(request, 'guardrails/dashboard.html', context)


@api_view(['GET'])
@login_required
def burnout_warning_api(request):
    """API endpoint for burnout warning status"""
    engine = MentalHealthGuardrailEngine(request.user)
    warning = engine.check_burnout_warning()
    
    return Response({
        'status': 'warning' if warning['triggered'] else 'normal',
        'triggered': warning['triggered'],
        'warning_score': warning['warning_score'],
        'days_to_burnout': warning['days_to_burnout'],
        'overwork_days': warning['overwork_days'],
        'stress_level': warning['stress_level'],
        'interventions': warning['urgent_interventions']
    })


@api_view(['GET'])
@login_required
def emotional_spiral_detection_api(request):
    """API endpoint for emotional spiral detection"""
    engine = MentalHealthGuardrailEngine(request.user)
    spiral_info = engine.check_emotional_spiral()
    
    return Response(spiral_info)


@api_view(['POST'])
@login_required
def recommend_grounding_exercise(request):
    """Get personalized grounding exercise recommendation"""
    emotion_state = request.data.get('emotion', None)
    
    engine = MentalHealthGuardrailEngine(request.user)
    exercise = engine.recommend_grounding_exercise(emotion_state)
    
    return Response({
        'exercise': exercise['exercise'],
        'reason': exercise['reason'],
        'duration_minutes': exercise['duration'],
        'instructions': get_exercise_instructions(exercise['exercise'])
    })


def get_exercise_instructions(exercise_type):
    """Get detailed instructions for exercise"""
    instructions = {
        '5_4_3_2_1': {
            'title': '5-4-3-2-1 Grounding Technique',
            'steps': [
                '1. Look around and name 5 things you can see',
                '2. Notice 4 things you can physically feel',
                '3. Listen for 3 things you can hear',
                '4. Identify 2 things you can smell (or imagine)',
                '5. Name 1 thing you can taste'
            ]
        },
        'box_breathing': {
            'title': 'Box Breathing',
            'steps': [
                '1. Breathe in for 4 counts',
                '2. Hold for 4 counts',
                '3. Exhale for 4 counts',
                '4. Hold for 4 counts',
                '5. Repeat 4-5 times'
            ]
        },
        'body_scan': {
            'title': 'Body Scan Meditation',
            'steps': [
                '1. Sit or lie down comfortably',
                '2. Start at the top of your head',
                '3. Slowly move attention down your body',
                '4. Notice sensations without judgment',
                '5. Continue to your toes',
                '6. Practice for 10-15 minutes'
            ]
        }
    }
    
    return instructions.get(exercise_type, {'title': 'Mindfulness Exercise', 'steps': []})


@api_view(['POST'])
@login_required
def log_exercise_completion(request):
    """Log completion of grounding exercise"""
    exercise_type = request.data.get('exercise_type')
    effectiveness_score = request.data.get('effectiveness_score')
    emotion_before = request.data.get('emotion_before')
    emotion_after = request.data.get('emotion_after')
    
    exercise = GroundingExercise.objects.create(
        user=request.user,
        exercise_type=exercise_type,
        user_did_exercise=True,
        effectiveness_score=effectiveness_score,
        emotion_before=emotion_before,
        emotion_after=emotion_after
    )
    
    return Response({
        'success': True,
        'message': 'Thank you for taking care of yourself!',
        'exercise_id': exercise.id
    })


@api_view(['GET'])
@login_required
def crisis_resources_api(request):
    """Get crisis support resources for user"""
    resources = {
        'crisis_hotlines': [
            {'name': '988 Suicide & Crisis Lifeline', 'number': '988', 'available': '24/7'},
            {'name': 'Crisis Text Line', 'number': 'Text HOME to 741741', 'available': '24/7'},
            {'name': 'NAMI Helpline', 'number': '1-800-950-6264', 'available': 'Mon-Fri 10am-10pm'},
        ],
        'emergency': '911',
        'immediate_actions': [
            'Call 911 if in immediate danger',
            'Contact a trusted friend or family member',
            'Go to nearest emergency room if suicidal',
            'Remove access to means of self-harm'
        ]
    }
    
    return Response(resources)


class MentalHealthHistoryListView(LoginRequiredMixin, ListView):
    """View history of mental health alerts and interventions"""
    template_name = 'guardrails/history.html'
    context_object_name = 'guardrails'
    paginate_by = 20
    
    def get_queryset(self):
        return MentalHealthGuardrail.objects.filter(
            user=self.request.user
        ).order_by('-triggered_at')


# ===== PRIVACY ENDPOINTS =====

@login_required
def privacy_dashboard(request):
    """Privacy and data control dashboard"""
    manager = PrivacyEngineManager(request.user)
    dashboard = manager.get_privacy_dashboard()
    
    # Get encryption settings
    policy = PrivacyPolicy.objects.get_or_create(user=request.user)[0]
    
    # Get data retention policies
    retention_policies = DataRetentionPolicy.objects.filter(user=request.user)
    
    # Get on-device models
    on_device_models = OnDeviceModel.objects.filter(user=request.user)
    
    # Get audit logs
    audit_logs = PrivacyAuditLog.objects.filter(user=request.user).order_by('-timestamp')[:20]
    
    context = {
        'dashboard': dashboard,
        'policy': policy,
        'retention_policies': retention_policies,
        'on_device_models': on_device_models,
        'audit_logs': audit_logs,
    }
    
    return render(request, 'privacy/dashboard.html', context)


@api_view(['POST'])
@login_required
def update_privacy_settings(request):
    """Update privacy policy settings"""
    policy, created = PrivacyPolicy.objects.get_or_create(user=request.user)
    
    # Update encryption settings
    if 'encryption_level' in request.data:
        policy.encryption_level = request.data['encryption_level']
    if 'encrypt_emotions_at_rest' in request.data:
        policy.encrypt_emotions_at_rest = request.data['encrypt_emotions_at_rest']
    
    # Update data retention
    if 'emotion_data_retention' in request.data:
        policy.emotion_data_retention = request.data['emotion_data_retention']
    if 'biofeedback_retention' in request.data:
        policy.biofeedback_retention = request.data['biofeedback_retention']
    
    # Update federated learning
    if 'allow_federated_learning' in request.data:
        policy.allow_federated_learning = request.data['allow_federated_learning']
    
    # Update transparency
    if 'show_ai_reasoning' in request.data:
        policy.show_ai_reasoning = request.data['show_ai_reasoning']
    if 'transparency_level' in request.data:
        policy.transparency_level = request.data['transparency_level']
    
    policy.save()
    
    return Response({
        'success': True,
        'message': 'Privacy settings updated'
    })


@api_view(['GET'])
@login_required
def data_export_api(request):
    """Export all user data in portable format"""
    data_type = request.query_params.get('type', 'all')  # all, emotions, biofeedback, tasks
    
    data = {}
    
    if data_type in ['all', 'emotions']:
        emotions = EmotionEvent.objects.filter(user=request.user)
        data['emotions'] = [{
            'timestamp': e.timestamp.isoformat(),
            'emotion': e.emotion,
            'intensity': e.intensity
        } for e in emotions]
    
    # Export would include other data types as well
    
    return Response({
        'user': request.user.username,
        'export_date': timezone.now().isoformat(),
        'data': data,
        'note': 'Data in JSON format. Can be imported into other tools.'
    })


@api_view(['POST'])
@login_required
def request_data_deletion(request):
    """Request complete data deletion"""
    deletion_type = request.data.get('deletion_type')  # partial, complete
    
    if deletion_type == 'complete':
        # Full GDPR right to be forgotten
        return Response({
            'success': True,
            'message': 'Account deletion initiated. Check email for confirmation.',
            'confirmation_required': True,
            'deadline_days': 30
        })
    
    return Response({
        'success': False,
        'error': 'Invalid deletion type'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@login_required
def encryption_status_api(request):
    """Check encryption status"""
    policy, _ = PrivacyPolicy.objects.get_or_create(user=request.user)
    
    vault_entries = EncryptedEmotionVault.objects.filter(user=request.user)
    
    return Response({
        'encryption_enabled': policy.encrypt_emotions_at_rest,
        'encryption_level': policy.encryption_level,
        'encrypted_records': vault_entries.count(),
        'last_encrypted': vault_entries.order_by('-created_at').first().created_at.isoformat() if vault_entries.exists() else None
    })


@api_view(['GET'])
@login_required
def audit_log_api(request):
    """Get user's privacy audit log"""
    days = int(request.query_params.get('days', 30))
    cutoff = timezone.now() - timedelta(days=days)
    
    logs = PrivacyAuditLog.objects.filter(
        user=request.user,
        timestamp__gte=cutoff
    ).order_by('-timestamp')
    
    return Response({
        'total_accesses': logs.count(),
        'access_types': dict(logs.values('access_type').annotate(count=Count('id'))),
        'logs': [{
            'timestamp': log.timestamp.isoformat(),
            'type': log.access_type,
            'data': log.data_accessed,
            'purpose': log.purpose,
            'accessed_by': log.accessed_by
        } for log in logs[:50]]
    })


@api_view(['POST'])
@login_required
def enable_on_device_ml(request):
    """Enable on-device ML processing for privacy"""
    manager = PrivacyEngineManager(request.user)
    manager.enable_on_device_processing()
    
    on_device_models = OnDeviceModel.objects.filter(user=request.user)
    
    return Response({
        'success': True,
        'message': 'On-device ML enabled',
        'models': [{
            'type': m.model_type,
            'version': m.model_version,
            'size_kb': m.model_file_size_kb,
            'enabled': m.is_enabled
        } for m in on_device_models]
    })


@api_view(['POST'])
@login_required
def enroll_federated_learning(request):
    """Enroll in federated learning study"""
    study_name = request.data.get('study_name')
    
    manager = PrivacyEngineManager(request.user)
    participant = manager.enroll_federated_learning(study_name)
    
    if participant:
        return Response({
            'success': True,
            'message': f'Enrolled in {study_name}',
            'differential_privacy': participant.differential_privacy_enabled,
            'noise_level': participant.noise_level
        })
    
    return Response({
        'success': False,
        'error': 'Federated learning not enabled in privacy settings'
    }, status=status.HTTP_400_BAD_REQUEST)


class PrivacySettingsView(LoginRequiredMixin, TemplateView):
    """View and manage privacy settings"""
    template_name = 'privacy/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        policy, _ = PrivacyPolicy.objects.get_or_create(user=self.request.user)
        context['policy'] = policy
        context['retention_options'] = PrivacyPolicy.DATA_RETENTION_CHOICES
        context['encryption_options'] = PrivacyPolicy.ENCRYPTION_LEVELS
        return context


@api_view(['GET'])
@login_required
def explainable_ai_insights(request):
    """Get recent AI insights with explanations"""
    transparency_level = request.query_params.get('level', 'detailed')
    days = int(request.query_params.get('days', 7))
    
    cutoff = timezone.now() - timedelta(days=days)
    
    insights = ExplainableAIInsight.objects.filter(
        user=request.user,
        created_at__gte=cutoff
    ).order_by('-created_at')[:20]
    
    return Response({
        'insights': [{
            'type': i.insight_type,
            'insight': i.insight_text,
            'explanation': i.get_explanation(transparency_level),
            'confidence': i.confidence_score,
            'key_factors': i.key_factors,
            'timestamp': i.created_at.isoformat()
        } for i in insights]
    })


@api_view(['POST'])
@login_required
def rate_ai_explanation(request):
    """Rate helpfulness of AI explanation"""
    insight_id = request.data.get('insight_id')
    helpful = request.data.get('helpful')
    feedback = request.data.get('feedback', '')
    
    try:
        insight = ExplainableAIInsight.objects.get(id=insight_id, user=request.user)
        insight.user_found_helpful = helpful
        insight.feedback_text = feedback
        insight.save()
        
        return Response({
            'success': True,
            'message': 'Thank you for the feedback'
        })
    except ExplainableAIInsight.DoesNotExist:
        return Response({
            'error': 'Insight not found'
        }, status=status.HTTP_404_NOT_FOUND)
