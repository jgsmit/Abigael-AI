from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from emotion_detection.companion_models import Persona, PersonaVariant, CompanionProfile


class PersonaTests(TestCase):
    def setUp(self):
        # Create staff user
        self.staff = User.objects.create_user('admin', 'admin@example.com', 'pass')
        self.staff.is_staff = True
        self.staff.save()

        # Create normal user
        self.user = User.objects.create_user('alice', 'alice@example.com', 'pass')

        # Create sample persona and variant
        self.persona = Persona.objects.create(
            name='Test Persona',
            description='A test persona',
            traits={'default_tone': 'casual'},
            default_tone='casual',
            default_voice='friendly_warm',
            is_public=True
        )

        self.variant = PersonaVariant.objects.create(
            persona=self.persona,
            name='Variant A',
            overrides={'communication_tone': 'calm'},
            is_active=True
        )

        # Create client
        self.client = Client()

    def test_persona_variants_json_staff(self):
        self.client.login(username='admin', password='pass')
        url = reverse('persona_variants_json', args=[self.persona.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('variants', data)
        self.assertTrue(any(v['id'] == self.variant.id for v in data['variants']))
        self.assertIn('create_url', data)

    def test_persona_variants_json_user(self):
        self.client.login(username='alice', password='pass')
        url = reverse('persona_variants_json', args=[self.persona.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('variants', data)
        # Non-staff should still see variants but no edit/create urls
        self.assertTrue(all('edit_url' not in v for v in data['variants']))

    def test_profile_select_and_variant_link(self):
        self.client.login(username='alice', password='pass')
        # Ensure profile can be created and variant linked
        profile, _ = CompanionProfile.objects.get_or_create(user=self.user)
        profile.selected_persona = self.persona
        profile.selected_persona_variant = self.variant
        profile.save()

        # Access persona select page and ensure serverSaved variant appears in context
        url = reverse('persona_select')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Select Your Companion Persona')
