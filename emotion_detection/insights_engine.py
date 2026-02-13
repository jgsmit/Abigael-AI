"""
Insights Engine - Generates actionable insights from user data patterns.

Responsible for:
1. Analyzing user behavior and biofeedback data
2. Detecting patterns and correlations
3. Generating insights for user consumption
4. Calculating confidence scores
5. Generating explainability for recommendations
"""

from django.utils import timezone
from django.db.models import Avg, Count, Q, F
from datetime import timedelta
import json
from statistics import mean, stdev

from .explainability_models import (
    ExplainabilitySignal,
    InterventionEffectiveness,
    UserPattern,
    Insight,
    ConfidenceScore,
)
from .models import JournalEntry, UserIntervention
from .intervention_models import InterventionRule


class InsightsEngine:
    """Autonomously generates insights from user data."""
    
    def __init__(self, user):
        self.user = user
        self.logger = __import__('logging').getLogger(__name__)
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def generate_all_insights(self, days=30):
        """
        Generate all types of insights for user.
        
        Returns:
            [Insight]
        """
        insights = []
        
        # Mood trend
        mood_insight = self._generate_mood_trend_insight(days)
        if mood_insight:
            insights.append(mood_insight)
        
        # Intervention effectiveness
        effectiveness_insights = self._generate_effectiveness_insights(days)
        insights.extend(effectiveness_insights)
        
        # Detected patterns
        pattern_insights = self._generate_pattern_insights(days)
        insights.extend(pattern_insights)
        
        # Correlations
        correlation_insights = self._generate_correlation_insights(days)
        insights.extend(correlation_insights)
        
        # Recommendations
        recommendation_insights = self._generate_recommendation_insights()
        insights.extend(recommendation_insights)
        
        return insights
    
    def create_recommendation_explanation(self, intervention) -> ExplainabilitySignal:
        """
        Create explainability signal for an intervention.
        Called when intervention is triggered.
        """
        from .biofeedback_integration_engine import BiofeedbackIntegrationEngine
        
        # Gather user state at time of triggering
        bio_engine = BiofeedbackIntegrationEngine(self.user)
        bio_state = bio_engine.gather_user_state()
        
        # Get latest journal entry
        latest_entry = JournalEntry.objects.filter(user=self.user).order_by('-entry_date').first()
        
        # Build user state snapshot
        user_state = {
            'emotion': latest_entry.primary_emotion if latest_entry else 'unknown',
            'stress_level': latest_entry.emotion_intensity if latest_entry else 0.5,
            'heart_rate': bio_state.get('heart_rate'),
            'sleep_quality': bio_state.get('sleep_quality'),
            'activity_level': bio_state.get('activity_level'),
        }
        
        # Determine trigger reason
        trigger_reason = self._determine_trigger_reason(intervention.rule, user_state)
        
        # Generate explanation
        explanation = self._generate_trigger_explanation(trigger_reason, user_state)
        
        # Calculate confidence in this recommendation
        confidence = self._calculate_recommendation_confidence(
            intervention.rule,
            user_state
        )
        
        # Get historical effectiveness
        effectiveness = InterventionEffectiveness.objects.filter(
            rule=intervention.rule
        ).first()
        historical_effectiveness = effectiveness.helpful_rate if effectiveness else 0.5
        
        # Create signal
        signal = ExplainabilitySignal.objects.create(
            intervention=intervention,
            trigger_reason=trigger_reason,
            explanation=explanation,
            confidence_score=confidence,
            evidence_points=self._gather_evidence(intervention.rule, user_state),
            user_state_snapshot=user_state,
            rule_code=intervention.rule.code if hasattr(intervention.rule, 'code') else str(intervention.rule.id),
            rule_priority=intervention.rule.priority,
            historical_effectiveness=historical_effectiveness,
            alternatives_considered=self._find_alternatives(intervention.rule, user_state),
        )
        
        # Create confidence score record
        ConfidenceScore.objects.create(
            user=self.user,
            subject='intervention_recommendation',
            subject_id=intervention.id,
            confidence=confidence,
            factors=self._calculate_confidence_factors(intervention.rule, user_state),
            explanation=explanation,
            uncertainty_reasons=self._identify_uncertainty_reasons(user_state),
        )
        
        return signal
    
    def detect_patterns(self) -> list:
        """
        Scan for behavior patterns in user data.
        Returns: [UserPattern]
        """
        patterns = []
        
        # Pattern 1: Daily stress peak times
        stress_pattern = self._detect_daily_stress_peaks()
        if stress_pattern:
            patterns.append(stress_pattern)
        
        # Pattern 2: Emotion cycles
        emotion_pattern = self._detect_emotion_cycle()
        if emotion_pattern:
            patterns.append(emotion_pattern)
        
        # Pattern 3: Sleep impact on mood
        sleep_pattern = self._detect_sleep_impact()
        if sleep_pattern:
            patterns.append(sleep_pattern)
        
        # Pattern 4: Intervention responsiveness
        response_pattern = self._detect_intervention_response_pattern()
        if response_pattern:
            patterns.append(response_pattern)
        
        # Pattern 5: Activity-emotion link
        activity_pattern = self._detect_activity_emotion_link()
        if activity_pattern:
            patterns.append(activity_pattern)
        
        return patterns
    
    # ========================================================================
    # Private Methods: Insight Generation
    # ========================================================================
    
    def _generate_mood_trend_insight(self, days=30) -> Insight:
        """Generate insight about mood trend."""
        start_date = timezone.now().date() - timedelta(days=days)
        entries = JournalEntry.objects.filter(
            user=self.user,
            entry_date__gte=start_date
        ).order_by('entry_date')
        
        if not entries.exists():
            return None
        
        # Calculate trend
        intensities = list(entries.values_list('emotion_intensity', flat=True))
        if len(intensities) < 2:
            return None
        
        avg_intensity = mean(intensities)
        first_week = mean(intensities[:len(intensities)//2])
        second_week = mean(intensities[len(intensities)//2:])
        
        # Determine trend
        if second_week < first_week * 0.85:
            title = "Your mood is improving! 📈"
            category = 'mood_trend'
            trend_type = 'improving'
        elif second_week > first_week * 1.15:
            title = "Your mood has been more challenging lately"
            category = 'mood_trend'
            trend_type = 'declining'
        else:
            title = "Your mood has been stable"
            category = 'mood_trend'
            trend_type = 'stable'
        
        description = f"Over the past {days} days, your average mood intensity is {avg_intensity:.1f}/1.0. "
        description += f"First period: {first_week:.1f}, Recent period: {second_week:.1f}"
        
        insight = Insight(
            user=self.user,
            category='mood_trend',
            title=title,
            description=description,
            insight_type='trend',
            data={
                'intensities': intensities,
                'average': avg_intensity,
                'trend': trend_type,
                'improvement_percent': ((first_week - second_week) / first_week * 100) if first_week > 0 else 0,
            },
            confidence=0.8,
            relevance_score=0.9,
            is_actionable=trend_type != 'stable',
            period_start=start_date,
            period_end=timezone.now().date(),
        )
        
        if trend_type == 'declining':
            insight.suggested_action = "Consider reviewing your interventions or reaching out for support."
        elif trend_type == 'improving':
            insight.suggested_action = "Great progress! Keep up what you're doing."
        
        return insight
    
    def _generate_effectiveness_insights(self, days=30) -> list:
        """Generate insights about intervention effectiveness."""
        insights = []
        
        # Find interventions with enough data
        start_date = timezone.now() - timedelta(days=days)
        interventions = UserIntervention.objects.filter(
            user=self.user,
            triggered_at__gte=start_date,
            completed=True
        ).values('rule').annotate(
            count=Count('id'),
            helpful_count=Count('id', filter=Q(was_helpful=True))
        ).filter(count__gte=3)  # At least 3 completions
        
        for intervention_data in interventions:
            rule = InterventionRule.objects.get(id=intervention_data['rule'])
            success_rate = intervention_data['helpful_count'] / intervention_data['count']
            
            if success_rate > 0.7:
                title = f"✅ {rule.name.title()} works well for you"
                description = f"You found {rule.name.lower()} helpful {intervention_data['helpful_count']}/{intervention_data['count']} times."
                category = 'effectiveness'
                is_actionable = True
                suggested_action = f"Keep using {rule.name.lower()} when needed - it's working!"
            elif success_rate < 0.4:
                title = f"⚠️ {rule.name.title()} might not be the right fit"
                description = f"You found {rule.name.lower()} helpful only {intervention_data['helpful_count']}/{intervention_data['count']} times."
                category = 'concern'
                is_actionable = True
                suggested_action = f"Try other interventions - {rule.name.lower()} doesn't seem to help much."
            else:
                continue  # Skip moderate effectiveness
            
            insight = Insight(
                user=self.user,
                category=category,
                title=title,
                description=description,
                insight_type='statistic',
                data={
                    'rule_id': rule.id,
                    'success_rate': success_rate,
                    'total': intervention_data['count'],
                    'helpful': intervention_data['helpful_count'],
                },
                confidence=0.7 if intervention_data['count'] >= 5 else 0.5,
                relevance_score=0.8,
                is_actionable=is_actionable,
                suggested_action=suggested_action,
                period_start=start_date.date(),
                period_end=timezone.now().date(),
            )
            
            insights.append(insight)
        
        return insights
    
    def _generate_pattern_insights(self, days=30) -> list:
        """Generate insights based on detected patterns."""
        insights = []
        patterns = self.detect_patterns()
        
        for pattern in patterns:
            insight = Insight(
                user=self.user,
                category='pattern',
                title=f"Pattern detected: {pattern.get_pattern_type_display()}",
                description=pattern.description,
                insight_type='correlation',
                data=pattern.details,
                confidence=pattern.confidence,
                relevance_score=max(0.6, pattern.confidence),
                is_actionable=bool(pattern.suggested_action),
                suggested_action=pattern.suggested_action,
                period_start=timezone.now().date() - timedelta(days=days),
                period_end=timezone.now().date(),
            )
            insights.append(insight)
        
        return insights
    
    def _generate_correlation_insights(self, days=30) -> list:
        """Generate insights about correlations (e.g., sleep affects mood)."""
        insights = []
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Sleep vs mood correlation
        from .biofeedback_models import SleepRecord, DailyBiofeedbackSummary
        
        sleep_data = DailyBiofeedbackSummary.objects.filter(
            user=self.user,
            date__gte=start_date
        ).values_list('sleep_duration_hours', 'sleep_quality')
        
        mood_data = JournalEntry.objects.filter(
            user=self.user,
            entry_date__gte=start_date
        ).order_by('entry_date').values_list('emotion_intensity', flat=True)
        
        if len(sleep_data) >= 5 and len(mood_data) >= 5:
            # Simple correlation check
            sleep_hours = [s[0] for s in sleep_data if s[0]]
            if sleep_hours:
                avg_sleep = mean(sleep_hours)
                
                # Find days with good vs bad sleep
                good_sleep_days = [s for s in sleep_data if s[0] and s[0] > avg_sleep + 1]
                bad_sleep_days = [s for s in sleep_data if s[0] and s[0] < avg_sleep - 1]
                
                if good_sleep_days and bad_sleep_days:
                    insight = Insight(
                        user=self.user,
                        category='correlation',
                        title="Sleep quality affects your mood",
                        description="Your mood tends to be better on nights with good sleep.",
                        insight_type='correlation',
                        data={
                            'correlation_type': 'sleep_mood',
                            'avg_sleep': avg_sleep,
                        },
                        confidence=0.65,
                        relevance_score=0.8,
                        is_actionable=True,
                        suggested_action="Prioritize sleep - even 1-2 extra hours can improve your mood.",
                        period_start=start_date,
                        period_end=timezone.now().date(),
                    )
                    insights.append(insight)
        
        return insights
    
    def _generate_recommendation_insights(self) -> list:
        """Generate personalized intervention recommendations."""
        insights = []
        
        # Find ineffective interventions used frequently
        last_30_days = timezone.now() - timedelta(days=30)
        ineffective = UserIntervention.objects.filter(
            user=self.user,
            triggered_at__gte=last_30_days,
            completed=True
        ).values('rule').annotate(
            count=Count('id'),
            helpful_count=Count('id', filter=Q(was_helpful=True))
        ).filter(
            count__gte=2,
            helpful_count__lt=1  # Never marked helpful
        )
        
        if ineffective.exists():
            rules = [InterventionRule.objects.get(id=i['rule']).name for i in ineffective]
            
            insight = Insight(
                user=self.user,
                category='recommendation',
                title="Time to try something different",
                description=f"You've tried {', '.join(rules)} recently without them helping. Let's explore new approaches.",
                insight_type='recommendation',
                confidence=0.7,
                relevance_score=0.85,
                is_actionable=True,
                suggested_action="Check out the Reward Shop for new intervention options or talk to your companion about alternatives.",
            )
            insights.append(insight)
        
        return insights
    
    # ========================================================================
    # Private Methods: Pattern Detection
    # ========================================================================
    
    def _detect_daily_stress_peaks(self) -> UserPattern:
        """Detect if stress peaks at certain times of day."""
        from .biofeedback_models import StressRecord
        
        # Get stress data from last 2 weeks
        two_weeks = timezone.now() - timedelta(days=14)
        stress_records = StressRecord.objects.filter(
            user=self.user,
            timestamp__gte=two_weeks
        )
        
        if stress_records.count() < 20:
            return None
        
        # Group by hour
        stress_by_hour = {}
        for record in stress_records:
            hour = record.timestamp.hour
            if hour not in stress_by_hour:
                stress_by_hour[hour] = []
            stress_by_hour[hour].append(record.stress_level)
        
        # Find peak hours
        hour_averages = {h: mean(levels) for h, levels in stress_by_hour.items()}
        if not hour_averages:
            return None
        
        peak_hour = max(hour_averages, key=hour_averages.get)
        peak_stress = hour_averages[peak_hour]
        avg_stress = mean(hour_averages.values())
        
        if peak_stress > avg_stress * 1.2:
            return UserPattern(
                user=self.user,
                pattern_type='daily_stress_peak',
                description=f"Your stress typically peaks around {peak_hour}:00 (stress level: {peak_stress:.1f})",
                details={'peak_hour': peak_hour, 'peak_stress': peak_stress, 'average_stress': avg_stress},
                confidence=0.7,
                sample_size=stress_records.count(),
                impact_description="Stress spikes in the afternoon could affect your workday performance and mood.",
                suggested_action="Plan a break or intervention around this time to manage stress proactively.",
                recommended_interventions=['breathing_exercise', 'meditation', 'movement_break'],
            )
        
        return None
    
    def _detect_emotion_cycle(self) -> UserPattern:
        """Detect recurring emotion cycles (e.g., weekly patterns)."""
        # Get 4+ weeks of journal data
        four_weeks = timezone.now().date() - timedelta(days=28)
        entries = JournalEntry.objects.filter(
            user=self.user,
            entry_date__gte=four_weeks
        )
        
        if entries.count() < 10:
            return None
        
        # Group by day of week
        emotion_by_dow = {}
        for entry in entries:
            dow = entry.entry_date.strftime('%A')
            if dow not in emotion_by_dow:
                emotion_by_dow[dow] = []
            emotion_by_dow[dow].append(entry.emotion_intensity)
        
        # Find pattern
        dow_averages = {dow: mean(intensities) for dow, intensities in emotion_by_dow.items()}
        
        if dow_averages:
            worst_day = min(dow_averages, key=dow_averages.get)
            worst_intensity = dow_averages[worst_day]
            
            if worst_intensity < mean(dow_averages.values()) * 0.8:
                return UserPattern(
                    user=self.user,
                    pattern_type='emotion_cycle',
                    description=f"Your mood tends to be lower on {worst_day}s.",
                    details={'worst_day': worst_day, 'day_intensities': dow_averages},
                    confidence=0.65,
                    sample_size=entries.count(),
                    impact_description=f"You consistently feel worse on {worst_day}s, which could be related to weekly routines.",
                    suggested_action=f"Plan extra self-care or interventions for {worst_day}s.",
                    recommended_interventions=['mood_boost', 'gratitude', 'social_connection'],
                )
        
        return None
    
    def _detect_sleep_impact(self) -> UserPattern:
        """Detect impact of sleep quality on next day's mood."""
        from .biofeedback_models import DailyBiofeedbackSummary
        
        start_date = timezone.now().date() - timedelta(days=30)
        summaries = DailyBiofeedbackSummary.objects.filter(
            user=self.user,
            date__gte=start_date
        ).order_by('date')
        
        if summaries.count() < 20:
            return None
        
        # Correlate previous night's sleep with next day's mood
        correlations = []
        for i, summary in enumerate(summaries[:-1]):
            next_entry = JournalEntry.objects.filter(
                user=self.user,
                entry_date=summaries[i+1].date
            ).first()
            
            if next_entry and summary.sleep_quality:
                correlations.append({
                    'sleep_quality': summary.sleep_quality,
                    'mood_intensity': next_entry.emotion_intensity
                })
        
        if len(correlations) >= 10:
            # Simple correlation
            sleep_scores = [c['sleep_quality'] for c in correlations]
            mood_scores = [c['mood_intensity'] for c in correlations]
            
            # If high sleep quality = low mood intensity, that's good
            avg_good_sleep_mood = mean([m for s, m in zip(sleep_scores, mood_scores) if s > 75])
            avg_bad_sleep_mood = mean([m for s, m in zip(sleep_scores, mood_scores) if s < 50])
            
            if avg_good_sleep_mood and avg_bad_sleep_mood:
                if avg_good_sleep_mood < avg_bad_sleep_mood:
                    return UserPattern(
                        user=self.user,
                        pattern_type='sleep_impact',
                        description="Good sleep quality noticeably improves your next day's mood.",
                        details={
                            'good_sleep_mood': avg_good_sleep_mood,
                            'bad_sleep_mood': avg_bad_sleep_mood,
                        },
                        confidence=0.7,
                        sample_size=len(correlations),
                        impact_description="Poor sleep directly impacts your emotional wellbeing the following day.",
                        suggested_action="Prioritize consistent sleep (7-9 hours) to maintain better mood.",
                    )
        
        return None
    
    def _detect_intervention_response_pattern(self) -> UserPattern:
        """Detect how quickly user responds to interventions."""
        # Get recent interventions with before/after mood
        return None  # Simplified for now
    
    def _detect_activity_emotion_link(self) -> UserPattern:
        """Detect link between activity and mood."""
        from .biofeedback_models import ActivityRecord, DailyBiofeedbackSummary
        
        start_date = timezone.now().date() - timedelta(days=30)
        activity_summaries = DailyBiofeedbackSummary.objects.filter(
            user=self.user,
            date__gte=start_date,
            active_minutes__isnull=False
        )
        
        if activity_summaries.count() < 15:
            return None
        
        # Correlate activity with stress
        active_days = activity_summaries.filter(active_minutes__gte=30)
        sedentary_days = activity_summaries.filter(active_minutes__lt=10)
        
        if active_days.exists() and sedentary_days.exists():
            avg_active_stress = active_days.aggregate(Avg('stress_level'))['stress_level__avg']
            avg_sedentary_stress = sedentary_days.aggregate(Avg('stress_level'))['stress_level__avg']
            
            if avg_active_stress and avg_sedentary_stress:
                if avg_active_stress < avg_sedentary_stress:
                    return UserPattern(
                        user=self.user,
                        pattern_type='activity_trigger',
                        description="You feel less stressed on days when you're more active.",
                        details={
                            'active_stress': avg_active_stress,
                            'sedentary_stress': avg_sedentary_stress,
                        },
                        confidence=0.65,
                        sample_size=activity_summaries.count(),
                        impact_description="Physical activity has a positive effect on your stress levels.",
                        suggested_action="Aim for 30+ minutes of activity daily to maintain lower stress.",
                        recommended_interventions=['movement_break', 'walk', 'exercise'],
                    )
        
        return None
    
    # ========================================================================
    # Private Methods: Explanation & Confidence
    # ========================================================================
    
    def _determine_trigger_reason(self, rule, user_state) -> str:
        """Determine primary reason intervention was triggered."""
        if rule.trigger_type == 'emotion':
            return 'emotion_match'
        elif rule.trigger_type == 'stress_level':
            return 'stress_threshold'
        elif rule.trigger_type == 'no_interaction':
            return 'inactivity'
        elif rule.trigger_type == 'time_of_day':
            return 'time_window'
        else:
            return 'multi_factor'
    
    def _generate_trigger_explanation(self, reason: str, user_state) -> str:
        """Generate human-readable explanation."""
        explanations = {
            'emotion_match': f"We noticed you're feeling {user_state.get('emotion', 'something')}, which often helps to address with this intervention.",
            'stress_threshold': f"Your stress level ({user_state.get('stress_level', 0)*100:.0f}) is elevated, and this intervention can help.",
            'inactivity': "We haven't heard from you in a while - this intervention might help you feel more connected.",
            'time_window': "It's a good time to check in with this intervention.",
            'pattern_detected': "Based on your patterns, this intervention would be helpful right now.",
            'biofeedback_anomaly': "Your biofeedback data suggests you might benefit from this intervention.",
            'user_pattern': "Based on what works for you, we recommend this intervention.",
            'multi_factor': "Multiple factors suggest this would be helpful.",
        }
        return explanations.get(reason, "This intervention was selected for you.")
    
    def _calculate_recommendation_confidence(self, rule, user_state) -> float:
        """Calculate confidence in recommendation (0-1)."""
        confidence = 0.5
        
        # Add confidence if emotion matches
        if user_state.get('emotion') in str(rule.trigger_condition):
            confidence += 0.2
        
        # Add confidence if stress is high
        if user_state.get('stress_level', 0) > 0.6:
            confidence += 0.15
        
        # Check historical effectiveness
        try:
            effectiveness = InterventionEffectiveness.objects.get(rule=rule)
            if effectiveness.helpful_rate > 0.7:
                confidence += 0.15
        except:
            pass
        
        return min(1.0, confidence)
    
    def _gather_evidence(self, rule, user_state) -> list:
        """Gather list of evidence points supporting recommendation."""
        evidence = []
        
        if user_state.get('emotion'):
            evidence.append(f"Your emotional state: {user_state['emotion']}")
        
        if user_state.get('stress_level', 0) > 0.6:
            evidence.append(f"Elevated stress level: {user_state['stress_level']*100:.0f}%")
        
        if user_state.get('sleep_quality', 50) < 50:
            evidence.append("Poor sleep quality detected")
        
        try:
            effectiveness = InterventionEffectiveness.objects.get(rule=rule)
            if effectiveness.helpful_rate > 0:
                evidence.append(f"Historical success rate: {effectiveness.helpful_rate*100:.0f}%")
        except:
            pass
        
        return evidence
    
    def _calculate_confidence_factors(self, rule, user_state) -> dict:
        """Calculate individual factors contributing to confidence."""
        return {
            'data_recency': 0.9,  # Fresh data
            'sample_size': 0.6 if rule else 0.4,  # Some history
            'historical_consistency': 0.7,  # Generally consistent
            'personalization': 0.8,  # Tailored to user
            'rule_effectiveness': 0.7,
        }
    
    def _identify_uncertainty_reasons(self, user_state) -> list:
        """List reasons why confidence might not be 100%."""
        reasons = []
        
        if not user_state.get('heart_rate'):
            reasons.append("Limited biofeedback data")
        
        if not user_state.get('sleep_quality'):
            reasons.append("Sleep data not available")
        
        stress = user_state.get('stress_level', 0.5)
        if 0.4 <= stress <= 0.6:
            reasons.append("Stress level is moderate, recommendation less certain")
        
        return reasons
    
    def _find_alternatives(self, rule, user_state) -> list:
        """Find alternative interventions that could have been recommended."""
        from .intervention_models import InterventionRule
        
        alternatives = []
        
        similar_rules = InterventionRule.objects.filter(
            is_active=True
        ).exclude(id=rule.id)[:3]
        
        for alt_rule in similar_rules:
            alternatives.append({
                'rule_id': alt_rule.id,
                'name': alt_rule.name,
                'reason_not_selected': 'Less relevant for current state',
            })
        
        return alternatives
