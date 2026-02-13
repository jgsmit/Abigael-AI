"""Views for micro-interventions."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .intervention_models import InterventionRule, InterventionContent, UserIntervention, InterventionTemplate
from .intervention_engine import intervention_engine


@login_required
def interventions_dashboard(request):
    """User dashboard for viewing recommended and past interventions."""
    user = request.user
    
    # Get pending interventions
    pending = UserIntervention.objects.filter(
        user=user,
        delivered_at__isnull=True,
        dismissed_at__isnull=True
    ).select_related('rule', 'content').order_by('-triggered_at')
    
    # Get recent completed interventions
    recent = UserIntervention.objects.filter(
        user=user,
        completed=True
    ).select_related('rule', 'content').order_by('-completed_at')[:10]
    
    # Get engagement stats
    stats = intervention_engine.get_intervention_status(user)
    
    context = {
        'pending': pending,
        'recent': recent,
        'stats': stats,
    }
    
    return render(request, 'companion/interventions_dashboard.html', context)


@login_required
def intervention_detail(request, intervention_id):
    """View details of a specific intervention and its content."""
    intervention = get_object_or_404(UserIntervention, id=intervention_id, user=request.user)
    
    # Mark as viewed
    if not intervention.viewed:
        intervention.viewed = True
        intervention.save()
    
    context = {
        'intervention': intervention,
        'content': intervention.content,
    }
    
    return render(request, 'companion/intervention_detail.html', context)


@login_required
@require_http_methods(["POST"])
def start_intervention(request, intervention_id):
    """Mark intervention as started."""
    try:
        intervention = get_object_or_404(UserIntervention, id=intervention_id, user=request.user)
        intervention.started = True
        intervention.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_http_methods(["POST"])
def complete_intervention(request, intervention_id):
    """Mark intervention as completed and record feedback."""
    try:
        intervention = get_object_or_404(UserIntervention, id=intervention_id, user=request.user)
        rating = request.POST.get('rating')
        was_helpful = request.POST.get('was_helpful') == 'true'
        feedback = request.POST.get('feedback', '')
        
        intervention_engine.complete_intervention(
            intervention,
            rating=int(rating) if rating else None,
            was_helpful=was_helpful
        )
        intervention.feedback_text = feedback
        intervention.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_http_methods(["POST"])
def dismiss_intervention(request, intervention_id):
    """Dismiss an intervention."""
    try:
        intervention = get_object_or_404(UserIntervention, id=intervention_id, user=request.user)
        intervention.dismissed_at = timezone.now()
        intervention.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def trigger_interventions(request):
    """Manually trigger intervention evaluation for the current user."""
    try:
        user = request.user
        triggered = intervention_engine.evaluate_user(user)
        
        return JsonResponse({
            'status': 'success',
            'triggered_count': len(triggered),
            'interventions': [
                {
                    'id': i.id,
                    'rule': i.rule.name,
                    'type': i.rule.intervention_type,
                    'content': i.content.title if i.content else None,
                }
                for i in triggered
            ]
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# --- Admin views for managing intervention rules and content ---

@login_required
def intervention_rules_admin(request):
    """Admin list of intervention rules."""
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    
    rules = InterventionRule.objects.all().order_by('-priority')
    return render(request, 'companion/intervention_rules_list.html', {'rules': rules})


@login_required
def intervention_rule_detail(request, rule_id):
    """Admin view rule details and associated content."""
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    
    rule = get_object_or_404(InterventionRule, id=rule_id)
    content = rule.content.all()
    
    context = {
        'rule': rule,
        'content': content,
    }
    
    return render(request, 'companion/intervention_rule_detail.html', context)


@login_required
def intervention_content_admin(request):
    """Admin list of intervention content."""
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    
    content = InterventionContent.objects.select_related('rule').order_by('rule', '-completion_rate')
    return render(request, 'companion/intervention_content_list.html', {'content': content})


@login_required
def intervention_templates(request):
    """View and deploy intervention templates."""
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    
    templates = InterventionTemplate.objects.filter(is_public=True)
    return render(request, 'companion/intervention_templates.html', {'templates': templates})


@login_required
@require_http_methods(["POST"])
def deploy_template(request, template_id):
    """Deploy an intervention template (create rules and content from it)."""
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    
    try:
        template = get_object_or_404(InterventionTemplate, id=template_id)
        
        # Create rules and content from template
        rule_config = template.default_rule_config
        rule = InterventionRule.objects.create(
            name=template.name,
            description=template.description,
            trigger_type=rule_config.get('trigger_type', 'emotion'),
            trigger_condition=rule_config.get('trigger_condition', {}),
            intervention_type=rule_config.get('intervention_type', 'breathing'),
            max_daily=rule_config.get('max_daily', 3),
            cooldown_minutes=rule_config.get('cooldown_minutes', 60),
            time_windows=rule_config.get('time_windows', []),
            is_active=True
        )
        
        # Create content
        for content_config in template.default_content_list:
            InterventionContent.objects.create(
                rule=rule,
                title=content_config.get('title', ''),
                description=content_config.get('description', ''),
                instructions=content_config.get('instructions', ''),
                audio_url=content_config.get('audio_url', ''),
                video_url=content_config.get('video_url', ''),
                duration_seconds=content_config.get('duration_seconds', 300),
                difficulty=content_config.get('difficulty', 'easy'),
                is_active=True
            )
        
        return JsonResponse({
            'status': 'success',
            'rule_id': rule.id,
            'message': f'Deployed template "{template.name}"'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
