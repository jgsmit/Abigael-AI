# Frontend API Reference

This document outlines all API endpoints available for frontend consumption. The system is organized into two main categories: **User Data APIs** and **Task APIs**.

## Base URLs

- **User/Companion APIs**: `/emotion_detection/api/user/`
- **Task APIs**: `/tasks/api/`

All endpoints require authentication (`@login_required`).

---

## User Data APIs

### 1. Get User Profile
**Endpoint**: `GET /emotion_detection/api/user/profile/`

Returns user account information and companion profile settings.

**Response**:
```json
{
  "status": "success",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_joined": "2025-01-01T10:00:00Z"
  },
  "profile": {
    "companion_name": "Abigael",
    "personality_type": "empathetic",
    "communication_style": "warm",
    "preferred_language": "en",
    "timezone": "UTC",
    "avatar_style": "friendly",
    "preferred_voice": "caring_gentle",
    "voice_speed": 1.0,
    "voice_pitch": 1.0,
    "ai_assistance_level": "high",
    "privacy_level": "moderate",
    "notifications_enabled": true
  }
}
```

---

### 2. Get User Emotions Data
**Endpoint**: `GET /emotion_detection/api/user/emotions/`

Returns current emotion, recent emotion history, and emotion trends.

**Response**:
```json
{
  "status": "success",
  "current_emotion": {
    "emotion": "focused",
    "intensity": 0.8,
    "timestamp": "2025-01-28T14:30:00Z",
    "context": "Working on important project"
  },
  "emotion_trends": {
    "last_24_hours": {
      "total_entries": 8,
      "emotions": [
        {"emotion": "happy", "intensity": 0.7, "timestamp": "2025-01-28T14:30:00Z"}
      ]
    },
    "last_7_days": {
      "distribution": {
        "happy": {"count": 15, "average_intensity": 0.75},
        "focused": {"count": 12, "average_intensity": 0.82}
      },
      "total_entries": 45
    }
  },
  "mental_health": {
    "burnout_risk": {
      "level": "low",
      "score": 2.5,
      "last_assessed": "2025-01-28T10:00:00Z"
    }
  }
}
```

---

### 3. Get User Productivity Data
**Endpoint**: `GET /emotion_detection/api/user/productivity/`

Returns task statistics, completion rates, and upcoming tasks.

**Response**:
```json
{
  "status": "success",
  "task_statistics": {
    "total_tasks": 25,
    "completed_tasks": 18,
    "pending_tasks": 7,
    "completion_rate_all_time": 72.0,
    "completion_rate_30_days": 78.5
  },
  "daily_trends": {
    "last_7_days": {
      "2025-01-28": 3,
      "2025-01-27": 2,
      "2025-01-26": 4
    }
  },
  "tasks_by_priority": {
    "high": 5,
    "medium": 12,
    "low": 8
  },
  "upcoming_tasks": [
    {
      "id": 1,
      "title": "Complete project report",
      "due_date": "2025-01-30T17:00:00Z",
      "priority": "high",
      "emotion_tag": "focused"
    }
  ]
}
```

---

### 4. Get User Engagement Data
**Endpoint**: `GET /emotion_detection/api/user/engagement/`

Returns gamification data, achievements, streaks, and daily status.

**Response**:
```json
{
  "status": "success",
  "gamification": {
    "points": 2350,
    "level": 5,
    "badges": ["Consistent", "Motivator", "Goal Setter"]
  },
  "streaks": {
    "current_streak": 12,
    "longest_streak": 24,
    "last_activity_date": "2025-01-28"
  },
  "activity_counts": {
    "daily_checkins": 45,
    "journal_entries": 28,
    "coaching_sessions": 12,
    "conversations_completed": 89
  },
  "achievements": {
    "total_earned": 8,
    "achievements": [
      {
        "id": 1,
        "name": "Week Warrior",
        "description": "Maintain 7-day streak",
        "earned_at": "2025-01-20T10:00:00Z",
        "points": 100
      }
    ]
  },
  "daily_status": {
    "date": "2025-01-28",
    "morning_greeting_sent": true,
    "evening_reflection_sent": false
  }
}
```

---

