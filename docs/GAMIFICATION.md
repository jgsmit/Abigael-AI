# Gamification & Habit Tracking System

## Overview

The Abigael Gamification System enhances user engagement through habit tracking, achievement unlocking, reward redemption, and optional leaderboards. It motivates consistent app usage and positive behavioral change through streaks, badges, points, and tier progression.

## Architecture

### Core Models

1. **UserStreak** - Engagement streak tracking
   - Current consecutive days engaged
   - Longest streak ever achieved
   - Total days engaged (non-consecutive)
   - Days since last engagement

2. **Badge** - Achievement definitions
   - Streak badges: 7-day, 14-day, 30-day, 100-day streaks
   - Engagement badges: Journal milestones (10, 50, 100 entries)
   - Emotion badges: Mood improvement achievements
   - Intervention badges: Intervention completion milestones
   - Special badges: Time-based (early bird, night owl)

3. **UserBadge** - Badge instances earned by users
   - Links user to earned badge
   - Timestamp of earning
   - Display preference (public/private)

4. **UserReward** - Points system and tier progression
   - Total points earned (all-time)
   - Available points (unspent)
   - Points spent (lifetime tracking)
   - Current tier: Bronze → Silver → Gold → Platinum
   - Tier progress indicator (0-100)

5. **PointTransaction** - Individual point transactions
   - Tracks all points received and spent
   - Reason for transaction
   - Type: earned, spent, bonus, adjustment

6. **LeaderboardEntry** - Optional community leaderboard
   - User rank and score
   - Public/private visibility
   - Name anonymization option
   - Period-based rankings (weekly, monthly, all-time)

7. **RewardOption** - Available rewards for redemption
   - Point cost
   - Category: feature unlock, premium content, customization, therapy session
   - Availability windows (time-limited rewards)
   - Per-user redemption limit

8. **UserRedemption** - Reward redemption tracking
   - Links user to redeemed reward
   - Points spent
   - Fulfillment status (pending, fulfilled, expired)
   - Admin notes for manual fulfillment

## Engagement Loop

```
User Action
  ↓
update_user_engagement_streak(user)     [Updates streak, last_engagement_date]
  ↓
award_points_for_action(user, action)   [Points: 10, 15, 20, etc]
  ↓
check_milestone_badges(user)             [Auto-unlock badges if eligible]
  ↓
Gamification Dashboard Updated
```

## Point System

### Points Awarded

| Action | Points | Trigger |
|--------|--------|---------|
| Daily engagement | Automatic | First action of day |
| Journal entry created | 10 | OneToOne |
| Intervention completed | 15 | When marked complete |
| Intervention rated helpful | +5 bonus | rating > 3/5 |
| Badge earned | Varies | 10-150 depending on badge |
| Mood improvement | 20 | Weekly mood up 30%+ |
| Streak milestones | 5 × days | Every X days |

### Points Spent

| Reward | Cost | Category |
|--------|------|----------|
| Meditation pack | 50 | Content |
| Avatar customization | 30 | Customization |
| Premium journaling | 75 | Feature |
| Extended music library | 60 | Content |
| Advanced personalization | 100 | Feature |
| Therapist session | 200 | Therapy |

### Tier Structure

| Tier | Points | Benefits |
|------|--------|----------|
| Bronze | 0-99 | Base access |
| Silver | 100-499 | 10% point multiplier |
| Gold | 500-1499 | 20% multiplier + badge display |
| Platinum | 1500+ | 25% multiplier + leaderboard feature |

## Badge System

### Auto-Unlocking Badges

Badges automatically unlock when eligibility requirements are met:

```python
badge.check_eligibility(user) → {
    'eligible': bool,
    'current_value': float,
    'required_value': float,
    'progress_percentage': 0-100
}
```

### Badge Types & Requirements

**Streak Badges**
- 7-Day Streak: `current_streak_count >= 7`
- 14-Day Streak: `current_streak_count >= 14`
- 30-Day Streak: `current_streak_count >= 30`
- 100-Day Streak: `current_streak_count >= 100`

