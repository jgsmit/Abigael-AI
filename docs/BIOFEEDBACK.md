# Biofeedback Integration System

## Overview

The Abigael Biofeedback Integration System enables real-time physiological monitoring via wearable devices. It connects to popular fitness trackers and health devices to track heart rate, sleep, activity, and stress levels, which then feed into the micro-intervention engine to trigger context-aware, physiologically-informed interventions.

## Architecture

### Core Components

1. **BiofeedbackDevice Model** - Represents a user's connected wearable
   - Supports: Fitbit, Apple Watch, Garmin, Oura Ring, WHOOP, Polar, Manual Entry
   - Stores OAuth tokens for API sync (flagged for encryption in production)
   - Tracks sync frequency and device lifecycle (connect/disconnect timestamps)

2. **Data Models**
   - `HeartRateRecord` - Hourly heart rate, HRV, activity context
   - `SleepRecord` - Sleep duration, quality, sleep stage breakdowns
   - `ActivityRecord` - Steps, calories, zone minutes
   - `StressRecord` - Subjective stress levels (0-100 scale)
   - `DailyBiofeedbackSummary` - Aggregated daily statistics
   - `BiofeedbackAlert` - Threshold-triggered alerts
   - `BiofeedbackIntegrationConfig` - User settings and thresholds
   - `BiofeedbackEmotionCorrelation` - Emotion ↔ physiological patterns

3. **BiofeedbackIntegrationEngine** (`biofeedback_integration_engine.py`)
   - Autonomous processing of biofeedback data
   - Anomaly detection (unusual HR patterns, sleep deprivation, stress spikes)
   - Insight generation (trends, correlations, narrative insights)
   - Device sync management (stub implementations for each API)

### Integration with InterventionEngine

The BiofeedbackIntegrationEngine feeds into `InterventionEngine._get_user_state()`:

```python
# InterventionEngine now receives:
state['heart_rate']              # Current beats per minute
state['hrv']                     # Heart rate variability
state['sleep_quality']           # 0-100 score
state['sleep_hours']             # Duration of last night
state['activity_level']          # sedentary|light|moderate|vigorous
state['heart_rate_trend']        # improving|declining|stable
state['biofeedback_alerts']      # [BiofeedbackAlert]
state['biofeedback_anomalies']   # [str] list of detected anomalies

# Stress level is blended from emotion + biofeedback (50/50)
state['stress_level'] = (emotion_stress * 0.5) + (bio_stress * 0.5)
```

This allows interventions to be triggered not just on emotion but on physiological markers:
- Elevated HR + high stress → Breathing exercise
- Sleep deprivation → Sleep hygiene reminder
- Inactivity + low HRV → Movement break

## Usage

### User Views

#### Dashboard (`/biofeedback/`)
- Quick stats: Current HR, Sleep quality, Stress, Activity
- Active alerts with acknowledgment
- Connected devices status
- 7-day trend visualization

#### Device Management (`/biofeedback/devices/`)
- List connected and disconnected devices
- View device details and sync status
- Connect/disconnect devices

#### Connect Device (`/biofeedback/devices/connect/`)
- Form to add new wearable
- Device type selection
- OAuth setup instructions (future)

#### Device Detail (`/biofeedback/devices/<id>/`)
- View recent heart rate and sleep data
- Device-specific metrics
- Sync history

#### Alert Dashboard (`/biofeedback/alerts/`)
- View all active and acknowledged alerts
- Acknowledge alerts with optional action notes
- Filter by type and severity

#### Settings (`/biofeedback/settings/`)
- Stress threshold (0-100, default 75)
- Heart rate threshold (BPM, default 100)
- Sleep threshold (hours, default 6)
- Toggle alerts, tracking, auto-interventions
- Privacy: Share with therapist option

### API Endpoints

All return JSON for mobile/external apps:

```
GET /api/biofeedback/hr/?days=7
    Returns: [{ timestamp, heart_rate, hrv, activity_type }]

GET /api/biofeedback/sleep/?days=30
    Returns: [{ sleep_start, sleep_end, duration_hours, quality, ... }]

GET /api/biofeedback/stats/?days=30
    Returns: { avg_heart_rate, avg_sleep, avg_stress, total_steps }

GET /api/biofeedback/emotions/
    Returns: [{ emotion, avg_hr, avg_hrv, correlation_strength }]
```

## Device Syncing Strategy

### Current Implementation
- Stub sync methods in BiofeedbackIntegrationEngine for each device type
- In production, each device type would have:
  1. OAuth initialization and token refresh
  2. API-specific rate limiting (Fitbit: 150 calls/hr, Oura: hourly)
  3. Historical data backfill on first sync
  4. Incremental updates on subsequent syncs

### Example: Fitbit Integration
```python
def _sync_fitbit(self, device) -> list:
    """
    1. Check token expiry; refresh if needed
    2. GET /1/user/-/activities/date/{date}.json (daily summary)
    3. GET /1/user/-/activities/heart/date/{date}/1d/1min.json (detailed HR)
    4. GET /1/user/-/sleep/date/{date}.json (sleep stage data)
    5. Create HeartRateRecord, SleepRecord, ActivityRecord for each data point
    6. Call check_biofeedback_alerts() to create alerts
    7. Return list of created records
    """
```

## Seeding & Testing

### Seed Sample Data
```bash
python manage.py seed_biofeedback --days 7 --user testuser
```

Creates:
- 1 Fitbit device per user
- 7 days of hourly heart rate records
- Daily sleep records (6-9 hours, quality 60-95%)
- Activity records (steps, zones)
- Stress records (30-70 baseline)
- Daily summaries with aggregated stats

