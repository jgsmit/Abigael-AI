"""
Gamification views for streaks, badges, points, and leaderboards.

Views:
- Gamification Dashboard: Overview of streaks, badges, points, tier
- Badge List: All badges with eligibility status and unlock progress
- Reward Shop: Available rewards for redemption
- Profile/Stats: Detailed user gamification stats
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone

from .gamification_models import (
    UserStreak,
    Badge,
    UserBadge,
    UserReward,
    PointTransaction,
    LeaderboardEntry,
    RewardOption,
    UserRedemption,
)


@login_required
def gamification_dashboard(request):
    """Main gamification dashboard with streaks, badges, points."""
    # Get or create user records
    streak, _ = UserStreak.objects.get_or_create(user=request.user)
    rewards, _ = UserReward.objects.get_or_create(user=request.user)
    
    # Get recent badges
    recent_badges = UserBadge.objects.filter(user=request.user).order_by('-earned_at')[:5]
    
    # Get point transactions
    recent_transactions = PointTransaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Get nearby badge eligibilities
    all_badges = Badge.objects.filter(is_active=True)
    badge_progress = []
    for badge in all_badges:
        if not UserBadge.objects.filter(user=request.user, badge=badge).exists():
            eligibility = badge.check_eligibility(request.user)
            if eligibility['progress_percentage'] > 0:  # Show badges with progress
                badge_progress.append({
                    'badge': badge,
                    'eligibility': eligibility,
                })
    
    # Sort by progress (closest to earning first)
    badge_progress.sort(key=lambda x: x['eligibility']['progress_percentage'], reverse=True)
    
    context = {
        'streak': streak,
        'rewards': rewards,
        'recent_badges': recent_badges,
        'recent_transactions': recent_transactions,
        'badge_progress': badge_progress[:3],  # Show top 3 in progress
        'earned_badge_count': UserBadge.objects.filter(user=request.user).count(),
    }
    
    return render(request, 'gamification/dashboard.html', context)


@login_required
def badges_view(request):
    """View all available badges with user's progress."""
    all_badges = Badge.objects.filter(is_active=True).order_by('badge_type', 'points_earned')
    
    # Get user's earned badges
    earned_badge_ids = UserBadge.objects.filter(user=request.user).values_list('badge_id', flat=True)
    
    # Build badge list with eligibility
    badge_data = []
    for badge in all_badges:
        earned = badge.id in earned_badge_ids
        eligibility = badge.check_eligibility(request.user) if not earned else None
        
        badge_data.append({
            'badge': badge,
            'earned': earned,
            'earned_at': UserBadge.objects.filter(user=request.user, badge=badge).first(),
            'eligibility': eligibility,
        })
    
    # Group by badge type
    badge_groups = {}
    for bd in badge_data:
        btn = bd['badge'].badge_type
        if btn not in badge_groups:
            badge_groups[btn] = []
        badge_groups[btn].append(bd)
    
    context = {
        'badge_groups': badge_groups,
        'total_available': all_badges.count(),
        'total_earned': UserBadge.objects.filter(user=request.user).count(),
    }
    
    return render(request, 'gamification/badges.html', context)


@login_required
def reward_shop(request):
    """Display available rewards for redemption."""
    now = timezone.now()
    
    # Get available rewards
    rewards = RewardOption.objects.filter(
        is_active=True,
        Q(available_from__isnull=True) | Q(available_from__lte=now),
        Q(available_until__isnull=True) | Q(available_until__gte=now),
    ).order_by('cost_points')
    
    # Filter by category if provided
    category = request.GET.get('category')
    if category:
        rewards = rewards.filter(category=category)
    
    # Get user's reward balance
    user_rewards, _ = UserReward.objects.get_or_create(user=request.user)
    
    # Get user's redemptions
    user_redemptions = UserRedemption.objects.filter(user=request.user)
    
    # Build reward data with redemption count
    reward_data = []
    for reward in rewards:
        redemption_count = user_redemptions.filter(reward=reward).count()
        can_redeem = (
            user_rewards.available_points >= reward.cost_points and
            (reward.limit_per_user is None or redemption_count < reward.limit_per_user)
        )
        
        reward_data.append({
            'reward': reward,
            'can_redeem': can_redeem,
            'redemption_count': redemption_count,
        })
    
    context = {
        'reward_data': reward_data,
        'available_points': user_rewards.available_points,
        'categories': RewardOption.REWARD_TYPES,
    }
    
    return render(request, 'gamification/reward_shop.html', context)


