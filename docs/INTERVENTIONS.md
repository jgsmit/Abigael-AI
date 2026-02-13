# Micro-Intervention System (Abigael AI)

## Overview

The micro-intervention engine delivers contextual, brief supportive tasks ("nudges") to help users manage emotions and behavior through:
- **Rules**: Define when and what type of intervention to trigger
- **Content**: Reusable task libraries (breathing, gratitude, movement, etc.)
- **Scheduling**: Time-based and emotion-based triggers with cooldowns
- **Feedback**: Track completion, ratings, and effectiveness

## Architecture

### Models

- **InterventionRule**: Conditions and scheduling for triggering interventions
  - `trigger_type`: emotion, time_of_day, pattern, stress_level, no_interaction, milestone
  - `intervention_type`: breathing, cbt, gratitude, movement, music, journal, social, rest, etc.
  - `max_daily`: Max triggers per day
  - `cooldown_minutes`: Minimum time between triggers
  - `time_windows`: Optional activity windows (e.g., 9am-10pm)
  - `success_rate`: A/B testing parameter (0-1)

- **InterventionContent**: Task content and instructions
  - Linked to a rule
  - Includes title, instructions, media URLs
  - Tracks completion rate and user ratings

- **UserIntervention**: User-specific intervention instance
  - Tracks triggered, delivered, completed, and feedback
  - Records user rating and helpfulness
  - Indexed for fast queries

- **InterventionTemplate**: Pre-built intervention packs for quick deployment
  - Categories: mental health, physical, social, productivity, leisure
  - Contains default rule config and content list

### Engine

`InterventionEngine` evaluates user state and triggers interventions:

1. **evaluate_user(user)**: Main entry point
   - Gathers user emotional/behavioral state
   - Iterates through active rules
   - Returns list of triggered interventions

2. **_get_user_state(user)**: Collects current state
   - Latest emotion from journal entry
   - Stress level (emotion intensity)
   - Inactivity status
   - Recent crisis detection

3. **_should_trigger(user, rule, state)**: Decision logic
   - Checks cooldown against last trigger
   - Enforces daily limits
   - Validates time windows
   - Checks trigger condition match
   - A/B test via random success_rate

4. **complete_intervention(...)**: Record completion and feedback
   - Updates rule success_rate based on was_helpful
   - Stores user rating and feedback

## Usage

### Admin: Create a Rule

1. Navigate to `/emotion_detection/admin/intervention_rules/`
2. Click "New Rule"
3. Set name, trigger type, and condition
4. Choose intervention type and scheduling
5. Add content variants
6. Deploy

### Admin: Deploy a Template

1. Go to `/emotion_detection/admin/intervention_templates/`
2. Select a template
3. Click "Deploy" → Creates rule + content automatically

### User: Receive Interventions

1. Interventions are triggered automatically based on emotion, time, and state
2. User sees them on `/emotion_detection/interventions/`
3. Click "View & Start" to open the intervention
4. Complete the task and rate helpfulness
5. Rating feeds back into rule effectiveness

### Seed Sample Data

```bash
python manage.py seed_interventions
```

Creates sample rules for:
- Stress → Breathing exercise
- Sadness → Gratitude prompt
- Inactivity → Movement break

## API Endpoints

| URL | Method | Purpose |
|-----|--------|---------|
| `/emotion_detection/interventions/` | GET | User dashboard |
| `/emotion_detection/interventions/<id>/` | GET | View intervention detail |
| `/emotion_detection/interventions/<id>/start/` | POST | Mark as started |
| `/emotion_detection/interventions/<id>/complete/` | POST | Mark as completed with rating |
| `/emotion_detection/interventions/<id>/dismiss/` | POST | Dismiss intervention |
| `/emotion_detection/interventions/trigger/` | GET | Manually trigger evaluation |
| `/emotion_detection/admin/intervention_rules/` | GET | List rules (staff only) |
| `/emotion_detection/admin/intervention_templates/` | GET | List templates (staff only) |

## Integration Points

- **CompanionEngine**: Could auto-trigger interventions during conversations
- **CrisisDetection**: High-stress interventions when crisis detected
- **JournalEntry**: Extract emotion/stress to feed state evaluation
- **CeleryTasks**: Schedule periodic intervention evaluation

## Metrics & Tracking

- Completion rate per rule
- Average user rating
- Effectiveness tracking via `was_helpful`
- A/B testing through `success_rate`

## Future Enhancements

- Personalization: Learn user preferences and timing
- Multi-modality: Voice-guided, video, AR
- Social: Group interventions, peer support prompts
- Adaptive: ML model to predict best intervention type per user