## Anomaly Detection

### Implemented Detectors

1. **Heart Rate Anomaly**
   - Compares last 3 days of data
   - Flags if HR > (baseline + 2 std) and > 100 BPM

2. **Stress Anomaly**
   - Flags if stress > 80 or increasing trend

3. **Sleep Anomaly**
   - Flags if < low_sleep_threshold (default 6 hours)

4. **Activity Anomaly**
   - Compares last 2 weeks
   - Flags if recent activity < 50% of baseline

### Alert Types
- `high_stress`: Stress level exceeds threshold
- `low_sleep`: Insufficient sleep duration
- `high_hr`: Heart rate exceeds threshold
- `irregular_pattern`: Unusual physiological pattern detected
- `recovery_needed`: Recovery score low (HRV declining)
- `anomaly`: Generic data anomaly flagged

### Alert Severity
- **Critical**: Requires immediate attention (rare)
- **High**: Notable deviation from baseline
- **Medium**: Mild concern, informational
- **Low**: Observation, no action needed

## Insights Generation

### Narrative Insights
- Sleep quality trend analysis
- Stress level trajectory with suggestions
- Activity consistency assessment
- Personalized recommendations based on patterns

### Emotion-Physiological Correlations
BiofeedbackEmotionCorrelation tracks:
- Average HR for each emotion (anxious, happy, calm, etc.)
- HRV patterns per emotion
- Correlation strength (0-1 scale)
- Sample size for statistical confidence

Example: User's anxiety correlates with 95+ BPM; system can then recommend HR-based interventions when stress detected.

## Privacy & Security

### Current State
- OAuth tokens stored in BiofeedbackDevice.access_token (plaintext)
  - **TODO (Production)**: Encrypt tokens using django-encrypted-model-fields
- Daily summaries and alerts associated with User
- Optional therapist sharing via BiofeedbackIntegrationConfig.share_with_therapist

### Data Retention
- Raw records (HR, sleep, activity, stress): Indefinite (can be pruned)
- Daily summaries: Indefinite for trend analysis
- Alerts: Keep indefinitely for audit trail
- Device tokens: Delete on device.disconnect_at

## Future Enhancements

1. **Real-Time Biofeedback Dashboard**
   - Live HR graph during app usage
   - Real-time stress detection and intervention triggering
   - Wearable notifications (send to device)

2. **Biofeedback-Triggered Interventions**
   - Create InterventionRule.trigger_type = 'biofeedback'
   - Trigger on: "heart_rate > 100 AND stress_detected"
   - Content library: Breathing exercises, meditation, movement

3. **Machine Learning**
   - Predict stress spikes from HR patterns
   - Personalized HR baseline calculation
   - Sleep quality prediction from evening stress/HR data

4. **Advanced Correlations**
   - Analyze emotion → HR → journal entry patterns
   - "When you write about anxiety, your HR averages 98 BPM"
   - Recommend triggers: "You're more anxious on Mondays"

5. **Therapist Dashboard**
   - View patient biofeedback trends
   - Approve/suggest interventions
   - Export reports (HIPAA-compliant)

6. **Mobile Push Notifications**
   - Alert user to high stress/HR anomalies in real-time
   - Suggest immediate actions (breathing, pause, hydrate)

## Settings & Configuration

### BiofeedbackIntegrationConfig Schema
```python
user: OneToOneField(User)
high_stress_threshold: float (0-100, default 75)      # When to alert
high_heart_rate_threshold: int (default 100)          # BPM
low_sleep_threshold: float (default 6.0)              # hours

enable_alerts: bool (default True)
enable_sleep_tracking: bool (default True)
enable_stress_tracking: bool (default True)
auto_trigger_interventions: bool (default True)        # Use bio in intervention logic
share_with_therapist: bool (default False)             # Privacy control
```

## Management Commands

### `seed_biofeedback`
```bash
python manage.py seed_biofeedback [--days 7] [--user username]
```
- Creates sample devices and data for testing
- Useful for demo/testing intervention engine

## Forms

- **BiofeedbackDeviceForm**: Connect new device (name, type, device_id, sync frequency)
- **BiofeedbackConfigForm**: Update thresholds and privacy settings

## Testing

Mock tests for the engine:
```python
# Test anomaly detection
bio_engine = BiofeedbackIntegrationEngine(user)
anomalies = bio_engine.detect_anomalies()
assert "Elevated heart rate" in anomalies

# Test state gathering for intervention engine
state = bio_engine.gather_user_state()
assert state['stress_level'] between [0, 1]
assert state['sleep_hours'] > 0
```

## Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Base models & device connection | ✓ Complete |
| 2 | Data sync & aggregation | → In Progress |
| 3 | Anomaly detection & alerts | ✓ Complete |
| 4 | Integration with InterventionEngine | ✓ Complete |
| 5 | Real-time visualization | Planned |
| 6 | Therapist dashboard | Planned |
| 7 | Mobile push notifications | Planned |

---

## Code References

- Models: [biofeedback_models.py](biofeedback_models.py)
- Engine: [biofeedback_integration_engine.py](biofeedback_integration_engine.py)
- Views: [biofeedback_views.py](biofeedback_views.py)
- Forms: [forms.py](forms.py#L50) (BiofeedbackDeviceForm, BiofeedbackConfigForm)
- URLs: [urls.py](urls.py#L50-L65) (15 routes)
- Templates: `templates/biofeedback/` (dashboard, alerts, device_list, etc.)
- Seeding: [seed_biofeedback.py](management/commands/seed_biofeedback.py)
