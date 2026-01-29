# Frontend Templates Integration Guide

## Overview

All web page templates have been updated to fetch and display **comprehensive user data** from the new API endpoints. Templates now use client-side JavaScript to load real-time data instead of relying on server-side template variables.

## Updated Templates

### 1. **Companion Dashboard** 
**File**: `tasks/templates/dashboard/unified_dashboard.html`

#### Features
- Fetches complete user profile from `/emotion_detection/api/user/complete/`
- Real-time emotion display with emoji indicators
- Live engagement data (streaks, points, level)
- Mental health crisis detection & alerts
- Voice chat with emotion-aware companion
- Video avatar support
- Auto-refresh emotion data every 30 seconds
- Message history with typing indicators
- Crisis alert system with quick support links

#### Key API Calls
```javascript
// Fetches all user data on load
await APIService.fetchUserData()

// Auto-updates emotion every 30 seconds
setInterval(async () => {
    const emotionData = await APIService.fetchEmotionData();
}, 30000);
```

#### Display Elements
| Element | Source | Update Frequency |
|---------|--------|------------------|
| Companion Name | Profile API | On load |
| Current Emotion | Emotion API | 30 seconds |
| Streak Counter | User Complete API | On load |
| Points & Level | User Complete API | On load |
| Crisis Status | Mental Health API | On load |
| Recent Journals | Companion API | On load |

---

### 2. **Enhanced Dashboard**
**File**: `tasks/templates/dashboard/unified_dashboard.html`

#### Features
- Displays live emotion state with visual indicators (😊😢🎯😰😌🎉😠😴)
- Task statistics with completion rates and trends
- AI-powered task recommendations (0-1 match score)
- Engagement tracking (level, streaks, achievements)
- Emotion history (24-hour trend visualization)
- Empathetic AI messages based on current mood
- Real-time task list with emotion integration
- Mental health status display

#### Key API Calls
```javascript
// Fetch all data in parallel
const [userData, analytics, recommendations, allTasks] = await Promise.all([
    DashboardAPI.fetchUserComplete(),
    DashboardAPI.fetchTasksAnalytics(),
    DashboardAPI.fetchTaskRecommendations(),
    DashboardAPI.fetchAllTasks('pending')
]);
```

#### Live Data Updates
| Component | API Endpoint | Refresh Rate |
|-----------|--------------|--------------|
| User Profile | `/emotion_detection/api/user/profile/` | On load |
| Emotions & Trends | `/emotion_detection/api/user/emotions/` | Manual refresh |
| Engagement | `/emotion_detection/api/user/engagement/` | Manual refresh |
| Task Analytics | `/tasks/api/tasks/analytics/` | Manual refresh |
| Task Recommendations | `/tasks/api/tasks/recommendations/` | Manual refresh |
| Pending Tasks | `/tasks/api/tasks/?status=pending` | Manual refresh |

#### Display Elements

**Emotion Card**
```html
<div id="emotionCard">
  <!-- Current emotion with emoji -->
  <!-- Emotion trend visualization -->
  <!-- Empathy message -->
</div>
```

**Statistics Cards**
- Total Tasks: From analytics.overview.total_tasks
- Pending Tasks: From analytics.overview.pending_tasks
- Completed Tasks: From analytics.overview.completed_tasks
- Completion Rate: Calculated from overview data

**Task Recommendations**
- Renders top 5 recommended tasks
- Shows match score (0-100%)
- Displays recommendation reason
- Links to task update pages

**Engagement Display**
- Level indicator with emoji (⭐)
- Current streak (🔥)
- Total points (⚡)
- Achievements count (🏆)

---

### 3. **Task List**
**File**: `tasks/templates/tasks/task_list.html`

#### Features
- Dynamic task rendering from API
- Client-side filtering by status, priority, and search term
- Task statistics dashboard (Total, Pending, In Progress, Completed)
- Completion rate visualization
- Real-time task list updates
- Quick-edit and delete actions
- Auto-refresh every 2 minutes

#### Key API Calls
```javascript
// Fetch all tasks with full data
const tasks = await TaskListAPI.fetchAllTasks();

// Get detailed analytics including completion rates
const analytics = await TaskListAPI.fetchTaskAnalytics();
```

#### Filtering
All filtering happens **client-side** for instant UX:
```javascript
function applyFilters() {
    const status = document.getElementById('filter-status').value;
    const priority = document.getElementById('filter-priority').value;
    const search = document.getElementById('filter-search').value.toLowerCase();
    
    let filtered = allTasks.filter(task => {
        const matchesStatus = !status || task.status === status;
        const matchesPriority = !priority || task.priority === priority;
        const matchesSearch = !search || task.title.toLowerCase().includes(search);
        return matchesStatus && matchesPriority && matchesSearch;
    });
    
    renderTasks(filtered);
}
```

#### Display Elements
| Element | Source | Format |
|---------|--------|--------|
| Total Tasks | analytics.overview.total_tasks | Number |
| Pending Tasks | analytics.overview.pending_tasks | Number |
| In Progress | analytics.overview.in_progress_tasks | Number |
| Completed | analytics.overview.completed_tasks | Number |
| Task Priority | task.priority | Badge (high/medium/low) |
| Task Status | task.status | Badge (pending/in_progress/completed) |
| Created Date | task.created_at | Formatted date |
| Due Date | task.due_date | Formatted date |

---

## API Service Classes

### DashboardAPI (unified_dashboard.html)
```javascript
class DashboardAPI {
    static async fetchUserComplete()
    static async fetchTasksAnalytics()
    static async fetchTaskRecommendations()
    static async fetchAllTasks(status = null)
}
```

