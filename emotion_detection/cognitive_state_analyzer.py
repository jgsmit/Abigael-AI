import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q, F
from .cognitive_models import (
    CognitiveState, BurnoutRisk, CognitiveLoadHistory, 
    FlowStateMetrics, AttentionSpanMetrics, MentalFatigueTracker,
    CognitiveUserDNA, DecisionDegradationTracker
)
from .autonomous_models import EmotionEvent
from .biofeedback_models import HeartRateRecord, ActivityRecord
from tasks.models import Task
import json


class CognitiveStateAnalyzer:
    """
    Advanced cognitive state detection and analysis.
    Detects: focused, overloaded, drained, flow, anxious, bored, saturated, recovering
    """
    
    def __init__(self, user):
        self.user = user
        self.current_time = timezone.now()
        
    def calculate_cognitive_load_score(self):
        """
        Calculate overall cognitive load (0-100)
        Formula: weighted(HRV, typing_variance, task_switching, speech_latency, time_on_task)
        """
        # Get recent data points
        recent_emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(minutes=30)
        ).order_by('-timestamp')[:20]
        
        # Calculate typing metrics
        typing_errors = self._calculate_typing_errors()
        task_switches = self._calculate_task_switches()
        
        # Get biofeedback data
        hrv_score = self._get_hrv_stability()
        
        # Weighted calculation
        cognitive_load = (
            (100 - hrv_score) * 0.25 +  # Lower HRV = higher load
            (typing_errors * 2) * 0.25 +  # Error rate
            (task_switches * 10) * 0.25 +  # Switch frequency
            self._calculate_response_latency() * 0.25  # Response delays
        )
        
        return max(0, min(100, cognitive_load))  # Clamp to 0-100
    
    def _calculate_typing_errors(self):
        """Get recent typing error rate (0-100)"""
        from emotion_detection.typing_detector import TypingMetrics
        
        try:
            recent_typing = TypingMetrics.objects.filter(
                user=self.user,
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).order_by('-timestamp')[:100]
            
            if not recent_typing:
                return 0  # No data yet
            
            error_counts = [t.error_count or 0 for t in recent_typing]
            keystroke_counts = [t.total_keystrokes or 1 for t in recent_typing]
            
            total_errors = sum(error_counts)
            total_keystrokes = sum(keystroke_counts)
            
            if total_keystrokes == 0:
                return 0
            
            error_rate = (total_errors / total_keystrokes) * 100
            return min(100, error_rate)
        except:
            return 0  # Fallback if table doesn't exist yet
    
    def _calculate_task_switches(self):
        """Count task switches in last hour"""
        recent_tasks = Task.objects.filter(
            user=self.user,
            updated_at__gte=self.current_time - timedelta(hours=1)
        ).order_by('-updated_at')[:20]
        
        return recent_tasks.count() if recent_tasks.count() > 1 else 0
    
    def _get_hrv_stability(self):
        """Get heart rate variability score (0-100, higher = better)"""
        recent_hrv = HeartRateRecord.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(minutes=30)
        ).values_list('hrv_score', flat=True)
        
        if not recent_hrv:
            return 50.0  # Default baseline
        
        avg_hrv = np.mean(list(recent_hrv))
        return min(100, avg_hrv * 100)  # Scale to 0-100
    
    def _calculate_response_latency(self):
        """Calculate average response time delay (0-100)"""
        # Higher latency = higher load
        recent_reactions = DecisionDegradationTracker.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(minutes=30)
        ).values_list('decision_speed', flat=True)
        
        if not recent_reactions:
            return 20.0  # Default
        
        avg_latency = np.mean(list(recent_reactions))
        return min(100, avg_latency / 10)  # Scale: 10s = 100 load
    
    def detect_cognitive_state(self):
        """
        Detect current cognitive state based on multiple signals
        States: focused, overloaded, drained, flow, anxious, bored, saturated, recovering
        """
        load_score = self.calculate_cognitive_load_score()
        hrv = self._get_hrv_stability()
        typing_errors = self._calculate_typing_errors()
        task_switches = self._calculate_task_switches()
        
        # State detection logic
        if load_score > 80 and task_switches > 5:
            state = 'overloaded'
        elif load_score > 90 and typing_errors > 20:
            state = 'saturated'
        elif hrv < 30 and load_score > 60:
            state = 'anxious'
        elif load_score < 30 and hrv > 70:
            state = 'drained'
        elif self._is_flow_state(load_score, hrv, typing_errors):
            state = 'flow'
        elif load_score < 40 and typing_errors < 10:
            state = 'bored'
        elif self._is_recovering(load_score, hrv):
            state = 'recovering'
        else:
            state = 'focused'
        
        confidence = self._calculate_state_confidence(state, load_score, hrv)
        
        return {
            'state': state,
            'confidence': confidence,
            'load_score': load_score,
            'hrv': hrv,
            'typing_errors': typing_errors,
            'task_switches': task_switches
        }
    
    def _is_flow_state(self, load_score, hrv, typing_errors):
        """Detect if user is in flow state"""
        # Flow: moderate load, stable HRV, low errors, no switching
        return (40 < load_score < 70 and 
                hrv > 60 and 
                typing_errors < 15 and
                self._calculate_task_switches() < 2)
    
    def _is_recovering(self, load_score, hrv):
        """Detect if user needs recovery"""
        recent_high_stress = BurnoutRisk.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(hours=2)
        ).filter(burnout_risk_score__gte=70).exists()
        
        return recent_high_stress and load_score < 40
    
    def _calculate_state_confidence(self, state, load_score, hrv):
        """Calculate confidence in state detection (0-1)"""
        # More extreme values = higher confidence
        load_confidence = min(abs(load_score - 50) / 50, 1.0)
        hrv_confidence = min(abs(hrv - 50) / 50, 1.0)
        
        combined = (load_confidence + hrv_confidence) / 2
        return min(1.0, combined * 0.95)  # Max 95% confidence
    
    def analyze_burnout_risk(self):
        """
        Calculate burnout risk score and identify warning signs
        """
        # Get historical data (last 7 days)
        seven_days_ago = self.current_time - timedelta(days=7)
        
        cognitive_states = CognitiveState.objects.filter(
            user=self.user,
            timestamp__gte=seven_days_ago
        )
        
        # Burnout contributing factors
        overload_days = cognitive_states.filter(cognitive_state='overloaded').values_list(
            'timestamp__date', flat=True
        ).distinct().count()
        
        saturated_days = cognitive_states.filter(cognitive_state='saturated').values_list(
            'timestamp__date', flat=True
        ).distinct().count()
        
        # Stress accumulation
        avg_load = cognitive_states.aggregate(Avg('cognitive_load_score'))['cognitive_load_score__avg'] or 0
        
        # Recovery deficit
        recovery_tasks = cognitive_states.filter(cognitive_state='recovering').count()
        recovery_ratio = recovery_tasks / max(cognitive_states.count(), 1)
        
        # Calculate burnout score
        burnout_score = (
            (overload_days * 5) +  # 5 points per overload day
            (saturated_days * 8) +  # 8 points per saturation day
            (avg_load * 0.3) +  # Continuous load pressure
            ((1 - recovery_ratio) * 20)  # Recovery deficit
        )
        
        burnout_score = min(100, max(0, burnout_score))
        
        # Determine level
        if burnout_score >= 75:
            level = 'critical'
        elif burnout_score >= 60:
            level = 'high'
        elif burnout_score >= 40:
            level = 'moderate'
        else:
            level = 'low'
        
        # Trend analysis
        recent_risk = BurnoutRisk.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(days=3)
        ).order_by('-timestamp')[:2]
        
        if len(recent_risk) >= 2:
            if recent_risk[0].burnout_risk_score > recent_risk[1].burnout_risk_score:
                trend = 'worsening'
            elif recent_risk[0].burnout_risk_score < recent_risk[1].burnout_risk_score:
                trend = 'improving'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # Recommendations
        recommendations = self._generate_recovery_recommendations(burnout_score, level)
        
        return {
            'burnout_score': burnout_score,
            'level': level,
            'trend': trend,
            'overload_days': overload_days,
            'recovery_deficit': 1 - recovery_ratio,
            'recommendations': recommendations
        }
    
    def _generate_recovery_recommendations(self, burnout_score, level):
        """Generate personalized recovery recommendations"""
        recommendations = []
        
        if level == 'critical':
            recommendations.extend([
                'Take immediate 15-minute break',
                'Consider taking rest day tomorrow',
                'Delegate or postpone non-urgent tasks',
                'Practice breathing exercises (5 min)',
                'Reach out to support network'
            ])
        elif level == 'high':
            recommendations.extend([
                'Take 10-minute break every hour',
                'Reduce task load by 30%',
                'Ensure 8 hours sleep tonight',
                'Schedule recovery time',
                'Avoid new commitments'
            ])
        elif level == 'moderate':
            recommendations.extend([
                'Take 5-minute breaks hourly',
                'Reduce load by 15%',
                'Maintain regular sleep schedule',
                'Light exercise recommended'
            ])
        
        return recommendations
    
    def detect_attention_span_decay(self):
        """Detect how user's attention decays over time"""
        recent_metrics = AttentionSpanMetrics.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(hours=8)
        ).order_by('timestamp')
        
        if recent_metrics.count() < 3:
            return {'decay_rate': 0.05, 'current_span': 45, 'prediction': 'insufficient_data'}
        
        focus_durations = list(recent_metrics.values_list('focus_duration_minutes', flat=True))
        timestamps = list(recent_metrics.values_list('timestamp', flat=True))
        
        # Calculate decay rate
        decay_rates = []
        for i in range(1, len(focus_durations)):
            time_diff = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # hours
            duration_change = (focus_durations[i] - focus_durations[i-1]) / focus_durations[i-1]
            decay_rates.append(abs(duration_change) / time_diff)
        
        avg_decay_rate = np.mean(decay_rates) if decay_rates else 0.05
        current_span = focus_durations[-1]
        
        # Predict when focus will drop below 15 min
        if avg_decay_rate > 0:
            minutes_to_critical = current_span / (avg_decay_rate * 60)
        else:
            minutes_to_critical = float('inf')
        
        return {
            'decay_rate': avg_decay_rate,
            'current_span_minutes': current_span,
            'typical_span_minutes': np.mean(focus_durations),
            'minutes_to_critical': minutes_to_critical,
            'needs_break': current_span < 15,
            'suggested_break_type': 'long' if current_span < 10 else 'short'
        }
    
    def track_decision_quality_decline(self):
        """Track how decision quality changes with fatigue/load"""
        recent_decisions = DecisionDegradationTracker.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(hours=4)
        ).order_by('-timestamp')[:10]
        
        if not recent_decisions:
            return {'decline_detected': False, 'recommendations': []}
        
        quality_scores = list(recent_decisions.values_list('decision_quality_score', flat=True))
        fatigue_levels = list(recent_decisions.values_list('fatigue_level', flat=True))
        
        # Analyze decline
        avg_quality = np.mean(quality_scores)
        trend = 'declining' if quality_scores[-1] < quality_scores[0] else 'stable'
        quality_decline = max(0, quality_scores[0] - quality_scores[-1])
        
        # Correlation with fatigue
        if len(fatigue_levels) > 1:
            fatigue_increase = fatigue_levels[-1] - fatigue_levels[0]
            correlated = quality_decline > 5 and fatigue_increase > 10
        else:
            correlated = False
        
        recommendations = []
        if avg_quality < 80:
            recommendations.append('Take a break before making important decisions')
        if trend == 'declining':
            recommendations.append('Decision quality is declining - defer non-urgent decisions')
        if correlated:
            recommendations.append('Fatigue is affecting decision-making quality')
        
        return {
            'average_quality': avg_quality,
            'trend': trend,
            'decline_detected': quality_decline > 5,
            'quality_decline_points': quality_decline,
            'correlated_with_fatigue': correlated,
            'recommendations': recommendations
        }
    
    def save_cognitive_state(self, state_data):
        """Save cognitive state to database"""
        return CognitiveState.objects.create(
            user=self.user,
            cognitive_state=state_data['state'],
            confidence=state_data['confidence'],
            cognitive_load_score=state_data['load_score'],
            heart_rate_variability=state_data['hrv'],
            typing_error_rate=state_data['typing_errors'],
            task_switch_frequency=state_data['task_switches']
        )
    
    def get_user_cognitive_dna(self):
        """Get or create user's cognitive profile"""
        dna, created = CognitiveUserDNA.objects.get_or_create(user=self.user)
        
        if created:
            self._initialize_cognitive_dna(dna)
        
        return dna
    
    def _initialize_cognitive_dna(self, dna):
        """Initialize cognitive DNA with baseline values"""
        # Get historical data if available
        historical = CognitiveState.objects.filter(user=self.user)
        
        if historical.exists():
            avg_load = historical.aggregate(Avg('cognitive_load_score'))['cognitive_load_score__avg']
            dna.stress_tolerance_threshold = min(100, avg_load + 20)  # Threshold is 20 points above baseline
        
        dna.optimal_session_length_minutes = 90  # Default Pomodoro
        dna.typical_attention_span_minutes = 45  # Default
        dna.recovery_speed_hours = 8  # Default 8 hours
        dna.save()