### 5. Get User Companion Data
**Endpoint**: `GET /emotion_detection/api/user/companion/`

Returns conversation history, journal entries, and coaching sessions.

**Response**:
```json
{
  "status": "success",
  "companion_profile": {
    "name": "Abigael",
    "personality": "empathetic",
    "communication_style": "warm"
  },
  "conversations": {
    "total": 89,
    "recent": [
      {
        "id": "user_1_1704877200",
        "type": "text",
        "started_at": "2025-01-28T14:00:00Z",
        "duration_minutes": 12,
        "message_count": 8,
        "user_emotion_start": "stressed"
      }
    ]
  },
  "journal_entries": {
    "total": 28,
    "recent": [
      {
        "id": 1,
        "date": "2025-01-28",
        "primary_emotion": "happy",
        "emotion_intensity": 0.8,
        "mood": "optimistic",
        "summary": "Had a great day at work...",
        "ai_insights": ["You show resilience", "Good work-life balance"]
      }
    ]
  },
  "coaching_sessions": {
    "total": 12,
    "recent": [
      {
        "id": 1,
        "date": "2025-01-25T15:00:00Z",
        "topic": "Work stress management",
        "duration_minutes": 45,
        "key_insights": "Breathing exercises help...",
        "action_items": ["Practice daily meditation"]
      }
    ]
  }
}
```

---

### 6. Get User Mental Health Data
**Endpoint**: `GET /emotion_detection/api/user/mental-health/`

Returns crisis assessment, burnout metrics, and support resources.

**Response**:
```json
{
  "status": "success",
  "mental_health_metrics": {
    "current_crisis_level": 0.0,
    "burnout_risk": {
      "level": "low",
      "score": 2.5,
      "factors": ["Work load", "Sleep quality"]
    },
    "recent_crises": []
  },
  "support_resources": {
    "emergency_contact_configured": true,
    "human_support_available": true,
    "crisis_hotline": true
  }
}
```

---

### 7. Get Complete User Profile
**Endpoint**: `GET /emotion_detection/api/user/complete/`

Returns all user data in a single comprehensive response. Combines all endpoints above.

**Response**: Unified JSON containing all data from endpoints 1-6.

**Use Case**: Frontend initialization - load all user data on app startup.

---

## Task APIs

### 1. Get All Tasks
**Endpoint**: `GET /tasks/api/tasks/`

Returns paginated list of user tasks with filtering options.

**Query Parameters**:
- `status`: Filter by status (pending, in_progress, completed)
- `priority`: Filter by priority (high, medium, low)
- `emotion`: Filter by emotion tag
- `sort_by`: Sort order (default: `-created_at`)

**Response**:
```json
{
  "status": "success",
  "total_count": 25,
  "tasks": [
    {
      "id": 1,
      "title": "Complete project report",
      "description": "Finish quarterly report",
      "status": "in_progress",
      "priority": "high",
      "emotion_tag": "focused",
      "created_at": "2025-01-27T10:00:00Z",
      "updated_at": "2025-01-28T14:30:00Z",
      "due_date": "2025-01-30T17:00:00Z",
      "completed_at": null,
      "duration_hours": 3.5
    }
  ]
}
```

---

### 2. Get Task Details
**Endpoint**: `GET /tasks/api/tasks/<task_id>/`

Returns detailed information about a specific task including emotion patterns.

**Response**:
```json
{
  "status": "success",
  "task": {
    "id": 1,
    "title": "Complete project report",
    "description": "Finish quarterly report",
    "status": "in_progress",
    "priority": "high",
    "emotion_tag": "focused",
    "created_at": "2025-01-27T10:00:00Z",
    "updated_at": "2025-01-28T14:30:00Z",
    "due_date": "2025-01-30T17:00:00Z",
    "completed_at": null,
    "duration_hours": 3.5,
    "estimated_duration": 4.0,
    "emotion_pattern": {
      "emotion_before": "stressed",
      "emotion_after": "proud",
      "emotional_impact": "positive"
    }
  }
}
```

---

### 3. Get Task Analytics
**Endpoint**: `GET /tasks/api/tasks/analytics/`

Returns comprehensive task analytics and insights.