### APIService (unified_dashboard.html)
```javascript
class APIService {
    static async fetchUserData()
    static async fetchEmotionData()
    static async sendMessage(conversationId, message)
}
```

### TaskListAPI (task_list.html)
```javascript
class TaskListAPI {
    static async fetchAllTasks()
    static async fetchTaskAnalytics()
}
```

---

## Data Flow Diagram

```
User Opens Dashboard
    ↓
JavaScript loads (DOMContentLoaded)
    ↓
API calls made in parallel
    ├─ fetchUserComplete()
    ├─ fetchTasksAnalytics()
    ├─ fetchTaskRecommendations()
    └─ fetchAllTasks()
    ↓
Data received (JSON responses)
    ↓
Update DOM with data
    ├─ updateEmotionDisplay()
    ├─ updateTaskStats()
    ├─ updateEngagementDisplay()
    └─ updateRecommendations()
    ↓
Display fully rendered dashboard
    ↓
Auto-refresh triggers (30s - 2 min)
    ↓
Repeat from "API calls made"
```

---

## Error Handling

All API service classes include try-catch blocks:

```javascript
static async fetchAllTasks() {
    try {
        const response = await fetch('/tasks/api/tasks/?limit=100');
        if (response.ok) {
            const data = await response.json();
            return data.status === 'success' ? data.data : [];
        }
    } catch (error) {
        console.error('Error fetching tasks:', error);
    }
    return [];
}
```

**Fallbacks**:
- Empty arrays `[]` if no data
- `null` if analytics fail
- Graceful display of "No data" messages
- Console error logging for debugging

---

## Auto-Refresh Schedules

| Template | Component | Interval |
|----------|-----------|----------|
| Companion Dashboard | Emotion data | 30 seconds |
| Enhanced Dashboard | Full dashboard | On-demand (button) |
| Enhanced Dashboard | Auto refresh | 1 minute |
| Task List | All tasks | 2 minutes |

---

## Response Format Reference

### /emotion_detection/api/user/complete/
```json
{
    "status": "success",
    "data": {
        "profile": { /* user account data */ },
        "emotions": { /* current + history */ },
        "productivity": { /* task stats */ },
        "engagement": { /* points, streaks, achievements */ },
        "companion": { /* conversations, journals */ },
        "mental_health": { /* crisis status, burnout */ }
    }
}
```

### /tasks/api/tasks/analytics/
```json
{
    "status": "success",
    "data": {
        "overview": {
            "total_tasks": 25,
            "completed_tasks": 15,
            "pending_tasks": 10,
            "in_progress_tasks": 0,
            "completion_rate": 60.0
        },
        "insights": [ /* 3-4 contextual insights */ ],
        "patterns": { /* emotion transitions, trends */ }
    }
}
```

### /tasks/api/tasks/recommendations/
```json
{
    "status": "success",
    "data": {
        "recommendations": [
            {
                "task_id": 5,
                "task_title": "Review Project Proposal",
                "match_score": 0.92,
                "reason": "You tend to feel focused when working on this task"
            }
            // ... more recommendations
        ]
    }
}
```

---

## Browser Console Debugging

Monitor API calls in browser DevTools:

```javascript
// Check loaded data
console.log('All Tasks:', allTasks);
console.log('User Data:', userData);

// Monitor API responses
fetch('/emotion_detection/api/user/complete/')
    .then(r => r.json())
    .then(data => console.log('Complete Profile:', data));
```

---

## Performance Considerations

1. **Parallel Requests**: All independent API calls happen simultaneously
2. **Client-side Filtering**: No server roundtrips for filter operations
3. **Caching**: Browser caches API responses (consider adding cache headers)
4. **Lazy Loading**: Only load data when needed
5. **Throttling**: Auto-refresh intervals prevent excessive API calls

---

## Troubleshooting

### 🔴 "No data displayed"
- Check browser console for fetch errors
- Verify API endpoints are responding: `curl /emotion_detection/api/user/complete/`
- Check CSRF token is being sent with POST requests
- Verify user authentication (401 Unauthorized indicates auth issue)

### 🔴 "Emotion data not updating"
- Check auto-refresh interval in console
- Verify emotion API is returning current data
- Check database has emotion records

### 🔴 "Task list empty"
- Verify user has created tasks
- Check `/tasks/api/tasks/` responds with data
- Verify task status is 'pending' if filtered

### 🔴 "Styling looks broken"
- Verify Bootstrap 5.1.3 CDN loaded
- Check FontAwesome 6.0.0 CDN loaded
- Inspect element styles in DevTools

---

## Integration Checklist

- [x] All templates fetch from new API endpoints
- [x] Real-time data display with auto-refresh
- [x] Error handling with graceful fallbacks
- [x] Emotion emoji mapping working
- [x] Crisis detection alerts display
- [x] Task filtering with client-side search
- [x] Statistics calculated from API data
- [x] Engagement data shows points/streaks/level
- [x] Recommendations display with match scores
- [x] Mental health status visible

---

## Next Steps

1. **Test in browser**: Open dashboard, verify all sections load
2. **Check network tab**: Confirm API calls are successful (200 status)
3. **Verify data**: Compare displayed values with database
4. **Monitor console**: Look for any JavaScript errors
5. **Test filters**: Try status/priority/search filters on task list
6. **Check auto-refresh**: Verify data updates at expected intervals

---

## Support

For questions or issues with template integration:
1. Check browser console for errors
2. Review Network tab in DevTools
3. Verify API endpoints from `FRONTEND_API_REFERENCE.md`
4. Test endpoints directly with curl or Postman
5. Check user authentication status
