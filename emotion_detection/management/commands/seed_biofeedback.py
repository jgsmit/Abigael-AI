"""
Management command to seed sample biofeedback data for testing.

Usage:
    python manage.py seed_biofeedback [--days 7]
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from datetime import timedelta
import random

from emotion_detection.models import (
    BiofeedbackDevice,
    HeartRateRecord,
    SleepRecord,
    ActivityRecord,
    StressRecord,
    DailyBiofeedbackSummary,
)


class Command(BaseCommand):
    help = 'Seed sample biofeedback data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of data to generate (default: 7)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to seed data for (default: all users with companions)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        username = options.get('user')
        
        if username:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {username} not found'))
                return
        else:
            # Get all users with companion profiles
            from emotion_detection.models import CompanionProfile
            users = User.objects.filter(companion_profile__isnull=False).distinct()
        
        self.stdout.write(f"Seeding biofeedback data for {users.count()} user(s) - {days} days")
        
        for user in users:
            self._seed_for_user(user, days)
        
        self.stdout.write(self.style.SUCCESS('✓ Biofeedback seeding complete'))
    
    def _seed_for_user(self, user, days):
        """Seed biofeedback data for a specific user."""
        self.stdout.write(f"  Seeding for {user.username}...")
        
        # Create or get device
        device, created = BiofeedbackDevice.objects.get_or_create(
            user=user,
            device_id=f'fitbit_{user.id}',
            defaults={
                'device_name': 'Fitbit Sense',
                'device_type': 'fitbit',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(f"    Created device: {device.device_name}")
        
        # Generate historical data
        now = timezone.now()
        
        for day_offset in range(days):
            target_date = now.date() - timedelta(days=day_offset)
            day_start = timezone.make_aware(
                timezone.datetime.combine(target_date, timezone.datetime.min.time())
            )
            
            # Generate heart rate records (hourly)
            base_hr = random.choice([65, 70, 75, 80])
            for hour in range(24):
                timestamp = day_start + timedelta(hours=hour)
                
                # Vary HR throughout day
                if 23 <= hour or hour < 7:  # Night (lower HR)
                    hr = base_hr - random.randint(5, 15)
                elif 12 <= hour < 14:  # Midday spike
                    hr = base_hr + random.randint(10, 20)
                else:
                    hr = base_hr + random.randint(-5, 10)
                
                HeartRateRecord.objects.get_or_create(
                    device=device,
                    timestamp=timestamp,
                    defaults={
                        'heart_rate': max(50, min(130, hr)),
                        'heart_rate_variability': random.uniform(20, 80),
                        'activity_type': 'resting' if 23 <= hour or hour < 7 else 'active',
                    }
                )
            
            # Generate sleep record
            sleep_start = day_start - timedelta(hours=8)
            sleep_quality = random.randint(60, 95)
            
            SleepRecord.objects.get_or_create(
                device=device,
                sleep_date=target_date,
                defaults={
                    'bedtime': sleep_start,
                    'wake_time': day_start,
                    'duration_hours': 8.0,
                    'sleep_quality': sleep_quality,
                    'time_in_deep_sleep': random.uniform(60, 120),
                    'time_in_light_sleep': random.uniform(180, 240),
                    'time_in_rem_sleep': random.uniform(90, 150),
                }
            )
            
            # Generate activity record
            active_minutes = random.randint(20, 60) if random.random() > 0.2 else 5
            ActivityRecord.objects.get_or_create(
                device=device,
                date=target_date,
                defaults={
                    'steps': random.randint(3000, 15000),
                    'calories_burned': random.uniform(1500, 2500),
                    'active_minutes_zone1': random.randint(10, 30),
                    'active_minutes_zone2': max(0, active_minutes - 20),
                }
            )
            
            # Generate stress records (4x per day)
            base_stress = random.randint(30, 70)
            for period in range(4):
                stress_time = day_start + timedelta(hours=period * 6)
                stress_level = base_stress + random.randint(-20, 20)
                
                StressRecord.objects.get_or_create(
                    device=device,
                    timestamp=stress_time,
                    defaults={
                        'stress_level': max(0, min(100, stress_level)),
                    }
                )
        
        # Generate daily summaries
        for day_offset in range(days):
            target_date = now.date() - timedelta(days=day_offset)
            
            hr_records = HeartRateRecord.objects.filter(
                device=device,
                timestamp__date=target_date
            )
            
            summary, created = DailyBiofeedbackSummary.objects.get_or_create(
                user=user,
                date=target_date,
                defaults={
                    'avg_heart_rate': hr_records.aggregate(models.Avg('heart_rate')).get('heart_rate__avg', 70),
                    'sleep_duration_hours': random.uniform(6.5, 9.0),
                    'sleep_quality': random.randint(60, 95),
                    'steps': random.randint(3000, 15000),
                    'stress_level': random.randint(30, 70),
                    'energy_level': random.randint(40, 85),
                }
            )
        
        self.stdout.write(f"    ✓ Generated {days} days of biofeedback data")
