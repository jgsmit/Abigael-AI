"""Micro-intervention engine for triggering contextual nudges and supportive tasks."""
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta
import json
import random

from .intervention_models import InterventionRule, InterventionContent, UserIntervention
from .companion_models import JournalEntry, CrisisDetection

# Import biofeedback engine (optional - won't fail if not available)
try:
    from .biofeedback_integration_engine import BiofeedbackIntegrationEngine
    BIOFEEDBACK_AVAILABLE = True
except ImportError:
    BIOFEEDBACK_AVAILABLE = False

# Import insights engine (optional)
try:
    from .insights_engine import InsightsEngine
    INSIGHTS_AVAILABLE = True
except ImportError:
    INSIGHTS_AVAILABLE = False


class InterventionEngine:
    """Evaluates rules and triggers interventions for users."""
    
    def __init__(self):
        self.cache = {}
    
    def evaluate_user(self, user):
        """Evaluate current user state and trigger interventions if appropriate."""
        try:
            # Get user's current state
            current_state = self._get_user_state(user)
            
            # Get active rules
            rules = InterventionRule.objects.filter(is_active=True).order_by('-priority')
            
            triggered = []
            for rule in rules:
                if self._should_trigger(user, rule, current_state):
                    intervention = self._create_intervention(user, rule)
                    if intervention:
                        triggered.append(intervention)
            
            return triggered
        except Exception as e:
            print(f"Error evaluating interventions for {user.username}: {e}")
            return []
    
    def _get_user_state(self, user):
        """Gather current user emotional and behavioral state."""
        try:
            state = {
                'timestamp': timezone.now(),
                'emotion': 'neutral',
                'stress_level': 0.5,
                'is_engaged': False,
                'recent_pattern': None,
            }
            
            # Get latest journal entry
            latest_entry = JournalEntry.objects.filter(user=user).order_by('-entry_date').first()
            if latest_entry:
                state['emotion'] = latest_entry.primary_emotion
                state['stress_level'] = latest_entry.emotion_intensity
                state['is_engaged'] = True
            
            # Check for recent crisis detection
            recent_crisis = CrisisDetection.objects.filter(
                user=user,
                detected_at__gte=timezone.now() - timedelta(hours=24)
            ).first()
            if recent_crisis:
                state['stress_level'] = min(1.0, state['stress_level'] + 0.3)
            
            # Check inactivity
            last_24h = timezone.now() - timedelta(hours=24)
            recent_activity = UserIntervention.objects.filter(
                user=user,
                triggered_at__gte=last_24h
            ).exists()
            if not recent_activity:
                state['recent_pattern'] = 'inactive'
            
            # ====== BIOFEEDBACK INTEGRATION ======
            # If biofeedback is available, enrich state with physiological data
            if BIOFEEDBACK_AVAILABLE:
                try:
                    bio_engine = BiofeedbackIntegrationEngine(user)
                    bio_state = bio_engine.gather_user_state()
                    
                    # Merge biofeedback data
                    state['heart_rate'] = bio_state.get('heart_rate')
                    state['hrv'] = bio_state.get('hrv')
                    state['sleep_quality'] = bio_state.get('sleep_quality', 0.5)
                    state['sleep_hours'] = bio_state.get('sleep_hours', 0.0)
                    state['activity_level'] = bio_state.get('activity_level', 'sedentary')
                    state['heart_rate_trend'] = bio_state.get('heart_rate_trend', 'stable')
                    state['biofeedback_alerts'] = bio_state.get('alerts', [])
                    state['biofeedback_anomalies'] = bio_state.get('anomalies', [])
                    
                    # Adjust stress_level based on biofeedback if available
                    bio_stress = bio_state.get('stress_level')
                    if bio_stress is not None:
                        # Weight biofeedback at 50% if both emotion and biofeedback available
                        state['stress_level'] = (state['stress_level'] * 0.5) + (bio_stress / 100.0 * 0.5)
                    
                except Exception as e:
                    # Graceful fallback if biofeedback engine fails
                    print(f"Warning: Biofeedback integration failed: {e}")
            
            return state
        except Exception as e:
            print(f"Error getting user state: {e}")
            return {}
    
    def _should_trigger(self, user, rule, state):
        """Check if a rule should trigger for the user."""
        try:
            # Check if already triggered recently (cooldown)
            last_trigger = UserIntervention.objects.filter(
                user=user,
                rule=rule
            ).order_by('-triggered_at').first()
            
            if last_trigger:
                time_since = timezone.now() - last_trigger.triggered_at
                cooldown = timedelta(minutes=rule.cooldown_minutes)
                if time_since < cooldown:
                    return False
            
            # Check daily limit
            today = timezone.now().date()
            today_count = UserIntervention.objects.filter(
                user=user,
                rule=rule,
                triggered_at__date=today
            ).count()
            if today_count >= rule.max_daily:
                return False
            
            # Check time window
            if not self._is_in_time_window(rule):
                return False
            
            # Check trigger condition
            if not self._matches_trigger_condition(rule, state):
                return False
            
            # Success rate A/B testing
            if random.random() > rule.success_rate:
                return False
            
            return True
        except Exception as e:
            print(f"Error checking trigger: {e}")
            return False
    
    def _is_in_time_window(self, rule):
        """Check if current time is within rule's time windows."""
        if not rule.time_windows:
            return True
        
        try:
            current_time = timezone.now().time()
            
            for window in rule.time_windows:
                start = self._parse_time(window.get('start', '00:00'))
                end = self._parse_time(window.get('end', '23:59'))
                
                if start <= current_time <= end:
                    return True
            
            return False
        except Exception:
            return True
    
    def _parse_time(self, time_str):
        """Parse HH:MM format to time object."""
        try:
            parts = time_str.split(':')
            return timezone.datetime.time(int(parts[0]), int(parts[1]))
        except Exception:
            return timezone.datetime.time(0, 0)
    
    def _matches_trigger_condition(self, rule, state):
        """Check if user state matches rule trigger condition."""
        try:
            condition = rule.trigger_condition or {}
            
            if rule.trigger_type == 'emotion':
                emotion = condition.get('emotion')
                intensity_min = condition.get('intensity_min', 0.0)
                intensity_max = condition.get('intensity_max', 1.0)
                
                if state.get('emotion') == emotion:
                    stress = state.get('stress_level', 0.5)
                    return intensity_min <= stress <= intensity_max
            
            elif rule.trigger_type == 'stress_level':
                threshold = condition.get('threshold', 0.7)
                return state.get('stress_level', 0.0) >= threshold
            
            elif rule.trigger_type == 'no_interaction':
                hours_inactive = condition.get('hours', 8)
                return state.get('recent_pattern') == 'inactive'
            
            elif rule.trigger_type == 'time_of_day':
                hour = timezone.now().hour
                start_hour = condition.get('start_hour', 0)
                end_hour = condition.get('end_hour', 23)
                return start_hour <= hour <= end_hour
            
            return True
        except Exception as e:
            print(f"Error matching trigger: {e}")
            return False
    
    def _create_intervention(self, user, rule):
        """Create and schedule an intervention for the user."""
        try:
            # Pick a content variant
            content_options = rule.content.filter(is_active=True)
            if not content_options:
                return None
            
            content = content_options.order_by('?').first()
            
            # Create intervention record
            intervention = UserIntervention.objects.create(
                user=user,
                rule=rule,
                content=content,
                triggered_at=timezone.now()
            )

            # Create an explainability signal if insights subsystem is available
            try:
                if INSIGHTS_AVAILABLE:
                    try:
                        InsightsEngine(user).create_recommendation_explanation(intervention)
                    except Exception as ie:
                        print(f"Warning: Insights generation failed: {ie}")
            except Exception:
                pass

            return intervention
        except Exception as e:
            print(f"Error creating intervention: {e}")
            return None
    
    def deliver_intervention(self, intervention):
        """Mark intervention as delivered."""
        try:
            intervention.delivered_at = timezone.now()
            intervention.viewed = True
            intervention.save()
            return True
        except Exception:
            return False
    
    def complete_intervention(self, intervention, rating=None, was_helpful=None):
        """Mark intervention as completed and record feedback."""
        try:
            intervention.completed = True
            intervention.completed_at = timezone.now()
            intervention.user_rating = rating
            intervention.was_helpful = was_helpful
            intervention.save()
            
            # Update rule success metrics
            if intervention.rule.content:
                rule = intervention.rule
                if was_helpful:
                    rule.success_rate = min(1.0, rule.success_rate + 0.05)
                else:
                    rule.success_rate = max(0.0, rule.success_rate - 0.05)
                rule.save()
            
            return True
        except Exception:
            return False
    
    def get_intervention_status(self, user):
        """Get stats on user's intervention engagement."""
        try:
            week_ago = timezone.now() - timedelta(days=7)
            
            interventions = UserIntervention.objects.filter(
                user=user,
                triggered_at__gte=week_ago
            )
            
            return {
                'total_triggered': interventions.count(),
                'completed': interventions.filter(completed=True).count(),
                'completed_rate': interventions.filter(completed=True).count() / max(1, interventions.count()),
                'avg_rating': sum([i.user_rating for i in interventions if i.user_rating]) / max(1, sum([1 for i in interventions if i.user_rating])),
            }
        except Exception:
            return {}


# Global intervention engine instance
intervention_engine = InterventionEngine()
