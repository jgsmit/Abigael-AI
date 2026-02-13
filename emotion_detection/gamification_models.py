"""
Habit and Gamification Models

Tracks user engagement, streaks, achievements, and rewards to encourage
consistent use of the Abigael platform and positive behavioral change.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta


class UserStreak(models.Model):
    """Tracks user engagement streaks."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='engagement_streak')
    
    # Current streak
    current_streak_count = models.IntegerField(default=0, help_text="Days in current streak")
    current_streak_start = models.DateField(null=True, blank=True)
    
    # Best streak
    longest_streak_count = models.IntegerField(default=0, help_text="Longest streak ever")
    longest_streak_start = models.DateField(null=True, blank=True)
    longest_streak_end = models.DateField(null=True, blank=True)
    
    # Engagement tracking
    days_engaged = models.IntegerField(default=0, help_text="Total days engaged (may not be consecutive)")
    last_engagement_date = models.DateField(null=True, blank=True)
    
    # Streak-related metrics
    streak_lost_count = models.IntegerField(default=0, help_text="Number of times streak was broken")
    
    class Meta:
        verbose_name_plural = "User Streaks"
    
    def __str__(self):
        return f"{self.user.username} - {self.current_streak_count} day streak"
    
    def update_engagement(self):
        """
        Called when user engages with app (journal, intervention, etc).
        Updates streak counts.
        """
        today = timezone.now().date()
        
        if self.last_engagement_date is None:
            # First engagement ever
            self.current_streak_count = 1
            self.current_streak_start = today
            self.longest_streak_count = 1
            self.longest_streak_start = today
            self.days_engaged = 1
        elif self.last_engagement_date == today:
            # Already engaged today, don't update
            return
        elif self.last_engagement_date == today - timedelta(days=1):
            # Consecutive day, extend streak
            self.current_streak_count += 1
            if self.current_streak_count > self.longest_streak_count:
                self.longest_streak_count = self.current_streak_count
                self.longest_streak_start = self.current_streak_start
                self.longest_streak_end = today
            self.days_engaged += 1
        else:
            # Streak broken, start new one
            if self.current_streak_count > 0:
                self.streak_lost_count += 1
            self.current_streak_count = 1
            self.current_streak_start = today
            self.days_engaged += 1
        
        self.last_engagement_date = today
        self.save()


class Badge(models.Model):
    """Achievement badges for milestones and accomplishments."""
    # Badge definition
    code = models.CharField(max_length=50, unique=True)  # e.g., 'streak_7_days'
    name = models.CharField(max_length=100)
    description = models.TextField()
    badge_type = models.CharField(max_length=20, choices=[
        ('streak', 'Streak Achievement'),
        ('emotion', 'Emotion Improvement'),
        ('engagement', 'Engagement Milestone'),
        ('intervention', 'Intervention Success'),
        ('special', 'Special Achievement'),
    ])
    
    # Display
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    color = models.CharField(max_length=20, blank=True, help_text="Badge color (primary, success, warning, etc)")
    
    # Requirements
    requirements = models.JSONField(default=dict, help_text='{"streak_days": 7, "mood_improvement": 0.3}')
    
    # Reward
    points_earned = models.IntegerField(default=10, help_text="Points user gets when they earn this badge")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name}"
    
    def check_eligibility(self, user) -> dict:
        """
        Check if user qualifies for this badge.
        
        Returns:
            {
                'eligible': bool,
                'current_value': float (for progress bars),
                'required_value': float,
                'progress_percentage': 0-100
            }
        """
        reqs = self.requirements or {}
        result = {
            'eligible': True,
            'current_value': 0,
            'required_value': 0,
            'progress_percentage': 0,
        }
        
        # Check streak requirement
        if 'streak_days' in reqs:
            streak = user.engagement_streak
            result['current_value'] = streak.current_streak_count
            result['required_value'] = reqs['streak_days']
            if result['current_value'] < result['required_value']:
                result['eligible'] = False
                result['progress_percentage'] = int((result['current_value'] / result['required_value']) * 100)
        
        # Check mood improvement requirement
        elif 'mood_improvement' in reqs:
            # Compare mood from past 7 days to previous 7 days
            from emotion_detection.models import JournalEntry
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            current_week_entries = JournalEntry.objects.filter(
                user=user,
                entry_date__gte=week_ago
            ).aggregate(avg_intensity=models.Avg('emotion_intensity'))
            
            previous_week_entries = JournalEntry.objects.filter(
                user=user,
                entry_date__range=[two_weeks_ago, week_ago]
            ).aggregate(avg_intensity=models.Avg('emotion_intensity'))
            
            current_avg = current_week_entries['avg_intensity'] or 0.5
            previous_avg = previous_week_entries['avg_intensity'] or 0.5
            
            improvement = previous_avg - current_avg  # Lower intensity = better
            result['current_value'] = improvement
            result['required_value'] = reqs['mood_improvement']
            if improvement < reqs['mood_improvement']:
                result['eligible'] = False
                result['progress_percentage'] = int((improvement / reqs['mood_improvement']) * 100)
        
        # Check intervention completion requirement
        elif 'interventions_completed' in reqs:
            from emotion_detection.models import UserIntervention
            completed = UserIntervention.objects.filter(
                user=user,
                completed=True,
                completed_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            result['current_value'] = completed
            result['required_value'] = reqs['interventions_completed']
            if completed < reqs['interventions_completed']:
                result['eligible'] = False
                result['progress_percentage'] = int((completed / reqs['interventions_completed']) * 100)
        
        return result


class UserBadge(models.Model):
    """Badge instance earned by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    
    # Earned timestamp
    earned_at = models.DateTimeField(auto_now_add=True)
    
    # Display
    is_displayed = models.BooleanField(default=True, help_text="Show in public profile")
    
    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class UserReward(models.Model):
    """Reward points and redemption tracking."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rewards')
    
    # Points system
    total_points = models.IntegerField(default=0)
    available_points = models.IntegerField(default=0)
    points_spent = models.IntegerField(default=0)
    
    # Achievements
    badges_earned = models.IntegerField(default=0)
    
    # Tier/Level
    REWARD_TIERS = [
        ('bronze', 'Bronze - Beginner'),
        ('silver', 'Silver - Consistent'),
        ('gold', 'Gold - Dedicated'),
        ('platinum', 'Platinum - Master'),
    ]
    current_tier = models.CharField(max_length=20, choices=REWARD_TIERS, default='bronze')
    tier_progress = models.IntegerField(default=0, help_text="0-100 progress to next tier")
    
    class Meta:
        verbose_name_plural = "User Rewards"
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} points ({self.current_tier})"
    
    def add_points(self, amount, reason=""):
        """Award points to user."""
        self.total_points += amount
        self.available_points += amount
        self.save()
        
        # Create point record
        PointTransaction.objects.create(
            user=self.user,
            amount=amount,
            transaction_type='earned',
            reason=reason,
        )
        
        # Check for tier upgrade
        self.check_tier_upgrade()
    
    def spend_points(self, amount, reason=""):
        """Spend points on a reward."""
        if self.available_points < amount:
            raise ValueError("Not enough points available")
        
        self.available_points -= amount
        self.points_spent += amount
        self.save()
        
        PointTransaction.objects.create(
            user=self.user,
            amount=amount,
            transaction_type='spent',
            reason=reason,
        )
    
    def check_tier_upgrade(self):
        """Check if user qualifies for tier upgrade."""
        tier_thresholds = {
            'bronze': 0,
            'silver': 100,
            'gold': 500,
            'platinum': 1500,
        }
        
        if self.total_points >= tier_thresholds.get('platinum', float('inf')):
            self.current_tier = 'platinum'
        elif self.total_points >= tier_thresholds.get('gold', 0):
            self.current_tier = 'gold'
        elif self.total_points >= tier_thresholds.get('silver', 0):
            self.current_tier = 'silver'
        else:
            self.current_tier = 'bronze'
        
        self.save()


