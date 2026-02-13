from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random, json

from emotion_detection.explainability_models import Insight, ConfidenceScore, ExplainabilitySignal
from emotion_detection.models import UserIntervention


class Command(BaseCommand):
    help = 'Seed sample insights, confidence scores and explainability signals for users (test/dev only)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='How many days back to simulate')
        parser.add_argument('--limit', type=int, default=10, help='Max users to seed')

    def handle(self, *args, **options):
        User = get_user_model()
        days = options['days']
        limit = options['limit']

        users = User.objects.all()[:limit]
        now = timezone.now()

        for user in users:
            # Create a few insights
            for i in range(3):
                ins = Insight.objects.create(
                    user=user,
                    category=random.choice(['mood_trend', 'pattern', 'recommendation', 'correlation']),
                    title=f"Sample insight {i+1}",
                    description="This is a seeded sample insight for development and testing.",
                    insight_type=random.choice(['trend', 'statistic', 'recommendation']),
                    data={'sample_points': [random.random() for _ in range(5)]},
                    confidence=round(random.uniform(0.4, 0.95), 2),
                    relevance_score=round(random.uniform(0.4, 0.95), 2),
                    is_actionable=random.choice([True, False]),
                    suggested_action="Try a breathing exercise." if random.random() > 0.5 else "Consider a short walk.",
                    period_start=(now - timedelta(days=days)).date(),
                    period_end=now.date()
                )

            # Create a confidence score for recent recommendations
            ConfidenceScore.objects.create(
                user=user,
                subject='intervention_recommendation',
                subject_id=None,
                confidence=round(random.uniform(0.5, 0.9), 2),
                factors={'data_recency': 0.9, 'sample_size': 0.6},
                explanation='Synthetic sample confidence for testing',
                uncertainty_reasons=['Limited historical data']
            )

            # If user has a recent intervention, attach a simple explainability signal
            intervention = UserIntervention.objects.filter(user=user).order_by('-triggered_at').first()
            if intervention:
                try:
                    ExplainabilitySignal.objects.create(
                        intervention=intervention,
                        trigger_reason='multi_factor',
                        explanation='Seeded explainability signal attached to existing intervention.',
                        confidence_score=0.6,
                        evidence_points=['recent_journal', 'hrv_drop'],
                        user_state_snapshot={'emotion': 'neutral'},
                        rule_code=str(intervention.rule.id),
                        rule_priority=intervention.rule.priority if hasattr(intervention.rule, 'priority') else 0,
                        historical_effectiveness=0.5,
                        alternatives_considered=[]
                    )
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS('Seeded sample insights and confidence scores.'))
