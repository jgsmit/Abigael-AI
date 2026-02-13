from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Seed sample personas and variants for development'

    def handle(self, *args, **options):
        try:
            from emotion_detection.companion_models import Persona, PersonaVariant

            samples = [
                {
                    'name': 'Caring Friend',
                    'description': 'Warm, empathetic companion that listens and comforts.',
                    'traits': {'default_tone': 'casual', 'personality_type': 'caring_friend', 'phrasing': 'warm_supportive'},
                    'is_public': True,
                    'variants': [
                        {'name': 'Warm Casual', 'overrides': {'communication_tone': 'casual', 'default_voice': 'friendly_warm'}},
                        {'name': 'Gentle Calm', 'overrides': {'communication_tone': 'calm', 'default_voice': 'calm'}}
                    ]
                },
                {
                    'name': 'Supportive Mentor',
                    'description': 'Encouraging, structured coach that gives actionable advice.',
                    'traits': {'default_tone': 'professional', 'personality_type': 'supportive_mentor', 'phrasing': 'actionable'},
                    'is_public': True,
                    'variants': [
                        {'name': 'Direct Coach', 'overrides': {'communication_tone': 'professional', 'default_voice': 'professional'}},
                    ]
                }
            ]

            for s in samples:
                p, created = Persona.objects.get_or_create(name=s['name'], defaults={
                    'description': s['description'],
                    'traits': s['traits'],
                    'default_tone': s['traits'].get('default_tone', 'casual'),
                    'default_voice': s['traits'].get('default_voice', 'friendly_warm'),
                    'is_public': s.get('is_public', True)
                })

                for v in s.get('variants', []):
                    PersonaVariant.objects.get_or_create(persona=p, name=v['name'], defaults={'overrides': v.get('overrides', {}), 'is_active': True})

            self.stdout.write(self.style.SUCCESS('Sample personas seeded.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding personas: {e}'))
