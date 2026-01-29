# QUICK START GUIDE: Using EmoFocus Features

A practical guide for developers integrating EmoFocus capabilities into your Django app.

---

## Installation (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create migrations
python manage.py makemigrations emotion_detection
python manage.py migrate

# 3. Update settings.py
# Add to INSTALLED_APPS: 'rest_framework'
# Add guardrails_privacy_urls to main urls.py

# 4. You're done!
```

---

## Quick Examples

### 1. Check User's Mental Health Status

```python
from emotion_detection.mental_health_guardrails import MentalHealthGuardrailEngine

user = request.user
engine = MentalHealthGuardrailEngine(user)

# Get complete status
status = engine.check_all_guardrails()

if status['burnout_warning']['triggered']:
    # User is at risk of burnout
    days_remaining = status['burnout_warning']['days_to_burnout']
    print(f"⚠️ Burnout risk in {days_remaining} days")
    
    # Recommend interventions
    for action in status['critical_actions']:
        print(f"Suggested action: {action}")

if status['emotional_spiral']['detected']:
    spiral_type = status['emotional_spiral']['spiral_type']
    print(f"🌀 Detected {spiral_type}")
    
    # Get grounding exercise
    exercise = engine.recommend_grounding_exercise()
    print(f"Try this: {exercise['exercise']}")
```

### 2. Get Emotion Forecast for Next 3 Hours

```python
from emotion_detection.emotion_forecaster import EmotionForecaster

forecaster = EmotionForecaster(user=request.user)
forecast = forecaster.forecast_emotions(hours_ahead=3)

print("Next 3 hours emotions:")
for item in forecast:
    print(f"  {item['time']}: {item['emotion']} (confidence: {item['confidence']:.0%})")

# Get insights
stress_peaks = forecaster.identify_stress_peaks()
focus_windows = forecaster.identify_focus_windows()

print(f"\nStress peaks: {[p['time'] for p in stress_peaks]}")
print(f"Focus windows: {[f['time'] for f in focus_windows]}")
```

### 3. Enable Flow State Protection

```python
from emotion_detection.flow_state_guardian import FlowStateGuardian

guardian = FlowStateGuardian(user=request.user)

# Start monitoring
is_in_flow = guardian.detect_flow_entry()

if is_in_flow:
    print("🎯 User is in flow state - enabling protections")
    
    # Activate protections
    protections = guardian.activate_flow_protection()
    # {notifications_suppressed: true, chat_disabled: true, ...}
    
    # Monitor for interruptions
    while user_still_working:
        interruptions = guardian.detect_flow_interruption()
        if len(interruptions) > 0:
            print("⚠️ Flow interrupted!")
            break
    
    # Plan recovery
    recovery = guardian.plan_post_flow_recovery()
    print(f"Recommended recovery: {recovery['type']}")
```

### 4. Regulate Motivation/Dopamine

```python
from emotion_detection.dopamine_engine import DopamineRegulationEngine

engine = DopamineRegulationEngine(user=request.user)

# Check motivation status
depletion = engine.detect_dopamine_depletion()
print(f"Dopamine depletion risk: {depletion['risk_level']} ({depletion['score']}/100)")

if depletion['risk_level'] == 'critical':
    # Inject small wins
    wins = engine.inject_small_wins(task_id=task.id)
    print(f"Breaking task into {len(wins)} manageable pieces")
    
    # Get adaptive feedback tone
    tone = engine.adjust_feedback_tone()
    print(f"Use {tone} feedback tone")

# Predict crash
crash = engine.predict_motivation_crash()
if crash['hours_to_crash']:
    print(f"⚠️ Motivation crash predicted in {crash['hours_to_crash']} hours")
```

### 5. Manage Privacy & Encryption

```python
from emotion_detection.privacy_engine import PrivacyEngineManager

manager = PrivacyEngineManager(user=request.user)

# Encrypt sensitive emotion data
vault_entry = manager.encrypt_emotion_data(
    emotion='anxious',
    context={'activity': 'presentation', 'audience': 5},
    triggers=['public_speaking']
)
print(f"Emotion securely stored: {vault_entry.id}")

# Schedule auto-deletion
manager.schedule_auto_deletion()
print("Auto-deletion scheduled for 90-day-old emotions")

# Enable on-device ML
manager.enable_on_device_processing()
print("On-device inference enabled (emotion, stress, flow models)")

# Get privacy dashboard
dashboard = manager.get_privacy_dashboard()
print(f"Encryption level: {dashboard['encryption_level']}")
print(f"Data usage: {dashboard['data_storage']['total_mb']}MB")
```

### 6. Get Team/Organization Insights (Admin Only)

```python
from emotion_detection.org_mode_models import AnonymousTeamAnalytics

org = request.user.organization  # User's organization
analytics = AnonymousTeamAnalytics(org)

