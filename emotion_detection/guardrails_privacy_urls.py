"""
URL Routes for Mental Health Guardrails and Privacy Features
"""

from django.urls import path
from emotion_detection import guardrails_privacy_views

app_name = 'guardrails_privacy'

urlpatterns = [
    # ===== MENTAL HEALTH GUARDRAILS ROUTES =====
    
    # Dashboard
    path('mental-health/', 
         guardrails_privacy_views.mental_health_dashboard, 
         name='mental_health_dashboard'),
    
    # API Endpoints
    path('api/burnout-warning/', 
         guardrails_privacy_views.burnout_warning_api, 
         name='burnout_warning_api'),
    
    path('api/emotional-spiral/', 
         guardrails_privacy_views.emotional_spiral_detection_api, 
         name='emotional_spiral_api'),
    
    path('api/grounding-exercise/recommend/', 
         guardrails_privacy_views.recommend_grounding_exercise, 
         name='recommend_grounding_exercise'),
    
    path('api/grounding-exercise/log-completion/', 
         guardrails_privacy_views.log_exercise_completion, 
         name='log_exercise_completion'),
    
    path('api/crisis-resources/', 
         guardrails_privacy_views.crisis_resources_api, 
         name='crisis_resources'),
    
    # History
    path('mental-health/history/', 
         guardrails_privacy_views.MentalHealthHistoryListView.as_view(), 
         name='mental_health_history'),
    
    # ===== PRIVACY ROUTES =====
    
    # Dashboard
    path('privacy/', 
         guardrails_privacy_views.privacy_dashboard, 
         name='privacy_dashboard'),
    
    path('privacy/settings/', 
         guardrails_privacy_views.PrivacySettingsView.as_view(), 
         name='privacy_settings'),
    
    # API Endpoints
    path('api/privacy/update-settings/', 
         guardrails_privacy_views.update_privacy_settings, 
         name='update_privacy_settings'),
    
    path('api/privacy/encryption-status/', 
         guardrails_privacy_views.encryption_status_api, 
         name='encryption_status'),
    
    path('api/privacy/audit-log/', 
         guardrails_privacy_views.audit_log_api, 
         name='audit_log'),
    
    path('api/privacy/data-export/', 
         guardrails_privacy_views.data_export_api, 
         name='data_export'),
    
    path('api/privacy/request-deletion/', 
         guardrails_privacy_views.request_data_deletion, 
         name='request_deletion'),
    
    # On-Device ML
    path('api/privacy/enable-on-device-ml/', 
         guardrails_privacy_views.enable_on_device_ml, 
         name='enable_on_device_ml'),
    
    # Federated Learning
    path('api/privacy/enroll-federated-learning/', 
         guardrails_privacy_views.enroll_federated_learning, 
         name='enroll_federated_learning'),
    
    # Explainable AI
    path('api/ai-insights/', 
         guardrails_privacy_views.explainable_ai_insights, 
         name='ai_insights'),
    
    path('api/ai-insights/rate/', 
         guardrails_privacy_views.rate_ai_explanation, 
         name='rate_ai_insight'),
]