**Engagement Badges**
- First Steps: 1 journal entry
- Journaling Habit: 10 journal entries
- Deep Reflector: 50 journal entries
- Century Club: 100 journal entries

**Emotion Badges**
- Feeling Better: Mood improved 30% (week-over-week)
- Resilient: Maintained mood despite adversity

**Intervention Badges**
- Intervention Champion: 10 completed interventions
- Intervention Master: 25 completed interventions

**Special Badges**
- Early Bird: Complete intervention before 8 AM
- Night Owl Wellness: Complete intervention after 9 PM
- Social Butterfly: Complete social-focused intervention

## Streak Mechanics

### Streak Rules
1. First engagement: Start streak at 1
2. Consecutive day: Extend streak
3. Same day re-engagement: No streak extension
4. Skip day: Streak broken, start new one
5. Longest streak: Tracked separately for hall of fame

### Streak Rewards
- Milestone bonuses at 7, 14, 30, 60, 100, 365 days
- Progressive point multipliers
- Special badges at major milestones

## Leaderboard System

### Visibility Control
- Opt-in leaderboard (LeaderboardEntry.is_public)
- Optional anonymization (initials only)
- Period-based rankings: weekly, monthly, all-time

### Ranking Calculation
```python
score = (total_points * 0.5) + (current_streak_count * 10) + (badges_earned * 25)
```

### Display
- Top 100 users per period
- User's rank highlighted if public
- Filters by category: points, streak, badges

## Views & API Endpoints

### User-Facing Views

**Dashboard** (`/gamification/`)
- Quick stats: Streak, Points, Tier, Recent badges
- In-progress badge eligibility
- Recent point transactions
- Links to deeper views

**Badges** (`/gamification/badges/`)
- All available badges with eligibility
- Earned badges with unlock date
- Progress toward in-progress badges
- Filter by badge type

**Rewards Shop** (`/gamification/rewards/`)
- Filterable reward catalog
- Point cost and redemption limit display
- Redemption form with validation
- User's current point balance

**Streak Detail** (`/gamification/streak/`)
- Current and longest streak visualization
- Upcoming milestone rewards
- Historical streak data
- Tips for maintaining streaks

**Leaderboard** (`/gamification/leaderboard/`)
- Top 100 public players
- Period selector (week, month, all-time)
- User's rank if participating
- Anonymized names/initials

**Profile Stats** (`/gamification/profile/`)
- Comprehensive user achievements
- Lifetime statistics (journals, interventions)
- Point transaction history
- Tier progression timeline

### API Endpoints

```
GET /api/gamification/stats/
    Returns: { streak, rewards, badges counts }

GET /api/gamification/badges/progress/
    Returns: [{ badge_name, progress%, current, required }]
    (Only badges in-progress, for progress tracking)

POST /gamification/rewards/<id>/redeem/
    Redeems reward if user has sufficient points
    Returns: { success, new_balance }
```

## Integration Points

### With InterventionEngine
- Points awarded when UserIntervention.completed = True
- Bonus points if was_helpful = True
- Auto-check for intervention-related badges

### With JournalEntry
- Points awarded on entry creation
- Mood improvement badges trigger on journal data
- Emotion-based badge eligibility checks

### With CompanionProfile
- Streak updates on any app engagement
- Tier affects companion personality/features

## Internal Functions

### `update_user_engagement_streak(user)`
Called when user engages with app (any significant action).
Updates or creates UserStreak and calls `streak.update_engagement()`.

### `award_badge_if_eligible(user, badge_code)`
Checks if user qualifies for specific badge.
Auto-creates UserBadge and awards points if eligible.

### `award_points_for_action(user, action_type, amount=None)`
Awards points based on action type:
- `journal_entry`: 10 pts
- `intervention_completed`: 15 pts
- `intervention_rated_helpful`: +5 bonus
- `mood_improvement`: 20 pts