# Get team health (NO individual data exposed)
health = analytics.get_team_health_dashboard()
print(f"Team focus availability: {health['focus_available']}%")
print(f"Team cognitive load: {health['cognitive_load_avg']}%")
print(f"Burnout risk: {health['burnout_risk']}%")

# Analyze meeting impact
meeting = Meeting.objects.get(id=1)
impact = analytics.analyze_meeting_efficiency(meeting)
print(f"Meeting costs {impact['focus_cost_hours']} team focus hours")
print(f"Recommendation: {impact['recommendation']}")

# Get recovery score
recovery = analytics.get_recovery_score()
print(f"Team recovery rate: {recovery['recovery_rate']}%")
```

### 7. Create AI Insights with Explanations

```python
from emotion_detection.privacy_engine import PrivacyEngineManager

manager = PrivacyEngineManager(user=request.user)

# Create an insight with explanation
insight = manager.create_explainable_insight(
    insight_type='recommendation',
    insight_text='Take a break in next 2 hours',
    reasoning='Attention span declining, no breaks in 4 hours',
    key_factors={
        'attention_decay': 0.15,
        'break_deficit': 0.8,
        'emotion_trend': 0.25
    },
    confidence=0.92
)

# User sees different levels based on their preference
simple = insight.get_explanation('simple')
# → "Take a break in next 2 hours"

detailed = insight.get_explanation('detailed')
# → "Take a break in next 2 hours
#    Why: Attention span declining, no breaks in 4 hours"

technical = insight.get_explanation('technical')
# → Full breakdown with confidence, alternatives, key factors
```

---

## Common Tasks

### A. Respond to Mental Health Crisis

```python
from emotion_detection.mental_health_guardrails import (
    CrisisIndicator, HumanSupportEscalation
)

# Detect crisis
crisis = CrisisIndicator.objects.create(
    user=user,
    indicator_type='suicidal_ideation',
    crisis_level='critical'
)

# Escalate immediately
escalation = HumanSupportEscalation.objects.create(
    user=user,
    reason='crisis_team',
    urgency='critical'
)

# Provide resources
resources = {
    '988 Suicide Lifeline': '988',
    'Crisis Text Line': 'Text HOME to 741741',
    'Emergency': '911'
}
```

### B. Enable Federated Learning (Privacy-Preserving)

```python
from emotion_detection.privacy_engine import PrivacyEngineManager

manager = PrivacyEngineManager(user=request.user)

# User opts into federated learning
participant = manager.enroll_federated_learning(
    study_name='emotion-forecasting-improvement'
)

# System now:
# - Trains emotion model locally on user's device
# - Sends only model weights to server (not raw emotions)
# - Server aggregates weights from all participants
# - Updated global model returned to device
# - No individual emotions ever transmitted
```

### C. Export User Data (GDPR)

```python
from emotion_detection.privacy_engine import PrivacyEngineManager

manager = PrivacyEngineManager(user=request.user)

# Export all user data
export = manager.get_privacy_dashboard()  # Includes export link
# User gets JSON file with all emotions, tasks, metrics

# Request deletion
request.data = {'deletion_type': 'complete'}
# → 30-day grace period starts
# → User confirms via email
# → All data permanently deleted after confirmation
```

### D. Give Grounding Exercise in Crisis Moment

```python
from emotion_detection.mental_health_guardrails import MentalHealthGuardrailEngine

engine = MentalHealthGuardrailEngine(request.user)

# Get exercise recommendation
exercise = engine.recommend_grounding_exercise(emotion_state='anxious')

# Return to user in crisis
response = {
    'exercise': exercise['exercise'],  # 'box_breathing'
    'instructions': [
        'Breathe in for 4 counts',
        'Hold for 4 counts',
        'Exhale for 4 counts',
        'Hold for 4 counts',
        'Repeat 4-5 times'
    ],
    'duration_minutes': 5,
    'reason': 'Good for anxious state'
}

# Log completion
GroundingExercise.objects.create(
    user=request.user,
    exercise_type='box_breathing',
    user_did_exercise=True,
    effectiveness_score=8,
    emotion_before='anxious',
    emotion_after='calm'
)
```

### E. Use On-Device ML for Privacy

```python
from emotion_detection.privacy_engine import PrivacyEngineManager

# All users can use on-device models
manager = PrivacyEngineManager(user=request.user)
manager.enable_on_device_processing()

# Models now available locally:
# 1. Emotion Classifier (v2.1) - Detects emotion from face
# 2. Stress Detector (v1.5) - Detects stress from voice
# 3. Flow State Detector (v1.0) - Detects flow from activity

# Running emotion detection on device (no cloud):
# - Camera → Local emotion classifier → Result
# - Never sends image to server
# - Privacy by design
```

---

## API Endpoints Quick Reference

### Mental Health Guardrails

```bash
# Get burnout warning
curl -H "Authorization: Bearer $TOKEN" \
  https://api.emofocus.app/api/burnout-warning/

# Get emotional spiral status
curl https://api.emofocus.app/api/emotional-spiral/

