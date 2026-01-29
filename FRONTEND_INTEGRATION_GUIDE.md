# Frontend Integration Guide

Complete guide for frontend developers to integrate with the EmoFocus AI backend.

## Overview

The backend provides comprehensive APIs for:
1. **User Profile & Settings** - User info, preferences, companion configuration
2. **Emotion Data** - Current emotion, history, trends, mental health status
3. **Productivity Data** - Tasks, completion rates, upcoming work
4. **Engagement Metrics** - Gamification, achievements, streaks, activity tracking
5. **Companion Interaction** - Conversations, journal entries, coaching sessions
6. **Mental Health Data** - Crisis assessment, burnout risk, support resources
7. **Task Management** - CRUD operations, analytics, AI recommendations

---

## Quick Start

### 1. Load User Data on App Init

```javascript
// src/services/api.js
async function initializeUserData() {
  try {
    const response = await fetch('/emotion_detection/api/user/complete/');
    const data = await response.json();
    
    if (data.status === 'success') {
      return {
        profile: data.profile,
        user: data.user,
        emotions: data.emotions,
        productivity: data.productivity,
        engagement: data.engagement,
        companion: data.companion,
        mentalHealth: data.mental_health
      };
    }
  } catch (error) {
    console.error('Failed to load user data:', error);
  }
}

// src/main.js (Vue/React app entry)
async function setupApp() {
  const userData = await initializeUserData();
  store.commit('setUserData', userData);
  renderApp();
}
```

### 2. Display Current Emotion & Status

```vue
<!-- src/components/EmotionStatus.vue -->
<template>
  <div class="emotion-card">
    <h3>Current Mood</h3>
    <div class="emotion-display">
      <span class="emotion-icon">{{ getEmotionIcon(currentEmotion.emotion) }}</span>
      <span class="emotion-name">{{ currentEmotion.emotion }}</span>
      <span class="intensity">{{ Math.round(currentEmotion.intensity * 100) }}%</span>
    </div>
    <p class="timestamp">{{ formatTime(currentEmotion.timestamp) }}</p>
  </div>
</template>

<script>
export default {
  computed: {
    currentEmotion() {
      return this.$store.state.userEmotion.current || {};
    }
  },
  methods: {
    getEmotionIcon(emotion) {
      const icons = {
        happy: '😊',
        sad: '😢',
        focused: '🎯',
        stressed: '😰',
        calm: '😌',
        excited: '🎉'
      };
      return icons[emotion] || '😐';
    },
    formatTime(timestamp) {
      return new Date(timestamp).toLocaleTimeString();
    }
  }
}
</script>
```

### 3. Display Task Dashboard

```vue
<!-- src/components/TaskDashboard.vue -->
<template>
  <div class="dashboard">
    <!-- Task Statistics -->
    <div class="stats-grid">
      <stat-card 
        title="Completed" 
        :value="taskStats.completed_tasks"
        color="green"
      />
      <stat-card 
        title="Pending" 
        :value="taskStats.pending_tasks"
        color="orange"
      />
      <stat-card 
        title="Completion Rate" 
        :value="`${taskStats.completion_rate_all_time}%`"
        color="blue"
      />
    </div>

    <!-- Task Recommendations -->
    <div class="recommendations">
      <h3>Recommended Tasks ({{ currentEmotion }})</h3>
      <task-card 
        v-for="task in recommendations" 
        :key="task.task_id"
        :task="task"
        :is-recommended="task.recommended_now"
      />
    </div>

    <!-- Upcoming Tasks -->
    <div class="upcoming">
      <h3>Upcoming Tasks</h3>
      <task-list :tasks="upcomingTasks" />
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      recommendations: [],
      upcomingTasks: []
    }
  },
  computed: {
    taskStats() {
      return this.$store.state.productivity.task_statistics;
    },
    currentEmotion() {
      return this.$store.state.userEmotion.current?.emotion || 'neutral';
    }
  },
  async mounted() {
    // Load task recommendations based on current emotion
    const recResponse = await fetch('/tasks/api/tasks/recommendations/');
    const recData = await recResponse.json();
    this.recommendations = recData.recommendations;

    // Load upcoming tasks
    const tasksResponse = await fetch('/tasks/api/tasks/?status=pending');
    const tasksData = await tasksResponse.json();
    this.upcomingTasks = tasksData.tasks;
  }
}
</script>
```

