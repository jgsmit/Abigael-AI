"""
Biofeedback Integration Engine

Responsible for:
1. Monitoring incoming biofeedback data from wearables
2. Detecting anomalies and patterns in physiological data
3. Feeding biofeedback state into the intervention engine
4. Triggering physiologically-informed micro-interventions

Integration with InterventionEngine:
- BiofeedbackIntegrationEngine provides user state (stress_level, sleep_quality, etc.)
- InterventionEngine uses this state to trigger context-aware interventions
- Bidirectional: Interventions targeting biofeedback improvements (e.g., sleep, stress) update feedback
"""

from django.utils import timezone
from django.db.models import Avg, Q
from datetime import timedelta
from statistics import mean, stdev
import logging

from .models import (
    User,
    HeartRateRecord,
    SleepRecord,
    ActivityRecord,
    StressRecord,
    DailyBiofeedbackSummary,
    BiofeedbackAlert,
    BiofeedbackIntegrationConfig,
    BiofeedbackEmotionCorrelation,
    BiofeedbackDevice,
)

logger = logging.getLogger(__name__)


class BiofeedbackIntegrationEngine:
    """
    Autonomous engine for biofeedback data processing and anomaly detection.
    """
    
    def __init__(self, user):
        """
        Initialize engine for a specific user.
        
        Args:
            user: Django User instance
        """
        self.user = user
        self.config, _ = BiofeedbackIntegrationConfig.objects.get_or_create(user=user)
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def gather_user_state(self) -> dict:
        """
        Gather current biofeedback user state for intervention engine.
        
        Returns:
            {
                'stress_level': float (0-100),
                'sleep_quality': float (0-100),
                'heart_rate': int,
                'activity_level': str (sedentary|light|moderate|vigorous),
                'heart_rate_trend': str (improving|declining|stable),
                'alerts': [BiofeedbackAlert],
                'anomalies': [str],
            }
        """
        state = {}
        
        # Current stress
        latest_stress = StressRecord.objects.filter(user=self.user).order_by('-timestamp').first()
        state['stress_level'] = latest_stress.stress_level if latest_stress else 50.0
        
        # Latest heart rate
        latest_hr = HeartRateRecord.objects.filter(user=self.user).order_by('-timestamp').first()
        state['heart_rate'] = latest_hr.heart_rate if latest_hr else None
        state['hrv'] = latest_hr.heart_rate_variability if latest_hr else None
        
        # Recent sleep quality
        today = timezone.now().date()
        yesterday_sleep = SleepRecord.objects.filter(
            user=self.user,
            sleep_end__date=today
        ).order_by('-sleep_end').first()
        
        if yesterday_sleep:
            state['sleep_quality'] = yesterday_sleep.sleep_quality
            state['sleep_hours'] = yesterday_sleep.duration_hours
        else:
            state['sleep_quality'] = 50.0
            state['sleep_hours'] = 0.0
        
        # Activity level
        latest_activity = ActivityRecord.objects.filter(user=self.user).order_by('-date').first()
        if latest_activity:
            state['activity_level'] = self._classify_activity(latest_activity.active_minutes_zone1 or 0)
        else:
            state['activity_level'] = 'sedentary'
        
        # Heart rate trend
        state['heart_rate_trend'] = self._calculate_hr_trend()
        
        # Pending alerts
        state['alerts'] = list(BiofeedbackAlert.objects.filter(
            user=self.user,
            acknowledged_at__isnull=True
        ).order_by('-triggered_at')[:3])
        
        # Detected anomalies
        state['anomalies'] = self.detect_anomalies()
        
        return state
    
    def detect_anomalies(self) -> list:
        """
        Detect anomalies in recent biofeedback data.
        
        Returns:
            List of anomaly descriptions
        """
        anomalies = []
        
        # Check for unusual heart rate patterns
        hr_anomaly = self._detect_hr_anomaly()
        if hr_anomaly:
            anomalies.append(hr_anomaly)
        
        # Check for unusual stress patterns
        stress_anomaly = self._detect_stress_anomaly()
        if stress_anomaly:
            anomalies.append(stress_anomaly)
        
        # Check for sleep deprivation
        sleep_anomaly = self._detect_sleep_anomaly()
        if sleep_anomaly:
            anomalies.append(sleep_anomaly)
        
        # Check for activity changes
        activity_anomaly = self._detect_activity_anomaly()
        if activity_anomaly:
            anomalies.append(activity_anomaly)
        
        return anomalies
    
    def generate_insights(self) -> dict:
        """
        Generate insights from biofeedback patterns.
        
        Returns:
            {
                'insights': [str],
                'correlations': dict (emotion -> avg_hr, etc.),
                'trends': dict,
            }
        """
        insights = {
            'insights': [],
            'correlations': {},
            'trends': {},
        }
        
        # Get emotion correlations
        correlations = BiofeedbackEmotionCorrelation.objects.filter(user=self.user)
        for corr in correlations:
            insights['correlations'][corr.emotion] = {
                'avg_hr': corr.avg_heart_rate,
                'avg_hrv': corr.avg_hrv,
                'avg_stress': corr.avg_stress_level,
                'strength': corr.correlation_strength,
            }
        
        # Daily summary trends (last 7 days)
        seven_days = timezone.now().date() - timedelta(days=7)
        weekly = DailyBiofeedbackSummary.objects.filter(
            user=self.user,
            date__gte=seven_days
        ).order_by('date')
        
        if weekly.exists():
            hr_values = [s.avg_heart_rate for s in weekly if s.avg_heart_rate]
            if len(hr_values) > 1:
                insights['trends']['hr_trend'] = 'improving' if hr_values[-1] < hr_values[0] else 'rising'
            
            sleep_values = [s.sleep_duration_hours for s in weekly if s.sleep_duration_hours]
            if len(sleep_values) > 1:
                insights['trends']['sleep_trend'] = 'improving' if sleep_values[-1] > sleep_values[0] else 'declining'
            
            stress_values = [s.stress_level for s in weekly if s.stress_level]
            if len(stress_values) > 1:
                insights['trends']['stress_trend'] = 'improving' if stress_values[-1] < stress_values[0] else 'worsening'
        
        # Generate narrative insights
        insights['insights'] = self._generate_narrative_insights(weekly)
        
        return insights
    
    def sync_device(self, device):
        """
        Sync data from a specific biofeedback device.
        In production, this would call the actual API.
        
        Args:
            device: BiofeedbackDevice instance
            
        Returns:
            {'success': bool, 'records_synced': int, 'errors': [str]}
        """
        result = {'success': False, 'records_synced': 0, 'errors': []}
        
        # Check if device needs sync
        if device.last_synced_at and (timezone.now() - device.last_synced_at).seconds < 300:
            result['success'] = True
            result['message'] = 'Device already synced recently'
            return result
        
        try:
            if device.device_type == 'fitbit':
                records = self._sync_fitbit(device)
            elif device.device_type == 'apple_watch':
                records = self._sync_apple_watch(device)
            elif device.device_type == 'garmin':
                records = self._sync_garmin(device)
            elif device.device_type == 'oura_ring':
                records = self._sync_oura(device)
            elif device.device_type == 'whoop':
                records = self._sync_whoop(device)
            elif device.device_type == 'polar':
                records = self._sync_polar(device)
            else:
                result['errors'].append(f'Unsupported device type: {device.device_type}')
                return result
            
            result['success'] = True
            result['records_synced'] = len(records)
            device.last_synced_at = timezone.now()
            device.save()
            
        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Failed to sync {device.device_type}: {e}")
        
        return result
    
    def record_device_event(self, device, event_type, data=None):
        """
        Record a device-related event (e.g., sync failure, authentication error).
        
        Args:
            device: BiofeedbackDevice instance
            event_type: str (sync_failed, auth_expired, data_gap, etc.)
            data: optional dict with event details
        """
        logger.info(f"Device event: {device.device_type} {event_type}", extra={
            'user': self.user.id,
            'device_id': device.id,
            'event': event_type,
            'data': data,
        })
        
        # Could create a BiofeedbackDeviceEvent model here
    
    # ========================================================================
    # Private Methods: Anomaly Detection
    # ========================================================================
    
    def _detect_hr_anomaly(self) -> str:
        """Detect unusual heart rate patterns."""
        # Get last 3 days of data
        three_days = timezone.now() - timedelta(days=3)
        records = list(HeartRateRecord.objects.filter(
            user=self.user,
            timestamp__gte=three_days
        ).order_by('timestamp').values_list('heart_rate', flat=True))
        
        if len(records) < 10:
            return None
        
        # Calculate baseline and standard deviation
        baseline = mean(records)
        std = stdev(records) if len(records) > 1 else 0
        
        # Check latest value
        latest = records[-1]
        if latest > baseline + (2 * std) and latest > 100:
            return f"Elevated heart rate: {latest} BPM (baseline: {baseline:.0f})"
        
        return None
    
    def _detect_stress_anomaly(self) -> str:
        """Detect unusual stress patterns."""
        # Get last 3 days of stress data
        three_days = timezone.now() - timedelta(days=3)
        records = list(StressRecord.objects.filter(
            user=self.user,
            timestamp__gte=three_days
        ).order_by('timestamp').values_list('stress_level', flat=True))
        
        if len(records) < 5:
            return None
        
        baseline = mean(records)
        latest = records[-1]
        
        if latest > 80:
            return f"High stress level: {latest:.0f} (recent average: {baseline:.0f})"
        
        return None
    
    def _detect_sleep_anomaly(self) -> str:
        """Detect insufficient sleep."""
        # Check last night's sleep
        today = timezone.now().date()
        yesterday_sleep = SleepRecord.objects.filter(
            user=self.user,
            sleep_end__date=today
        ).order_by('-sleep_end').first()
        
        if yesterday_sleep and yesterday_sleep.duration_hours < self.config.low_sleep_threshold:
            return f"Insufficient sleep: {yesterday_sleep.duration_hours:.1f}h (target: {self.config.low_sleep_threshold:.0f}h)"
        
        return None
    
    def _detect_activity_anomaly(self) -> str:
        """Detect unusual activity changes."""
        # Compare last 2 weeks
        two_weeks = timezone.now().date() - timedelta(days=14)
        recent = ActivityRecord.objects.filter(
            user=self.user,
            date__gte=two_weeks
        ).order_by('-date')
        
        if not recent.exists():
            return None
        
        # Get activity trend
        recent_activity = [r.active_minutes_zone1 or 0 for r in recent[:7]]
        older_activity = [r.active_minutes_zone1 or 0 for r in recent[7:14]]
        
        if len(recent_activity) > 0 and len(older_activity) > 0:
            recent_avg = mean(recent_activity)
            older_avg = mean(older_activity)
            
            if recent_avg < older_avg * 0.5 and older_avg > 0:
                return f"Activity level decreased: {recent_avg:.0f} min/day (was {older_avg:.0f})"
        
        return None
    
    # ========================================================================
    # Private Methods: Trend Analysis
    # ========================================================================
    
    def _calculate_hr_trend(self) -> str:
        """Calculate recent heart rate trend."""
        seven_days = timezone.now() - timedelta(days=7)
        records = list(HeartRateRecord.objects.filter(
            user=self.user,
            timestamp__gte=seven_days
        ).order_by('timestamp').values_list('heart_rate', flat=True))
        
        if len(records) < 10:
            return 'stable'
        
        first_half = mean(records[:len(records)//2])
        second_half = mean(records[len(records)//2:])
        
        if second_half < first_half * 0.95:
            return 'improving'
        elif second_half > first_half * 1.05:
            return 'declining'
        return 'stable'
    
    def _classify_activity(self, active_minutes) -> str:
        """Classify activity level from active minutes."""
        if active_minutes < 10:
            return 'sedentary'
        elif active_minutes < 30:
            return 'light'
        elif active_minutes < 60:
            return 'moderate'
        return 'vigorous'
    
    # ========================================================================
    # Private Methods: Device Sync Stubs
    # ========================================================================
    
    def _sync_fitbit(self, device) -> list:
        """
        Sync data from Fitbit API.
        Placeholder for actual API integration.
        
        In production:
        1. Get oauth_token from device
        2. Call Fitbit API endpoints:
           - /1/user/-/activities/date/{date}.json (daily summary)
           - /1/user/-/activities/heart/date/{date}/1d/1min.json (heart rate)
           - /1/user/-/sleep/date/{date}.json (sleep)
        3. Create HeartRateRecord, SleepRecord, ActivityRecord
        4. Call check_biofeedback_alerts()
        """
        return []
    
    def _sync_apple_watch(self, device) -> list:
        """Sync from Apple Watch via HealthKit."""
        return []
    
    def _sync_garmin(self, device) -> list:
        """Sync from Garmin Connect API."""
        return []
    
    def _sync_oura(self, device) -> list:
        """Sync from Oura Ring API."""
        return []
    
    def _sync_whoop(self, device) -> list:
        """Sync from WHOOP API."""
        return []
    
    def _sync_polar(self, device) -> list:
        """Sync from Polar API."""
        return []
    
    # ========================================================================
    # Private Methods: Insights
    # ========================================================================
    
    def _generate_narrative_insights(self, weekly_summaries) -> list:
        """Generate narrative insights from weekly data."""
        insights = []
        
        if not weekly_summaries:
            return insights
        
        # Sleep quality trend
        sleep_scores = [s.sleep_quality for s in weekly_summaries if s.sleep_quality]
        if sleep_scores:
            avg_sleep = mean(sleep_scores)
            if avg_sleep < 50:
                insights.append("Your sleep quality has been low. Consider setting a consistent bedtime.")
            elif avg_sleep > 75:
                insights.append("Great job maintaining good sleep quality this week!")
        
        # Stress trend
        stress_scores = [s.stress_level for s in weekly_summaries if s.stress_level]
        if stress_scores:
            stress_trend = stress_scores[-1] - stress_scores[0]
            if stress_trend > 10:
                insights.append("Your stress levels are increasing. Take time to relax and recharge.")
            elif stress_trend < -10:
                insights.append("Your stress is decreasing. Keep up the positive work!")
        
        # Activity consistency
        activity = [s.active_minutes for s in weekly_summaries if s.active_minutes]
        if len(activity) >= 5:
            consistency = len([a for a in activity if a > 20]) / len(activity)
            if consistency > 0.7:
                insights.append("You've been consistently active. Great dedication!")
            elif consistency < 0.3:
                insights.append("Try to increase your daily activity. Even short walks help.")
        
        return insights