### `check_milestone_badges(user)`
Scans all milestone badges (streak, engagement, emotion).
Auto-unlocks any badges user now qualifies for.

## Gamification Logic Flow

```
1. User does action (journal, intervention)
   ↓
2. View calls update_user_engagement_streak(user)
   ↓
3. Streak updated, points awarded via award_points_for_action()
   ↓
4. check_milestone_badges(user) scans all badges
   ↓
5. For each badge: check_eligibility() → if eligible: award_badge_if_eligible()
   ↓
6. Badge unlocked + points awarded + UserBadge created
   ↓
7. User sees achievement on dashboard
```

## Forms

- **LeaderboardVisibilityForm**: Toggle leaderboard visibility, anonymization
- **RewardRedemptionForm**: Select reward to redeem (RadioSelect)

## Templates

- `gamification/dashboard.html`: Main dashboard with quick stats
- `gamification/badges.html`: All badges with progress bars
- `gamification/reward_shop.html`: Reward catalog and redemption
- `gamification/streak_detail.html`: Detailed streak tracking
- `gamification/leaderboard.html`: Public leaderboards
- `gamification/profile_stats.html`: Comprehensive user stats

## Seeding & Testing

### Seed Sample Data
```bash
python manage.py seed_gamification
```

Creates:
- 10 badge templates
- 6 reward options
- User gamification records (streaks, rewards, leaderboard entries)
- All users given 100 starting points

## Security Considerations

1. **Point Manipulation**: Validate all point transactions server-side
2. **Badge Spoofing**: Verify eligibility before awarding badges
3. **Leaderboard Gaming**: Rate-limit point earning, detect anomalies
4. **Redemption Limits**: Enforce per-user redemption caps
5. **Admin Override**: Allow admins to adjust points/badges for support

## Future Enhancements

1. **Social Features**
   - Friend streaks and challenges
   - Badge sharing and reactions
   - Team leaderboards

2. **Dynamic Rewards**
   - Time-limited event rewards
   - Seasonal achievement passes
   - Limited-edition badges

3. **AI-Powered Insights**
   - Predictive streaks ("You'll reach 30 days in 3 days!")
   - Personalized challenges
   - Habit recommendations

4. **Mobile Push**
   - Streak reminders (notifications before streak breaks)
   - Badge achievement notifications
   - Leaderboard rank changes

5. **Integration**
   - Therapy integration (therapist views patient progress)
   - Wearable integration (health achievements from biofeedback)
   - Social media sharing (selective badge promotion)

## Testing Checklist

- [ ] Streak updates on each engagement
- [ ] Points awarded and deducted correctly
- [ ] Badges unlock automatically at thresholds
- [ ] Tier upgrades on point milestones
- [ ] Leaderboard calculation accurate
- [ ] Reward redemption deducts points
- [ ] Redemption limits enforced
- [ ] Anonymization hides user details on leaderboard
- [ ] API endpoints return correct data
- [ ] Admin can manually adjust points/badges

## Code References

- Models: [gamification_models.py](gamification_models.py)
- Views: [gamification_views.py](gamification_views.py)
- Forms: [forms.py](forms.py#L125-145)
- URLs: [urls.py](urls.py#L70-82)
- Templates: `templates/gamification/` (dashboard, badges, rewards, etc.)  
- Seeding: [seed_gamification.py](management/commands/seed_gamification.py)

---

## Integration Checklist

To integrate gamification with other systems:

1. **In InterventionEngine**: Call `award_points_for_action(user, 'intervention_completed', 15)`
2. **In JournalEntry creation**: Call `update_user_engagement_streak(user)` and `award_points_for_action(user, 'journal_entry', 10)`
3. **In CompanionProfile**: Check user's tier for feature unlocks
4. **In Templates**: Display `user.rewards` tier badge and streak count
5. **In Admin**: Add gamification stats to user detail page