### 4. Display Achievements & Streaks

```vue
<!-- src/components/GamificationWidget.vue -->
<template>
  <div class="gamification">
    <!-- Current Streak -->
    <div class="streak-card">
      <div class="flame-icon">🔥</div>
      <div class="streak-info">
        <p class="current">{{ streakData.current_streak }} day streak</p>
        <p class="best">Best: {{ streakData.longest_streak }} days</p>
      </div>
    </div>

    <!-- Points & Level -->
    <div class="level-card">
      <p class="level">Level {{ gamification.level }}</p>
      <p class="points">{{ gamification.points }} Points</p>
      <div class="progress-bar">
        <div class="fill" :style="{ width: getProgressPercent() }"></div>
      </div>
    </div>

    <!-- Badges -->
    <div class="badges">
      <h4>Badges Earned</h4>
      <div class="badge-list">
        <badge-item 
          v-for="badge in gamification.badges"
          :key="badge"
          :badge="badge"
        />
      </div>
    </div>

    <!-- Recent Achievements -->
    <div class="achievements">
      <h4>Recent Achievements</h4>
      <achievement-item 
        v-for="achievement in recentAchievements"
        :key="achievement.id"
        :achievement="achievement"
      />
    </div>
  </div>
</template>

<script>
export default {
  computed: {
    gamification() {
      return this.$store.state.engagement.gamification;
    },
    streakData() {
      return this.$store.state.engagement.streaks;
    },
    recentAchievements() {
      return this.$store.state.engagement.achievements.achievements.slice(0, 3);
    }
  },
  methods: {
    getProgressPercent() {
      // Calculate progress to next level (example: 100 points per level)
      const pointsInLevel = this.gamification.points % 100;
      return (pointsInLevel / 100) * 100;
    }
  }
}
</script>
```

### 5. Emotion Trends Chart

```vue
<!-- src/components/EmotionTrends.vue -->
<template>
  <div class="trends-chart">
    <h3>Emotion Trends - Last 7 Days</h3>
    <div class="emotion-distribution">
      <emotion-bar 
        v-for="(data, emotion) in emotionDistribution"
        :key="emotion"
        :emotion="emotion"
        :count="data.count"
        :intensity="data.average_intensity"
      />
    </div>
    <line-chart 
      :data="emotionTimeline"
      :options="chartOptions"
    />
  </div>
</template>

<script>
import LineChart from './charts/LineChart.vue';

export default {
  components: { LineChart },
  computed: {
    emotionDistribution() {
      return this.$store.state.userEmotion.emotion_trends.last_7_days.distribution;
    },
    emotionTimeline() {
      return this.$store.state.userEmotion.emotion_trends.last_24_hours.emotions
        .map(e => ({
          time: new Date(e.timestamp).toLocaleTimeString(),
          emotion: e.emotion,
          intensity: e.intensity
        }));
    }
  },
  data() {
    return {
      chartOptions: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            max: 1.0
          }
        }
      }
    }
  }
}
</script>
```

### 6. Real-time Updates