@login_required
@require_http_methods(["POST"])
def redeem_reward(request, reward_id):
    """Redeem a reward with points."""
    reward = get_object_or_404(RewardOption, id=reward_id)
    user_rewards = UserReward.objects.get(user=request.user)
    
    # Check eligibility
    if user_rewards.available_points < reward.cost_points:
        return JsonResponse({'error': 'Insufficient points'}, status=400)
    
    # Check redemption limit
    if reward.limit_per_user:
        redemption_count = UserRedemption.objects.filter(user=request.user, reward=reward).count()
        if redemption_count >= reward.limit_per_user:
            return JsonResponse({'error': 'You have reached the limit for this reward'}, status=400)
    
    # Process redemption
    try:
        user_rewards.spend_points(reward.cost_points, f"Redeemed: {reward.name}")
        
        UserRedemption.objects.create(
            user=request.user,
            reward=reward,
            points_spent=reward.cost_points,
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Successfully redeemed {reward.name}!",
            'new_balance': user_rewards.available_points,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def leaderboard_view(request):
    """Display leaderboard of public players."""
    period = request.GET.get('period', 'all_time')
    
    entries = LeaderboardEntry.objects.filter(
        is_public=True,
        period=period
    ).order_by('rank')[:100]
    
    # Get user's rank
    user_entry = LeaderboardEntry.objects.filter(user=request.user).first()
    
    context = {
        'entries': entries,
        'user_entry': user_entry,
        'available_periods': [
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('all_time', 'All Time'),
        ],
        'selected_period': period,
    }
    
    return render(request, 'gamification/leaderboard.html', context)


@login_required
def streak_detail(request):
    """Detailed view of user's streak progress."""
    streak = UserStreak.objects.get(user=request.user)
    
    # Calculate next milestone rewards
    next_milestones = [7, 14, 30, 60, 100, 365]
    milestone_data = []
    for milestone in next_milestones:
        if streak.current_streak_count < milestone:
            days_remaining = milestone - streak.current_streak_count
            milestone_data.append({
                'days': milestone,
                'days_remaining': days_remaining,
                'points_reward': milestone * 5,  # Reward calculation
            })
    
    context = {
        'streak': streak,
        'milestone_data': milestone_data,
    }
    
    return render(request, 'gamification/streak_detail.html', context)


@login_required
@require_http_methods(["GET"])
def user_stats_api(request):
    """API endpoint for user gamification stats."""
    streak = UserStreak.objects.get(user=request.user)
    rewards = UserReward.objects.get(user=request.user)
    badges = UserBadge.objects.filter(user=request.user).count()
    
    return JsonResponse({
        'streak': {
            'current': streak.current_streak_count,
            'longest': streak.longest_streak_count,
            'days_engaged': streak.days_engaged,
            'last_engagement': streak.last_engagement_date,
        },
        'rewards': {
            'total_points': rewards.total_points,
            'available_points': rewards.available_points,
            'tier': rewards.current_tier,
            'tier_progress': rewards.tier_progress,
        },
        'badges': {
            'earned': badges,
        },
    })


@login_required
@require_http_methods(["GET"])
def badges_progress_api(request):
    """API endpoint showing badge unlock progress."""
    all_badges = Badge.objects.filter(is_active=True)
    earned_badge_ids = set(UserBadge.objects.filter(user=request.user).values_list('badge_id', flat=True))
    
    data = []
    for badge in all_badges:
        if badge.id not in earned_badge_ids:
            eligibility = badge.check_eligibility(request.user)
            if eligibility['progress_percentage'] > 0:
                data.append({
                    'name': badge.name,
                    'progress': eligibility['progress_percentage'],
                    'current': eligibility['current_value'],
                    'required': eligibility['required_value'],
                })
    
    return JsonResponse({
        'in_progress': sorted(data, key=lambda x: x['progress'], reverse=True),
    })


@login_required
def profile_stats(request):
    """Detailed user statistics and achievements page."""
    streak = UserStreak.objects.get(user=request.user)
    rewards = UserReward.objects.get(user=request.user)
    badges = UserBadge.objects.filter(user=request.user).order_by('-earned_at')
    
    # Calculate engagement metrics
    from emotion_detection.models import JournalEntry, UserIntervention
    
    journal_count = JournalEntry.objects.filter(user=request.user).count()
    intervention_count = UserIntervention.objects.filter(user=request.user).count()
    
    # Get point transaction summary
    earned_this_month = PointTransaction.objects.filter(
        user=request.user,
        transaction_type='earned',
        created_at__month=timezone.now().month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'streak': streak,
        'rewards': rewards,
        'badges': badges,
        'journal_count': journal_count,
        'intervention_count': intervention_count,
        'earned_this_month': earned_this_month,
    }
    
    return render(request, 'gamification/profile_stats.html', context)


# ============================================================================
# INTERNAL FUNCTIONS (called by other systems for gamification logic)
# ============================================================================

def update_user_engagement_streak(user):
    """Called when user engages with app (any significant action)."""
    try:
        streak = UserStreak.objects.get(user=user)
        streak.update_engagement()
    except UserStreak.DoesNotExist:
        UserStreak.objects.create(user=user).update_engagement()


def award_badge_if_eligible(user, badge_code):
    """Check if user qualifies for badge and award if needed."""
    try:
        badge = Badge.objects.get(code=badge_code)
        
        # Skip if already earned
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            return None
        
        # Check eligibility
        eligibility = badge.check_eligibility(user)
        
        if eligibility['eligible']:
            user_badge = UserBadge.objects.create(user=user, badge=badge)
            
            # Award points
            rewards = UserReward.objects.get(user=user)
            rewards.add_points(badge.points_earned, f"Badge earned: {badge.name}")
            
            # Increment badge count
            rewards.badges_earned += 1
            rewards.save()
            
            return user_badge
    except Badge.DoesNotExist:
        pass
    
    return None


def award_points_for_action(user, action_type, amount=None, reason=""):
    """Award points based on user action."""
    rewards = UserReward.objects.get(user=user)
    
    # Default point values
    points_map = {
        'journal_entry': 10,
        'intervention_completed': 15,
        'badge_earned': 25,
        'streak_10': 50,
        'streak_30': 100,
        'mood_improvement': 20,
    }
    
    points = amount or points_map.get(action_type, 5)
    rewards.add_points(points, reason or action_type)


def check_milestone_badges(user):
    """Check for milestone-based badges (streak, mood improvement, etc.)"""
    # Streak milestones
    streak = UserStreak.objects.get(user=user)
    streak_milestones = {
        'streak_7_days': 7,
        'streak_14_days': 14,
        'streak_30_days': 30,
        'streak_100_days': 100,
    }
    
    for badge_code, days_required in streak_milestones.items():
        if streak.current_streak_count >= days_required:
            award_badge_if_eligible(user, badge_code)
    
    # Engagement milestones
    from emotion_detection.models import JournalEntry
    journal_count = JournalEntry.objects.filter(user=user).count()
    
    journal_milestones = {
        'first_entry': 1,
        'ten_entries': 10,
        'fifty_entries': 50,
        'hundred_entries': 100,
    }
    
    for badge_code, threshold in journal_milestones.items():
        if journal_count >= threshold:
            award_badge_if_eligible(user, badge_code)