**Response**:
```json
{
  "status": "success",
  "overview": {
    "total_tasks": 25,
    "completed_tasks": 18,
    "pending_tasks": 7,
    "overall_completion_rate": 72.0
  },
  "time_based": {
    "last_7_days": {
      "completed": 8,
      "completion_rate": 80.0
    },
    "last_30_days": {
      "completed": 15,
      "completion_rate": 75.0
    }
  },
  "distribution": {
    "by_priority": [
      {"priority": "high", "count": 5},
      {"priority": "medium", "count": 12}
    ],
    "by_status": [
      {"status": "completed", "count": 18},
      {"status": "in_progress", "count": 3}
    ]
  },
  "patterns": {
    "emotion_transitions": [
      {"emotion_before": "stressed", "emotion_after": "proud", "count": 8}
    ],
    "completion_by_weekday": {
      "2025-01-28": 3,
      "2025-01-27": 2
    },
    "avg_duration_by_priority": [
      {"priority": "high", "avg_duration": 4.5, "count": 5}
    ]
  },
  "insights": [
    "Excellent completion rate! You're very productive.",
    "You have 2 high-priority tasks pending. Consider starting one today."
  ]
}
```

---

### 4. Get Task Recommendations
**Endpoint**: `GET /tasks/api/tasks/recommendations/`

Returns AI-powered task recommendations based on current emotion and patterns.

**Response**:
```json
{
  "status": "success",
  "current_emotion": "focused",
  "recommendations": [
    {
      "task_id": 1,
      "title": "Complete project report",
      "priority": "high",
      "match_score": 0.92,
      "recommended_now": true,
      "context": "Perfect timing for this task - you're focused!",
      "emotional_readiness": "focused"
    },
    {
      "task_id": 3,
      "title": "Review team feedback",
      "priority": "medium",
      "match_score": 0.78,
      "recommended_now": true,
      "context": "This task makes you feel good!",
      "emotional_readiness": "focused"
    }
  ]
}
```

---

## Frontend Integration Examples

### Initialize App with Complete User Data
```javascript
// On app startup, load all user data
fetch('/emotion_detection/api/user/complete/')
  .then(res => res.json())
  .then(data => {
    // Set user profile
    store.commit('setUserProfile', data.profile);
    
    // Set emotions
    store.commit('setCurrentEmotion', data.emotions.current_emotion);
    store.commit('setEmotionTrends', data.emotion_trends);
    
    // Set productivity
    store.commit('setTaskStats', data.productivity.task_statistics);
    
    // Set engagement
    store.commit('setGamification', data.engagement.gamification);
    store.commit('setStreaks', data.engagement.streaks);
  });
```

### Display Task Recommendations
```javascript
// Get smart task recommendations
fetch('/tasks/api/tasks/recommendations/')
  .then(res => res.json())
  .then(data => {
    // Show top recommended tasks
    const recommended = data.recommendations.filter(r => r.recommended_now);
    displayRecommendations(recommended);
  });
```

### Update Dashboard with Real-time Data
```javascript
// Periodically refresh user data
setInterval(() => {
  fetch('/emotion_detection/api/user/emotions/')
    .then(res => res.json())
    .then(data => {
      updateEmotionDisplay(data.current_emotion);
      updateEmotionChart(data.emotion_trends);
    });
}, 30000); // Every 30 seconds
```

---

## Error Handling

All endpoints return standard error format:

```json
{
  "status": "error",
  "message": "Description of error"
}
```

HTTP Status Codes:
- `200`: Success
- `400`: Bad request
- `401`: Unauthorized (not logged in)
- `404`: Not found
- `500`: Server error

---

## Rate Limiting & Performance

- No rate limiting enforced (production might add)
- Task list limited to 100 results per request
- Use pagination for large datasets
- Cache responses on frontend for 30 seconds minimum

---

## Data Update Frequency

Recommended frontend refresh intervals:
- **User Profile**: On-demand or once per session
- **Emotions**: Every 30 seconds
- **Tasks**: Every 1 minute
- **Engagement/Streaks**: Every 5 minutes
- **Analytics**: On-demand or every 10 minutes