class PointTransaction(models.Model):
    """Individual point transaction record."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=[
        ('earned', 'Earned'),
        ('spent', 'Spent'),
        ('bonus', 'Bonus'),
        ('adjustment', 'Adjustment'),
    ])
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.amount} points"


class LeaderboardEntry(models.Model):
    """Optional leaderboard for community engagement."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='leaderboard_entry')
    
    # Ranking
    rank = models.IntegerField(default=0)
    score = models.IntegerField(default=0, help_text="Calculated from points + streaks + badges")
    
    # Visibility
    is_public = models.BooleanField(default=False, help_text="Show in leaderboard")
    anonymized = models.BooleanField(default=False, help_text="Hide real name, show initials")
    
    # Leaderboard period
    period = models.CharField(max_length=20, default='all_time', choices=[
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('all_time', 'All Time'),
    ])
    
    # Stats
    streak_rank = models.IntegerField(null=True, blank=True)
    points_rank = models.IntegerField(null=True, blank=True)
    badges_rank = models.IntegerField(null=True, blank=True)
    
    # Tracking
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['rank']
    
    def __str__(self):
        return f"#{self.rank} {self.user.username|default:'Anonymous'} - {self.score} points"
    
    @classmethod
    def recalculate_leaderboard(cls):
        """Recalculate all leaderboard rankings."""
        entries = cls.objects.filter(is_public=True).order_by('-score')
        for rank, entry in enumerate(entries, 1):
            entry.rank = rank
            entry.save()


class RewardOption(models.Model):
    """Available rewards users can redeem points for."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=[
        ('feature', 'Feature Unlock'),
        ('content', 'Premium Content'),
        ('customization', 'Customization'),
        ('therapy', 'Therapy Session'),
    ])
    
    cost_points = models.IntegerField(help_text="Points required to redeem")
    limit_per_user = models.IntegerField(null=True, blank=True, help_text="Max redemptions per user")
    
    icon = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to='rewards/', null=True, blank=True)
    
    # Availability
    is_active = models.BooleanField(default=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['cost_points']
    
    def __str__(self):
        return f"{self.name} ({self.cost_points} pts)"


class UserRedemption(models.Model):
    """Track user redemptions of rewards."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='redemptions')
    reward = models.ForeignKey(RewardOption, on_delete=models.CASCADE)
    
    points_spent = models.IntegerField()
    redeemed_at = models.DateTimeField(auto_now_add=True)
    
    # Fulfillment
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('expired', 'Expired'),
    ], default='pending')
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, help_text="Admin notes for fulfillment")
    
    class Meta:
        ordering = ['-redeemed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.reward.name}"