# Get grounding exercise recommendation
curl -X POST https://api.emofocus.app/api/grounding-exercise/recommend/ \
  -d '{"emotion": "anxious"}'

# Log exercise completion
curl -X POST https://api.emofocus.app/api/grounding-exercise/log-completion/ \
  -d '{"exercise_type": "box_breathing", "effectiveness_score": 8}'

# Get crisis resources
curl https://api.emofocus.app/api/crisis-resources/
```

### Privacy Management

```bash
# Get privacy dashboard
curl https://api.emofocus.app/privacy/

# Update privacy settings
curl -X POST https://api.emofocus.app/api/privacy/update-settings/ \
  -d '{"encryption_level": "maximum"}'

# Check encryption status
curl https://api.emofocus.app/api/privacy/encryption-status/

# Get audit log
curl "https://api.emofocus.app/api/privacy/audit-log/?days=30"

# Export data (GDPR)
curl https://api.emofocus.app/api/privacy/data-export/

# Get AI insights
curl "https://api.emofocus.app/api/ai-insights/?level=detailed"
```

---

## Frontend Integration

### Mental Health Dashboard

```html
<!-- Show burnout warning -->
<div id="burnout-alert" style="display: none;">
  <h3>⚠️ Burnout Alert</h3>
  <p id="burnout-message"></p>
  <button onclick="startRecoveryMode()">Start Recovery</button>
</div>

<script>
fetch('/api/burnout-warning/')
  .then(r => r.json())
  .then(data => {
    if (data.triggered) {
      document.getElementById('burnout-alert').style.display = 'block';
      document.getElementById('burnout-message').innerText = 
        `Burnout risk in ${data.days_to_burnout} days. Score: ${data.warning_score}/100`;
    }
  });
</script>
```

### Emotion Forecast Widget

```html
<div id="emotion-forecast">
  <h3>Next 3 Hours</h3>
  <div id="forecast-list"></div>
</div>

<script>
fetch('/api/emotion-forecast/')
  .then(r => r.json())
  .then(data => {
    const html = data.forecast
      .map(f => `<div>${f.time}: ${f.emotion} (${f.confidence}%)</div>`)
      .join('');
    document.getElementById('forecast-list').innerHTML = html;
  });
</script>
```

### Privacy Settings Panel

```html
<div id="privacy-settings">
  <label>
    <input type="checkbox" id="encryption" /> 
    Enable Encryption
  </label>
  
  <label>
    <select id="retention">
      <option value="7_days">7 Days</option>
      <option value="30_days">30 Days</option>
      <option value="90_days">90 Days (Default)</option>
    </select>
    Data Retention
  </label>
  
  <button onclick="savePrivacySettings()">Save</button>
</div>

<script>
function savePrivacySettings() {
  const settings = {
    encrypt_emotions_at_rest: document.getElementById('encryption').checked,
    emotion_data_retention: document.getElementById('retention').value
  };
  
  fetch('/api/privacy/update-settings/', {
    method: 'POST',
    body: JSON.stringify(settings)
  });
}
</script>
```

---

## Run locally (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
# (optional) Create an admin user: python manage.py createsuperuser
python manage.py runserver
```

Visit: http://localhost:8000/  — unified dashboard
Visit: http://localhost:8000/tasks/ — task list & recommendations

## Testing

```python
# Run tests
python manage.py test emotion_detection

# Test burnout detection
from emotion_detection.mental_health_guardrails import BurnoutEarlyWarning

BurnoutEarlyWarning.objects.create(
    user=test_user,
    stress_accumulation_score=80,
    urgent_action_needed=True
)

# Test encryption
from emotion_detection.privacy_engine import EncryptedEmotionVault

vault = EncryptedEmotionVault.encrypt_data('sad', encryption_key)
decrypted = EncryptedEmotionVault.decrypt_data(vault, encryption_key)
assert decrypted == 'sad'
```

---

## Error Handling

```python
try:
    engine = MentalHealthGuardrailEngine(user)
    results = engine.check_all_guardrails()
except Exception as e:
    # Gracefully handle errors
    logger.error(f"Guardrail check failed: {e}")
    # Return safe defaults
    results = {
        'burnout_warning': {'triggered': False},
        'emotional_spiral': {'detected': False},
        'crisis_indicators': {'detected': False}
    }
```

---

## Performance Tips

1. **Cache results** - Burnout checks every 1 hour (not continuous)
2. **Use on-device ML** - Faster inference, better privacy
3. **Batch queries** - Check multiple users at night (off-peak)
4. **Archive old data** - Move 1+ year old emotions to cold storage

---

## Support

- 📖 Full docs: See `IMPLEMENTATION_COMPLETE.md`
- 🐛 Issues: Check error logs in admin dashboard
- 💬 Questions: Review usage examples above
- 🔐 Security: All endpoints require authentication

---

**Version**: 7.0 (All phases complete)
**Last Updated**: 2024-01-15
**Status**: Production Ready ✅
