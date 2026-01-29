from django.urls import path
from . import views
from . import enhanced_views
from . import api_views

urlpatterns = [
    # Main views
    path('', enhanced_views.dashboard, name='dashboard'),
    path('hud/', enhanced_views.hud_dashboard, name='hud_dashboard'),
    path('tasks/', enhanced_views.task_list, name='task_list'),
    path('tasks/create/', enhanced_views.create_task, name='create_task'),
    path('tasks/<int:task_id>/update/', enhanced_views.update_task, name='update_task'),
    path('tasks/<int:task_id>/delete/', enhanced_views.delete_task, name='delete_task'),
    path('analytics/', enhanced_views.emotion_analytics, name='emotion_analytics'),
    path('biofeedback/', enhanced_views.biofeedback_settings, name='biofeedback_settings'),
    path('chat/', enhanced_views.motivation_chat, name='motivation_chat'),
    
    # Enhanced AJAX endpoints
    path('api/start-multimodal-detection/', enhanced_views.start_multimodal_detection, name='start_multimodal_detection'),
    path('api/stop-multimodal-detection/', enhanced_views.stop_multimodal_detection, name='stop_multimodal_detection'),
    path('api/comprehensive-emotion/', enhanced_views.get_comprehensive_emotion, name='get_comprehensive_emotion'),
    path('api/empathetic-message/', enhanced_views.get_empathetic_message, name='get_empathetic_message'),
    path('api/suggest-break/', enhanced_views.suggest_break, name='suggest_break'),
    path('api/motivation-chat/', enhanced_views.motivation_chat, name='motivation_chat_api'),
    
    # Legacy endpoints for compatibility
    path('api/start-emotion-detection/', views.start_emotion_detection, name='start_emotion_detection'),
    path('api/stop-emotion-detection/', views.stop_emotion_detection, name='stop_emotion_detection'),
    path('api/current-emotion/', views.get_current_emotion, name='get_current_emotion'),
    
    # Comprehensive task API endpoints
    path('api/tasks/', api_views.get_all_tasks, name='api_all_tasks'),
    path('api/tasks/<int:task_id>/', api_views.get_task_details, name='api_task_details'),
    path('api/tasks/analytics/', api_views.get_task_analytics, name='api_task_analytics'),
    path('api/tasks/recommendations/', api_views.get_task_recommendations, name='api_task_recommendations'),
]
