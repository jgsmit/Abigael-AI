from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed sample intervention rules and templates'

    def handle(self, *args, **options):
        try:
            from emotion_detection.intervention_models import InterventionRule, InterventionContent, InterventionTemplate

            # Sample rules
            rules = [
                {
                    'name': 'Calm Breathing for Stress',
                    'description': 'Guide user through a quick breathing exercise.',
                    'trigger_type': 'stress_level',
                    'trigger_condition': {'threshold': 0.7},
                    'intervention_type': 'breathing',
                    'max_daily': 3,
                    'cooldown_minutes': 60,
                    'priority': 10,
                    'is_active': True,
                    'content': [
                        {
                            'title': 'Box Breathing (4-4-4-4)',
                            'description': 'A simple breathing technique to calm anxiety.',
                            'instructions': '1. Inhale for 4 counts\n2. Hold for 4 counts\n3. Exhale for 4 counts\n4. Hold for 4 counts\n5. Repeat 5 times',
                            'duration_seconds': 180,
                            'difficulty': 'easy'
                        }
                    ]
                },
                {
                    'name': 'Gratitude Prompt for Sadness',
                    'description': 'Encourage gratitude reflection when mood is low.',
                    'trigger_type': 'emotion',
                    'trigger_condition': {'emotion': 'sad', 'intensity_min': 0.5},
                    'intervention_type': 'gratitude',
                    'max_daily': 2,
                    'cooldown_minutes': 120,
                    'priority': 8,
                    'is_active': True,
                    'content': [
                        {
                            'title': 'Three Good Things',
                            'description': 'Reflect on three positive moments from today.',
                            'instructions': 'Think of three good things that happened today, no matter how small. Write them down if you can.',
                            'duration_seconds': 300,
                            'difficulty': 'easy'
                        }
                    ]
                },
                {
                    'name': 'Movement Break for Lethargy',
                    'description': 'Suggest a quick stretch or movement when inactive.',
                    'trigger_type': 'no_interaction',
                    'trigger_condition': {'hours': 8},
                    'intervention_type': 'movement',
                    'max_daily': 5,
                    'cooldown_minutes': 180,
                    'time_windows': [{'start': '09:00', 'end': '20:00'}],
                    'priority': 5,
                    'is_active': True,
                    'content': [
                        {
                            'title': '5-Minute Stretch Routine',
                            'description': 'A quick full-body stretch.',
                            'instructions': '1. Neck rolls (30 sec)\n2. Shoulder rolls (30 sec)\n3. Forward fold (1 min)\n4. Side stretches (1 min)\n5. Hip circles (1 min)',
                            'duration_seconds': 300,
                            'difficulty': 'easy'
                        }
                    ]
                }
            ]

            for rule_data in rules:
                content_list = rule_data.pop('content', [])
                rule, created = InterventionRule.objects.get_or_create(name=rule_data['name'], defaults=rule_data)
                
                for content_data in content_list:
                    InterventionContent.objects.get_or_create(
                        rule=rule,
                        title=content_data['title'],
                        defaults=content_data
                    )

            # Sample templates
            templates = [
                {
                    'name': 'Mental Health Support',
                    'description': 'Breathing, grounding, and mindfulness interventions.',
                    'category': 'mental_health',
                    'is_public': True,
                    'default_rule_config': {
                        'trigger_type': 'stress_level',
                        'trigger_condition': {'threshold': 0.7},
                        'intervention_type': 'breathing',
                        'max_daily': 3,
                        'cooldown_minutes': 60
                    },
                    'default_content_list': [
                        {
                            'title': 'Calm Breathing',
                            'description': 'Guided breathing exercise.',
                            'instructions': 'Breathe in for 4, hold for 4, out for 4.',
                            'duration_seconds': 180,
                            'difficulty': 'easy'
                        }
                    ]
                }
            ]

            for template_data in templates:
                InterventionTemplate.objects.get_or_create(name=template_data['name'], defaults=template_data)

            self.stdout.write(self.style.SUCCESS('Sample interventions seeded successfully.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding interventions: {e}'))
