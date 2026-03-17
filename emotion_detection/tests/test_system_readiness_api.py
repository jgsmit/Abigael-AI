from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch

from emotion_detection.models import EmotionEvent
from emotion_detection.companion_models import JournalEntry
from emotion_detection.autonomous_models import AutoConfiguration


class SystemReadinessApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='readiness_user', password='testpass123')
        self.client.login(username='readiness_user', password='testpass123')

    def test_readiness_endpoint_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('api_system_readiness'))
        self.assertEqual(response.status_code, 302)

    def test_readiness_endpoint_returns_expected_shape(self):
        EmotionEvent.objects.create(user=self.user, emotion='focused', intensity=0.8)
        JournalEntry.objects.create(user=self.user, title='Daily reflection', key_moments='Made progress today')

        with patch.object(settings, 'AUTONOMOUS_LEARNING_ENABLED', True, create=True), \
             patch.object(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0', create=True), \
             patch.object(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/1', create=True):
            response = self.client.get(reverse('api_system_readiness'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload['status'], 'success')
        readiness = payload['system_readiness']

        self.assertIn('score', readiness)
        self.assertIn('grade', readiness)
        self.assertIn('checks', readiness)
        self.assertIn('recommendations', readiness)
        self.assertIn('generated_at', readiness)
        self.assertIn('history', readiness)
        self.assertIn('alerting', readiness)
        self.assertIn('self_heal', readiness)
        self.assertGreaterEqual(readiness['score'], 0)
        self.assertLessEqual(readiness['score'], 100)
        self.assertTrue(any(check['name'] == 'fresh_user_signals' for check in readiness['checks']))

    def test_readiness_persists_daily_history_snapshot(self):
        response = self.client.get(reverse('api_system_readiness'))
        self.assertEqual(response.status_code, 200)

        config = AutoConfiguration.objects.filter(
            user=self.user,
            category='system_health',
            parameter_name='daily_readiness_snapshots',
        ).first()
        self.assertIsNotNone(config)
        self.assertTrue(isinstance(config.parameter_value, list))
        self.assertGreaterEqual(len(config.parameter_value), 1)

    def test_self_heal_endpoint_executes_when_runtime_idle(self):
        with patch('emotion_detection.api_views.learning_manager') as manager:
            manager.is_running = False
            manager.start_learning.return_value = None

            with patch.object(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0', create=True), \
                 patch.object(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/1', create=True):
                response = self.client.post(reverse('api_system_self_heal'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertTrue(any(action['action'] == 'start_learning_manager' for action in payload['actions']))

    def test_self_heal_requires_post(self):
        response = self.client.get(reverse('api_system_self_heal'))
        self.assertEqual(response.status_code, 405)


    def test_self_improve_requires_post(self):
        response = self.client.get(reverse('api_system_self_improve'))
        self.assertEqual(response.status_code, 405)

    def test_self_improve_creates_history_entry(self):
        response = self.client.post(reverse('api_system_self_improve'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('self_improvement', payload)

        config = AutoConfiguration.objects.filter(
            user=self.user,
            category='system_health',
            parameter_name='self_improvement_history',
        ).first()
        self.assertIsNotNone(config)
        self.assertTrue(isinstance(config.parameter_value, list))
        self.assertGreaterEqual(len(config.parameter_value), 1)
