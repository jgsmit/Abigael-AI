"""
Biofeedback views for wearable device integration, data visualization, and alert management.

Views:
- Device Management: Connect/disconnect wearables, sync settings
- Data Display: Heart rate trends, sleep patterns, activity summaries
- Alert Dashboard: View and acknowledge alerts
- Configuration: Set thresholds and preferences
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Avg, Max, Min
from django.utils import timezone
from datetime import timedelta, datetime
import json

from .models import (
    BiofeedbackDevice,
    HeartRateRecord,
    SleepRecord,
    ActivityRecord,
    StressRecord,
    DailyBiofeedbackSummary,
    BiofeedbackAlert,
    BiofeedbackIntegrationConfig,
    BiofeedbackEmotionCorrelation,
)
from .forms import BiofeedbackDeviceForm


@login_required
def biofeedback_dashboard(request):
    """User-facing biofeedback dashboard showing connected devices and data."""
    devices = BiofeedbackDevice.objects.filter(user=request.user, disconnected_at__isnull=True)
    
    # Get latest daily summary
    latest_summary = DailyBiofeedbackSummary.objects.filter(
        user=request.user
    ).order_by('-date').first()
    
    # Get pending alerts
    pending_alerts = BiofeedbackAlert.objects.filter(
        user=request.user,
        acknowledged_at__isnull=True
    ).order_by('-triggered_at')[:5]
    
    # Get last 7 days of summaries
    seven_days_ago = timezone.now().date() - timedelta(days=7)
    weekly_data = DailyBiofeedbackSummary.objects.filter(
        user=request.user,
        date__gte=seven_days_ago
    ).order_by('date')
    
    # Get config or create default
    config, _ = BiofeedbackIntegrationConfig.objects.get_or_create(user=request.user)
    
    context = {
        'devices': devices,
        'latest_summary': latest_summary,
        'pending_alerts': pending_alerts,
        'weekly_data': list(weekly_data.values('date', 'avg_heart_rate', 'sleep_duration_hours', 'stress_level')),
        'config': config,
        'alert_count': pending_alerts.count(),
    }
    return render(request, 'biofeedback/dashboard.html', context)


@login_required
def device_list(request):
    """List all connected and disconnected devices."""
    connected = BiofeedbackDevice.objects.filter(user=request.user, disconnected_at__isnull=True)
    disconnected = BiofeedbackDevice.objects.filter(user=request.user, disconnected_at__isnull=False)
    
    context = {
        'connected_devices': connected,
        'disconnected_devices': disconnected,
    }
    return render(request, 'biofeedback/device_list.html', context)


@login_required
def connect_device(request):
    """Connect a new biofeedback device."""
    if request.method == 'POST':
        form = BiofeedbackDeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.user = request.user
            device.save()
            return redirect('device_detail', device_id=device.id)
    else:
        form = BiofeedbackDeviceForm()
    
    return render(request, 'biofeedback/connect_device.html', {'form': form})


@login_required
def device_detail(request, device_id):
    """Display device details and sync status."""
    device = get_object_or_404(BiofeedbackDevice, id=device_id, user=request.user)
    
    # Get recent data from this device
    heart_rate_data = HeartRateRecord.objects.filter(
        user=request.user,
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).order_by('-timestamp')[:50]
    
    sleep_data = SleepRecord.objects.filter(
        user=request.user,
        sleep_end__gte=timezone.now() - timedelta(days=7)
    ).order_by('-sleep_end')[:10]
    
    context = {
        'device': device,
        'heart_rate_data': heart_rate_data,
        'sleep_data': sleep_data,
        'is_connected': device.disconnected_at is None,
    }
    return render(request, 'biofeedback/device_detail.html', context)


@login_required
@require_http_methods(["POST"])
def disconnect_device(request, device_id):
    """Disconnect a biofeedback device."""
    device = get_object_or_404(BiofeedbackDevice, id=device_id, user=request.user)
    device.disconnected_at = timezone.now()
    device.save()
    return redirect('device_list')


@login_required
@require_http_methods(["GET"])
def heart_rate_timeline(request):
    """API endpoint for heart rate data timeline."""
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)
    
    data = HeartRateRecord.objects.filter(
        user=request.user,
        timestamp__gte=start_date
    ).order_by('timestamp').values(
        'timestamp', 'heart_rate', 'heart_rate_variability', 'activity_context'
    )
    
    return JsonResponse({
        'data': list(data),
        'days': days,
    })


@login_required
@require_http_methods(["GET"])
def sleep_timeline(request):
    """API endpoint for sleep data timeline."""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    data = SleepRecord.objects.filter(
        user=request.user,
        sleep_end__date__gte=start_date
    ).order_by('-sleep_end').values(
        'sleep_start', 'sleep_end', 'duration_hours', 'sleep_quality',
        'time_in_deep_sleep', 'time_in_light_sleep', 'time_in_rem_sleep'
    )
    
    return JsonResponse({
        'data': list(data),
        'days': days,
    })


@login_required
def daily_summary_view(request, date_str=None):
    """Display daily biofeedback summary for a specific date."""
    if date_str:
        try:
            summary_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            summary_date = timezone.now().date()
    else:
        summary_date = timezone.now().date()
    
    summary = DailyBiofeedbackSummary.objects.filter(
        user=request.user,
        date=summary_date
    ).first()
    
    # Get hourly heart rate for this day
    hourly_hr = HeartRateRecord.objects.filter(
        user=request.user,
        timestamp__date=summary_date
    ).order_by('timestamp').values_list('timestamp', 'heart_rate')
    
    context = {
        'summary': summary,
        'date': summary_date,
        'hourly_hr': list(hourly_hr),
    }
    return render(request, 'biofeedback/daily_summary.html', context)


@login_required
def alert_dashboard(request):
    """Display all biofeedback alerts."""
    acknowledged = request.GET.get('acknowledged', 'false').lower() == 'true'
    
    if acknowledged:
        alerts = BiofeedbackAlert.objects.filter(
            user=request.user,
            acknowledged_at__isnull=False
        ).order_by('-acknowledged_at')
        page_title = "Acknowledged Alerts"
    else:
        alerts = BiofeedbackAlert.objects.filter(
            user=request.user,
            acknowledged_at__isnull=True
        ).order_by('-triggered_at')
        page_title = "Active Alerts"
    
    # Group by alert type
    alert_counts = BiofeedbackAlert.objects.filter(user=request.user).values('alert_type').count()
    
    context = {
        'alerts': alerts,
        'page_title': page_title,
        'acknowledged': acknowledged,
    }
    return render(request, 'biofeedback/alert_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def acknowledge_alert(request, alert_id):
    """Acknowledge a biofeedback alert."""
    alert = get_object_or_404(BiofeedbackAlert, id=alert_id, user=request.user)
    alert.acknowledged_at = timezone.now()
    
    # Store action if provided
    if request.POST.get('action'):
        alert.action_taken = request.POST.get('action')
    
    alert.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'acknowledged'})
    
    return redirect('alert_dashboard')


@login_required
def biofeedback_settings(request):
    """Biofeedback configuration page."""
    config, created = BiofeedbackIntegrationConfig.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update thresholds and preferences
        config.high_stress_threshold = float(request.POST.get('high_stress_threshold', 75.0))
        config.high_heart_rate_threshold = int(request.POST.get('high_heart_rate_threshold', 100))
        config.low_sleep_threshold = float(request.POST.get('low_sleep_threshold', 6.0))
        
        config.enable_alerts = request.POST.get('enable_alerts') == 'on'
        config.enable_sleep_tracking = request.POST.get('enable_sleep_tracking') == 'on'
        config.enable_stress_tracking = request.POST.get('enable_stress_tracking') == 'on'
        config.auto_trigger_interventions = request.POST.get('auto_trigger_interventions') == 'on'
        config.share_with_therapist = request.POST.get('share_with_therapist') == 'on'
        
        config.save()
        return redirect('biofeedback_dashboard')
    
    context = {
        'config': config,
    }
    return render(request, 'biofeedback/settings.html', context)


@login_required
@require_http_methods(["GET"])
def biofeedback_statistics(request):
    """API endpoint for biofeedback statistics and trends."""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Get daily summaries
    summaries = DailyBiofeedbackSummary.objects.filter(
        user=request.user,
        date__gte=start_date
    ).order_by('date')
    
    # Calculate statistics
    stats = {
        'avg_heart_rate': summaries.aggregate(Avg('avg_heart_rate'))['avg_heart_rate__avg'],
        'avg_sleep': summaries.aggregate(Avg('sleep_duration_hours'))['sleep_duration_hours__avg'],
        'avg_stress': summaries.aggregate(Avg('stress_level'))['stress_level__avg'],
        'total_steps': summaries.aggregate(models.Sum('steps'))['steps__sum'] or 0,
    }
    
    return JsonResponse({
        'stats': stats,
        'days': days,
        'last_updated': summaries.last().date if summaries.exists() else None,
    })


@login_required
@require_http_methods(["GET"])
def emotion_correlation(request):
    """API endpoint for emotion-biofeedback correlations."""
    correlations = BiofeedbackEmotionCorrelation.objects.filter(
        user=request.user
    ).order_by('-correlation_strength')
    
    data = correlations.values(
        'emotion',
        'avg_heart_rate',
        'avg_hrv',
        'avg_stress_level',
        'correlation_strength'
    )
    
    return JsonResponse({
        'correlations': list(data),
    })


# ============================================================================
# INTERNAL VIEWS (called by other systems, not directly by users)
# ============================================================================

def create_daily_summary(user, date=None):
    """
    Create or update daily biofeedback summary for a user.
    Called from a Celery task or management command.
    """
    if date is None:
        date = timezone.now().date()
    
    # Get all data for the day
    day_start = datetime.combine(date, datetime.min.time())
    day_end = datetime.combine(date, datetime.max.time())
    
    # Heart rate statistics
    hr_records = HeartRateRecord.objects.filter(
        user=user,
        timestamp__date=date
    )
    
    # Sleep data (sleep_end on this date)
    sleep_records = SleepRecord.objects.filter(
        user=user,
        sleep_end__date=date
    )
    
    # Activity data
    activity_records = ActivityRecord.objects.filter(
        user=user,
        date=date
    )
    
    # Stress data
    stress_records = StressRecord.objects.filter(
        user=user,
        timestamp__date=date
    )
    
    # Calculate aggregates
    summary, created = DailyBiofeedbackSummary.objects.get_or_create(
        user=user,
        date=date
    )
    
    if hr_records.exists():
        summary.avg_heart_rate = hr_records.aggregate(Avg('heart_rate'))['heart_rate__avg']
        summary.min_heart_rate = hr_records.aggregate(Min('heart_rate'))['heart_rate__min']
        summary.max_heart_rate = hr_records.aggregate(Max('heart_rate'))['heart_rate__max']
        summary.heart_rate_variability = hr_records.aggregate(Avg('heart_rate_variability'))['heart_rate_variability__avg']
    
    if sleep_records.exists():
        sleep_sum = sleep_records.aggregate(models.Sum('duration_hours'))['duration_hours__sum']
        summary.sleep_duration_hours = sleep_sum / len(sleep_records) if len(sleep_records) > 0 else 0
        summary.sleep_quality = sleep_records.aggregate(Avg('sleep_quality'))['sleep_quality__avg']
        summary.time_in_deep_sleep = sleep_records.aggregate(models.Sum('time_in_deep_sleep'))['time_in_deep_sleep__sum']
        summary.time_in_rem_sleep = sleep_records.aggregate(models.Sum('time_in_rem_sleep'))['time_in_rem_sleep__sum']
    
    if activity_records.exists():
        summary.steps = activity_records.aggregate(models.Sum('steps'))['steps__sum']
        summary.calories_burned = activity_records.aggregate(models.Sum('calories_burned'))['calories_burned__sum']
        summary.active_minutes = activity_records.aggregate(models.Sum('active_minutes_zone1', 'active_minutes_zone2',
                                                                       models.F('active_minutes_zone1') + 
                                                                       models.F('active_minutes_zone2')))['active_minutes_zone1__sum'] or 0
    
    if stress_records.exists():
        summary.stress_level = stress_records.aggregate(Avg('stress_level'))['stress_level__avg']
    
    summary.save()
    return summary


def check_biofeedback_alerts(user):
    """
    Check recent biofeedback data and create alerts if thresholds exceeded.
    Called from Celery task or intervention engine.
    """
    config, _ = BiofeedbackIntegrationConfig.objects.get_or_create(user=user)
    if not config.enable_alerts:
        return []
    
    alerts = []
    
    # Get latest daily summary
    latest = DailyBiofeedbackSummary.objects.filter(user=user).order_by('-date').first()
    if not latest:
        return alerts
    
    # Check stress threshold
    if config.enable_stress_tracking and latest.stress_level and latest.stress_level > config.high_stress_threshold:
        alert, created = BiofeedbackAlert.objects.get_or_create(
            user=user,
            alert_type='high_stress',
            triggered_at__date=timezone.now().date(),
            defaults={
                'description': f'Stress level at {latest.stress_level:.1f} (threshold: {config.high_stress_threshold})',
                'severity': 'high' if latest.stress_level > 85 else 'medium',
            }
        )
        if created:
            alerts.append(alert)
    
    # Check sleep threshold
    if latest.sleep_duration_hours and latest.sleep_duration_hours < config.low_sleep_threshold:
        alert, created = BiofeedbackAlert.objects.get_or_create(
            user=user,
            alert_type='low_sleep',
            triggered_at__date=timezone.now().date(),
            defaults={
                'description': f'Sleep duration {latest.sleep_duration_hours:.1f}h (below target: {config.low_sleep_threshold}h)',
                'severity': 'high' if latest.sleep_duration_hours < 5 else 'medium',
            }
        )
        if created:
            alerts.append(alert)
    
    # Check heart rate threshold
    latest_hr = HeartRateRecord.objects.filter(user=user).order_by('-timestamp').first()
    if latest_hr and latest_hr.heart_rate > config.high_heart_rate_threshold:
        alert, created = BiofeedbackAlert.objects.get_or_create(
            user=user,
            alert_type='high_hr',
            triggered_at__date=timezone.now().date(),
            defaults={
                'description': f'Elevated heart rate: {latest_hr.heart_rate} BPM',
                'severity': 'high' if latest_hr.heart_rate > 120 else 'medium',
            }
        )
        if created:
            alerts.append(alert)
    
    return alerts
