"""
Management command to seed sample gamification data (badges, rewards) for testing.

Usage:
    python manage.py seed_gamification
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from emotion_detection.gamification_models import (
    Badge,
    RewardOption,
    UserStreak,
    UserReward,
    LeaderboardEntry,
)


class Command(BaseCommand):
    help = 'Seed sample gamification data (badges, rewards)'
    
    def handle(self, *args, **options):
        self.stdout.write("Seeding gamification data...")
        
        # Seed badges
        self._seed_badges()
        
        # Seed rewards
        self._seed_rewards()
        
        # Seed user gamification records
        self._seed_user_records()
        
        self.stdout.write(self.style.SUCCESS('✓ Gamification seeding complete'))
    
    def _seed_badges(self):
        """Create sample badges."""
        badges_data = [
            {
                'code': 'first_entry',
                'name': 'First Steps',
                'description': 'Created your first journal entry',
                'badge_type': 'engagement',
                'icon': '🌱',
                'color': 'success',
                'requirements': {'journal_entries': 1},
                'points_earned': 10,
            },
            {
                'code': 'streak_7_days',
                'name': '7-Day Streak',
                'description': 'Engaged with the app for 7 consecutive days',
                'badge_type': 'streak',
                'icon': '🔥',
                'color': 'warning',
                'requirements': {'streak_days': 7},
                'points_earned': 50,
            },
            {
                'code': 'streak_30_days',
                'name': '30-Day Champion',
                'description': 'Maintained a 30-day engagement streak',
                'badge_type': 'streak',
                'icon': '⭐',
                'color': 'warning',
                'requirements': {'streak_days': 30},
                'points_earned': 150,
            },
            {
                'code': 'ten_entries',
                'name': 'Journaling Habit',
                'description': 'Completed 10 journal entries',
                'badge_type': 'engagement',
                'icon': '📝',
                'color': 'info',
                'requirements': {'journal_entries': 10},
                'points_earned': 30,
            },
            {
                'code': 'fifty_entries',
                'name': 'Deep Reflector',
                'description': 'Completed 50 journal entries',
                'badge_type': 'engagement',
                'icon': '🧠',
                'color': 'info',
                'requirements': {'journal_entries': 50},
                'points_earned': 100,
            },
            {
                'code': 'mood_improvement',
                'name': 'Feeling Better',
                'description': 'Improved your average mood by 30%',
                'badge_type': 'emotion',
                'icon': '😊',
                'color': 'success',
                'requirements': {'mood_improvement': 0.3},
                'points_earned': 75,
            },
            {
                'code': 'interventions_master',
                'name': 'Intervention Master',
                'description': 'Completed 25 interventions',
                'badge_type': 'intervention',
                'icon': '💪',
                'color': 'primary',
                'requirements': {'interventions_completed': 25},
                'points_earned': 80,
            },
            {
                'code': 'consistency',
                'name': 'Consistency is Key',
                'description': 'Logged in for 14 consecutive days',
                'badge_type': 'streak',
                'icon': '✨',
                'color': 'warning',
                'requirements': {'streak_days': 14},
                'points_earned': 80,
            },
            {
                'code': 'early_bird',
                'name': 'Early Bird',
                'description': 'Complete an intervention before 8 AM',
                'badge_type': 'special',
                'icon': '🌅',
                'color': 'info',
                'requirements': {},
                'points_earned': 25,
            },
            {
                'code': 'night_owl',
                'name': 'Night Owl Wellness',
                'description': 'Complete an intervention after 9 PM',
                'badge_type': 'special',
                'icon': '🌙',
                'color': 'info',
                'requirements': {},
                'points_earned': 25,
            },
        ]
        
        created_count = 0
        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                code=badge_data['code'],
                defaults={
                    'name': badge_data['name'],
                    'description': badge_data['description'],
                    'badge_type': badge_data['badge_type'],
                    'icon': badge_data['icon'],
                    'color': badge_data['color'],
                    'requirements': badge_data['requirements'],
                    'points_earned': badge_data['points_earned'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f"  ✓ Created {created_count} badges")
    
    def _seed_rewards(self):
        """Create sample rewards for redemption."""
        rewards_data = [
            {
                'code': 'meditation_pack',
                'name': 'Guided Meditation Pack',
                'category': 'content',
                'cost_points': 50,
                'description': '5 guided meditations by expert instructors',
                'icon': '🧘',
            },
            {
                'code': 'premium_journal',
                'name': 'Premium Journal Features',
                'category': 'feature',
                'cost_points': 75,
                'description': 'Advanced journaling analytics and mood predictions',
                'icon': '📊',
            },
            {
                'code': 'avatar_customization',
                'name': 'Avatar Customization Pack',
                'category': 'customization',
                'cost_points': 30,
                'description': 'Unlock 10 custom avatar appearances',
                'icon': '🎨',
            },
            {
                'code': 'therapy_session',
                'name': 'Therapist Consultation',
                'category': 'therapy',
                'cost_points': 200,
                'description': '30-minute session with licensed therapist',
                'icon': '👨‍⚕️',
            },
            {
                'code': 'music_library',
                'name': 'Extended Music Library',
                'category': 'content',
                'cost_points': 60,
                'description': '100+ curated tracks for mood regulation',
                'icon': '🎵',
            },
            {
                'code': 'personalization',
                'name': 'Advanced Personalization',
                'category': 'feature',
                'cost_points': 100,
                'description': 'Customize AI companion personality and responses',
                'icon': '⚙️',
            },
        ]
        
        created_count = 0
        for reward_data in rewards_data:
            reward, created = RewardOption.objects.get_or_create(
                code=reward_data['code'],
                defaults={
                    'name': reward_data['name'],
                    'description': reward_data['description'],
                    'category': reward_data['category'],
                    'cost_points': reward_data['cost_points'],
                    'icon': reward_data['icon'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f"  ✓ Created {created_count} reward options")
    
    def _seed_user_records(self):
        """Create user gamification records."""
        users = User.objects.filter(is_active=True)
        
        for user in users:
            # Create streak
            UserStreak.objects.get_or_create(user=user)
            
            # Create reward
            UserReward.objects.get_or_create(
                user=user,
                defaults={'total_points': 100, 'available_points': 100}
            )
            
            # Create/update leaderboard entry
            LeaderboardEntry.objects.get_or_create(
                user=user,
                defaults={
                    'rank': 0,
                    'score': 100,
                    'is_public': False,
                    'period': 'all_time',
                }
            )
        
        self.stdout.write(f"  ✓ Set up gamification for {users.count()} users")
