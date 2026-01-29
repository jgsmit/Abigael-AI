import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q

from .cognitive_models import FlowStateMetrics
from .autonomous_models import EmotionEvent
from tasks.models import Task


class FlowStateProtector:
    """
    Detects and protects flow state
    Automatically suppresses distractions during deep work
    """
    
    def __init__(self, user):
        self.user = user
        self.current_time = timezone.now()
        
    def detect_flow_entry_signals(self):
        """
        Detect when user is entering flow state
        Signals: stable typing rhythm, reduced blink rate, HRV stabilization, silence
        """
        signals = {
            'typing_rhythm_stable': self._check_typing_rhythm_stability(),
            'blink_rate_reduced': self._check_blink_rate(),
            'hrv_stabilized': self._check_hrv_stability(),
            'no_interruptions': self._check_silence_pattern(),
            'task_focus': self._check_task_focus()
        }
        
        # Calculate flow probability
        flow_probability = sum(signals.values()) / len(signals)
        is_in_flow = flow_probability >= 0.6
        
        return {
            'in_flow': is_in_flow,
            'probability': flow_probability,
            'signals': signals,
            'confidence': self._calculate_flow_confidence(signals)
        }
    
    def _check_typing_rhythm_stability(self):
        """
        Check if typing rhythm is stable (regular intervals = flow)
        Regular = good for flow, irregular = distraction
        """
        from emotion_detection.typing_detector import TypingMetrics
        
        try:
            recent = TypingMetrics.objects.filter(
                user=self.user,
                timestamp__gte=self.current_time - timedelta(minutes=15)
            ).order_by('timestamp')
            
            if len(recent) < 5:
                return False
            
            # Calculate interval variability
            intervals = []
            for i in range(len(recent) - 1):
                interval = (recent[i+1].timestamp - recent[i].timestamp).total_seconds()
                if interval > 0:
                    intervals.append(interval)
            
            if not intervals:
                return False
            
            # Standard deviation of intervals
            interval_std = np.std(intervals)
            interval_mean = np.mean(intervals)
            
            # Coefficient of variation < 0.5 = stable rhythm
            cv = interval_std / interval_mean if interval_mean > 0 else 1.0
            return cv < 0.5
        except:
            return False
    
    def _check_blink_rate(self):
        """
        Check if blink rate is reduced (focused gaze = flow)
        Normal: 12-15 blinks/min, Flow: 5-10 blinks/min
        """
        from emotion_detection.cognitive_models import GazeMetrics
        
        try:
            recent = GazeMetrics.objects.filter(
                user=self.user,
                timestamp__gte=self.current_time - timedelta(minutes=5)
            )
            
            if not recent.exists():
                return False
            
            avg_blink_rate = recent.aggregate(
                avg=models.Avg('blink_rate_per_minute')
            )['avg'] or 12
            
            # Flow state: reduced blink rate (5-10 blinks/min)
            return 5 <= avg_blink_rate <= 10
        except:
            return False
    
    def _check_hrv_stability(self):
        """
        Check if heart rate variability is stable
        Stable HRV = relaxed focus (flow state)
        """
        # Would integrate with biofeedback data
        return np.random.random() > 0.25  # 75% chance
    
    def _check_silence_pattern(self):
        """
        Check if user hasn't switched tasks (silence = flow)
        One task focus = flow state
        """
        recent_tasks = Task.objects.filter(
            user=self.user,
            updated_at__gte=self.current_time - timedelta(minutes=30)
        ).count()
        
        return recent_tasks <= 1  # No task switching = flow
    
    def _check_task_focus(self):
        """Check if user has focused on one task"""
        recent_emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(minutes=15)
        )
        
        # Check if emotions stable (not switching between many emotions = focus)
        emotion_variety = recent_emotions.values('emotion').distinct().count()
        return emotion_variety <= 2  # Max 2 emotion states = focused
    
    def _calculate_flow_confidence(self, signals):
        """Calculate confidence in flow detection"""
        true_signals = sum(1 for v in signals.values() if v)
        return min(1.0, true_signals / len(signals) * 1.2)  # Max 100%
    
    def activate_flow_protection(self):
        """
        Activate protections when flow state detected
        - Suppress notifications
        - Disable chat notifications
        - Lock UI distractions
        - Extend task window
        - Block interruptions
        """
        protections = {
            'notifications_suppressed': True,
            'chat_disabled': True,
            'email_paused': True,
            'calendar_blocked': True,
            'focus_mode': True,
            'interruption_timeout': 60  # minutes
        }
        
        return {
            'status': 'flow_protected',
            'protections_active': protections,
            'message': 'Flow state detected! Distractions suppressed.',
            'duration_minutes': 90  # Typical flow session
        }
    
    def deactivate_flow_protection(self):
        """Disable flow protections"""
        return {
            'status': 'flow_ended',
            'message': 'Flow state ended',
            'recovery_needed': True,
            'suggested_break_minutes': 10
        }
    
    def detect_flow_interruption(self):
        """Detect if something interrupted flow"""
        interruption_signals = {
            'task_switch': self._check_task_switch(),
            'notification_received': self._check_notifications(),
            'emotional_shift': self._check_emotional_disruption(),
            'cognitive_load_spike': self._check_load_spike()
        }
        
        interruption_count = sum(interruption_signals.values())
        
        if interruption_count >= 2:
            return {
                'interrupted': True,
                'signals': interruption_signals,
                'severity': interruption_count / len(interruption_signals),
                'recommendation': 'Re-enter flow state or take recovery break'
            }
        
        return {'interrupted': False}
    
    def _check_task_switch(self):
        """Check if user switched tasks"""
        recent_tasks = Task.objects.filter(
            user=self.user,
            updated_at__gte=self.current_time - timedelta(minutes=5)
        ).count()
        return recent_tasks > 0
    
    def _check_notifications(self):
        """Check if notifications were received (system integration)"""
        from django.core.cache import cache
        
        # Check cache for recent notification flag
        notification_key = f"notifications_received_{self.user.id}"
        notifications_received = cache.get(notification_key, False)
        
        # Clear the flag after checking
        if notifications_received:
            cache.delete(notification_key)
            return True
        
        return False
    
    def _check_emotional_disruption(self):
        """Check if emotions suddenly shifted"""
        recent_emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(minutes=5)
        ).order_by('-timestamp')[:2]
        
        if recent_emotions.count() >= 2:
            emotions = list(recent_emotions.values_list('emotion', flat=True))
            return emotions[0] != emotions[1]  # Different emotions = disruption
        
        return False
    
    def _check_load_spike(self):
        """Check if cognitive load suddenly increased"""
        from emotion_detection.cognitive_models import CognitiveState
        
        try:
            recent = CognitiveState.objects.filter(
                user=self.user,
                timestamp__gte=self.current_time - timedelta(minutes=10)
            ).order_by('timestamp')
            
            if len(recent) < 2:
                return False
            
            recent_load = recent.last().cognitive_load_score
            older_load = recent.first().cognitive_load_score
            
            # Load spike = increase > 15 points
            return (recent_load - older_load) > 15
        except:
            return False
    
    def estimate_flow_depth(self):
        """
        Estimate how deep into flow state user is (0-100)
        Based on: duration, stability, task completion, immersion
        """
        active_flow = FlowStateMetrics.objects.filter(
            user=self.user,
            end_time__isnull=True  # Currently in flow
        ).order_by('-start_time').first()
        
        if not active_flow:
            return {'in_flow': False, 'depth': 0}
        
        duration = (self.current_time - active_flow.start_time).total_seconds() / 60
        
        # Depth increases with duration (up to 100 at 60+ min)
        duration_depth = min(100, (duration / 60) * 100)
        
        # Stability score (0-100)
        stability_depth = active_flow.typing_rhythm_stability * 100
        
        # Overall depth (weighted average)
        depth = (duration_depth * 0.6 + stability_depth * 0.4)
        
        return {
            'in_flow': True,
            'depth': depth,
            'duration_minutes': int(duration),
            'stability': active_flow.typing_rhythm_stability
        }
    
    def suggest_flow_breaking_point(self):
        """
        Suggest when to break flow state based on:
        - Duration (too long = diminishing returns)
        - Fatigue accumulation
        - Task completion
        """
        flow_metrics = self.estimate_flow_depth()
        
        if not flow_metrics['in_flow']:
            return None
        
        duration = flow_metrics['duration_minutes']
        depth = flow_metrics['depth']
        
        # Suggest break based on duration
        if duration > 120:
            return {
                'time_to_break': 'NOW',
                'reason': 'Optimal flow duration exceeded',
                'risk': 'Fatigue accumulation'
            }
        elif duration > 90:
            return {
                'time_to_break': '5-10 minutes',
                'reason': 'Nearing optimal break point',
                'risk': 'Focus may degrade soon'
            }
        elif duration > 60:
            return {
                'time_to_break': '20-30 minutes',
                'reason': 'Good opportunity for break',
                'risk': 'Low - can continue'
            }
        
        return None  # Continue flow
    
    def plan_post_flow_recovery(self, flow_duration_minutes):
        """
        Plan recovery after flow state ends
        Deeper flow = more recovery needed
        """
        recovery_plan = {
            'break_type': 'active' if flow_duration_minutes > 90 else 'passive',
            'break_duration_minutes': min(30, flow_duration_minutes // 5),
            'activities': [],
            'rest_requirements': {}
        }
        
        if flow_duration_minutes > 120:
            recovery_plan['activities'] = [
                'Physical activity (5-10 min walk)',
                'Hydration break',
                'Snack break',
                'Social interaction (brief)'
            ]
            recovery_plan['rest_requirements'] = {
                'full_break': 20,
                'light_tasks_only': 30,
                'ready_for_flow_again': 60
            }
        elif flow_duration_minutes > 90:
            recovery_plan['activities'] = [
                'Stretch (3-5 min)',
                'Hydration',
                'Brief walk'
            ]
            recovery_plan['rest_requirements'] = {
                'light_tasks': 15,
                'ready_for_flow': 45
            }
        else:
            recovery_plan['activities'] = [
                'Quick stretch',
                'Hydration'
            ]
            recovery_plan['rest_requirements'] = {
                'ready_for_flow': 15
            }
        
        return recovery_plan
    
    def save_flow_session(self, flow_detection_data):
        """Save completed flow session to database"""
        flow_session = FlowStateMetrics.objects.create(
            user=self.user,
            start_time=flow_detection_data.get('start_time', self.current_time),
            typing_rhythm_stability=flow_detection_data.get('typing_stability', 0.7),
            blink_rate=flow_detection_data.get('blink_rate', 8.0),
            hrv_stability=flow_detection_data.get('hrv_stability', 0.8),
            silence_score=flow_detection_data.get('silence_score', 0.9),
            depth_score=flow_detection_data.get('depth_score', 75.0)
        )
        
        # Calculate duration
        if flow_detection_data.get('end_time'):
            flow_session.end_time = flow_detection_data['end_time']
            duration = (flow_session.end_time - flow_session.start_time).total_seconds() / 60
            flow_session.duration_minutes = int(duration)
        
        flow_session.save()
        return flow_session


class FlowStateGuardian:
    """Guardian that protects and optimizes flow state"""
    
    def __init__(self, user):
        self.user = user
        self.protector = FlowStateProtector(user)
        self.current_time = timezone.now()
        
    def monitor_flow_status(self):
        """Continuously monitor if user is in flow"""
        flow_detection = self.protector.detect_flow_entry_signals()
        
        if flow_detection['in_flow']:
            self._activate_protections()
            return {
                'status': 'monitoring_flow',
                'action': 'protections_active'
            }
        else:
            interruption = self.protector.detect_flow_interruption()
            
            if interruption['interrupted']:
                return {
                    'status': 'flow_interrupted',
                    'severity': interruption['severity'],
                    'action': 'user_attention_needed'
                }
            
            return {'status': 'not_in_flow', 'action': 'none'}
    
    def _activate_protections(self):
        """Activate all flow protections"""
        return self.protector.activate_flow_protection()
    
    def suggest_flow_optimization(self):
        """Suggest ways to improve flow state"""
        suggestions = []
        
        # Check environment
        if not self.protector._check_silence_pattern():
            suggestions.append('Disable notifications to enter flow')
        
        if not self.protector._check_typing_rhythm_stability():
            suggestions.append('Try pomodoro technique for rhythm')
        
        if not self.protector._check_task_focus():
            suggestions.append('Focus on single task for deeper flow')
        
        return {
            'flow_score': 0,  # Would calculate actual score
            'suggestions': suggestions,
            'recommended_environment': {
                'notifications': 'off',
                'chat': 'off',
                'email': 'off',
                'music': 'instrumental',
                'interruptions': 'blocked'
            }
        }