```javascript
// src/services/realtime.js

export class RealtimeService {
  constructor(store) {
    this.store = store;
    this.updateIntervals = {};
  }

  start() {
    // Update emotions every 30 seconds
    this.updateIntervals.emotions = setInterval(() => {
      this.updateEmotions();
    }, 30000);

    // Update tasks every 1 minute
    this.updateIntervals.tasks = setInterval(() => {
      this.updateTasks();
    }, 60000);

    // Update engagement metrics every 5 minutes
    this.updateIntervals.engagement = setInterval(() => {
      this.updateEngagement();
    }, 300000);
  }

  async updateEmotions() {
    const response = await fetch('/emotion_detection/api/user/emotions/');
    const data = await response.json();
    this.store.commit('setEmotionData', data);
  }

  async updateTasks() {
    const response = await fetch('/tasks/api/tasks/analytics/');
    const data = await response.json();
    this.store.commit('setTaskAnalytics', data);
  }

  async updateEngagement() {
    const response = await fetch('/emotion_detection/api/user/engagement/');
    const data = await response.json();
    this.store.commit('setEngagement', data);
  }

  stop() {
    Object.values(this.updateIntervals).forEach(interval => clearInterval(interval));
  }
}

// src/main.js
import { RealtimeService } from '@/services/realtime';

const realtimeService = new RealtimeService(store);
realtimeService.start();

// Cleanup on app unmount
window.addEventListener('beforeunload', () => {
  realtimeService.stop();
});
```

---

## API Endpoints Summary

| Feature | Endpoint | Method | Purpose |
|---------|----------|--------|---------|
| **User Profile** | `/emotion_detection/api/user/profile/` | GET | User info & settings |
| **Emotions** | `/emotion_detection/api/user/emotions/` | GET | Current emotion & trends |
| **Productivity** | `/emotion_detection/api/user/productivity/` | GET | Task stats & upcoming work |
| **Engagement** | `/emotion_detection/api/user/engagement/` | GET | Achievements, streaks, points |
| **Companion** | `/emotion_detection/api/user/companion/` | GET | Conversations, journals, coaching |
| **Mental Health** | `/emotion_detection/api/user/mental-health/` | GET | Crisis status, support resources |
| **Complete Profile** | `/emotion_detection/api/user/complete/` | GET | All data combined |
| **All Tasks** | `/tasks/api/tasks/` | GET | Task list with filtering |
| **Task Details** | `/tasks/api/tasks/<id>/` | GET | Single task info |
| **Task Analytics** | `/tasks/api/tasks/analytics/` | GET | Task metrics & insights |
| **Task Recommendations** | `/tasks/api/tasks/recommendations/` | GET | AI-powered suggestions |

---

## State Management (Vuex/Redux Example)

```javascript
// src/store/modules/user.js
const state = {
  profile: null,
  userInfo: null,
  emotions: {
    current: null,
    trends: {}
  },
  productivity: {
    task_statistics: {},
    upcoming_tasks: []
  },
  engagement: {
    gamification: {},
    streaks: {},
    achievements: []
  },
  mentalHealth: {
    burnout_risk: {},
    crisis_level: 0
  }
};

const mutations = {
  setUserData(state, data) {
    state.profile = data.profile;
    state.userInfo = data.user;
    state.emotions = data.emotions;
    state.productivity = data.productivity;
    state.engagement = data.engagement;
    state.mentalHealth = data.mentalHealth;
  },
  setEmotionData(state, data) {
    state.emotions = data;
  },
  updateCurrentEmotion(state, emotion) {
    state.emotions.current = emotion;
  }
};

export default {
  namespaced: true,
  state,
  mutations
};
```

---

## Best Practices

1. **Cache Data**: Store responses locally for 30+ seconds to reduce API calls
2. **Lazy Load**: Only fetch data when needed (e.g., on tab/modal open)
3. **Error Handling**: Always catch fetch errors and show user-friendly messages
4. **Loading States**: Show spinners while data is loading
5. **Batch Requests**: Consider fetching complete profile on app init instead of individual calls
6. **Real-time Updates**: Use intervals for critical data (emotions, tasks)
7. **Debounce**: Debounce frequent user actions before API calls

---

## Troubleshooting

### 401 Unauthorized
- User not logged in
- Session expired
- Implement login redirect in interceptor

### 404 Not Found
- Task/resource doesn't exist
- User doesn't have permission
- Check resource IDs and ownership

### 500 Server Error
- Check server logs
- Ensure all related models exist
- Verify database connectivity

---

## Support

For issues or questions about the API:
1. Check [FRONTEND_API_REFERENCE.md](./FRONTEND_API_REFERENCE.md)
2. Review endpoint response examples
3. Check browser console for error details
4. Review server logs for backend errors
