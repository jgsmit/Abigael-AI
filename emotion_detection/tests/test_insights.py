from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from emotion_detection.explainability_models import Insight


class InsightsExportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='insight_tester', password='testpass')
        self.client = Client()
        self.client.login(username='insight_tester', password='testpass')

        self.insight = Insight.objects.create(
            user=self.user,
            category='mood_trend',
            title='Unit test insight',
            description='Testing export endpoints',
            insight_type='trend',
            data={'a': 1},
            confidence=0.75,
            relevance_score=0.8,
            is_actionable=True,
        )

    def test_export_insight_json(self):
        url = reverse('export_insight_json', args=[self.insight.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('title', resp.json())

    def test_export_insight_csv(self):
        url = reverse('export_insight_csv', args=[self.insight.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        content = resp.content.decode('utf-8')
        self.assertIn('Unit test insight', content)
