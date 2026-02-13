from django.urls import path
from . import companion_views, life_event_views, api_views, journal_views, intervention_views, biofeedback_views, gamification_views
from . import insights_views
from . import admin_views

urlpatterns = [
    # Companion features
    path('', companion_views.companion_dashboard, name='companion_dashboard'),
    path('start_conversation/', companion_views.start_conversation, name='start_conversation'),
    path('send_message/', companion_views.send_message, name='send_message'),
    path('get_voice_response/', companion_views.get_voice_response, name='get_voice_response'),
    path('journal/', companion_views.journal_view, name='journal_view'),
    path('create_journal_entry/', companion_views.create_journal_entry, name='create_journal_entry'),
    path('coaching/', companion_views.coaching_view, name='coaching_view'),
    path('start_coaching_session/', companion_views.start_coaching_session, name='start_coaching_session'),
    path('avatar/', companion_views.avatar_interaction, name='avatar_interaction'),
    path('update_profile/', companion_views.update_companion_profile, name='update_companion_profile'),
    path('personas/', companion_views.persona_admin_list, name='persona_admin_list'),
    path('personas/create/', companion_views.persona_admin_create, name='persona_admin_create'),
    path('personas/<int:persona_id>/edit/', companion_views.persona_admin_edit, name='persona_admin_edit'),
    path('personas/select/', companion_views.persona_select, name='persona_select'),
    path('personas/variants/', companion_views.persona_variant_list, name='persona_variant_list'),
    path('personas/<int:persona_id>/variants/', companion_views.persona_variant_list, name='persona_variant_list_for_persona'),
    path('personas/variants/create/', companion_views.persona_variant_create, name='persona_variant_create'),
    path('personas/<int:persona_id>/variants/create/', companion_views.persona_variant_create, name='persona_variant_create_for_persona'),
    path('personas/variants/<int:variant_id>/edit/', companion_views.persona_variant_edit, name='persona_variant_edit'),
    path('personas/<int:persona_id>/variants/json/', companion_views.persona_variants_json, name='persona_variants_json'),
    path('human_support/', companion_views.human_support_view, name='human_support_view'),
    path('request_human_support/', companion_views.request_human_support, name='request_human_support'),
    path('detect_crisis/', companion_views.detect_crisis, name='detect_crisis'),
    path('achievements/', companion_views.achievements_view, name='achievements_view'),
    path('daily_interaction/', companion_views.daily_companion_interaction, name='daily_companion_interaction'),
    
    # Multimodal journal and timeline
    path('journal_timeline/', journal_views.journal_timeline, name='journal_timeline'),
    path('journal_create_multimodal/', journal_views.create_journal_entry_multimodal, name='journal_create_multimodal'),
    path('journal/<int:entry_id>/', journal_views.journal_entry_detail, name='journal_entry_detail'),
    path('api/journal_timeline/', journal_views.journal_timeline_json, name='journal_timeline_json'),
    path('api/journal_search/', journal_views.search_journal_entries, name='journal_search'),
    path('api/journal_export/', journal_views.export_journal_entries, name='journal_export'),
    
    # Micro-interventions
    path('interventions/', intervention_views.interventions_dashboard, name='interventions_dashboard'),
    path('interventions/<int:intervention_id>/', intervention_views.intervention_detail, name='intervention_detail'),
    path('interventions/<int:intervention_id>/start/', intervention_views.start_intervention, name='start_intervention'),
    path('interventions/<int:intervention_id>/complete/', intervention_views.complete_intervention, name='complete_intervention'),
    path('interventions/<int:intervention_id>/dismiss/', intervention_views.dismiss_intervention, name='dismiss_intervention'),
    path('interventions/trigger/', intervention_views.trigger_interventions, name='trigger_interventions'),
    path('admin/intervention_rules/', intervention_views.intervention_rules_admin, name='intervention_rules_admin'),
    path('admin/intervention_rules/<int:rule_id>/', intervention_views.intervention_rule_detail, name='intervention_rule_detail'),
    path('admin/intervention_content/', intervention_views.intervention_content_admin, name='intervention_content_admin'),
    path('admin/intervention_templates/', intervention_views.intervention_templates, name='intervention_templates'),
    path('admin/intervention_templates/<int:template_id>/deploy/', intervention_views.deploy_template, name='deploy_template'),
    
    # Biofeedback wearable device integration
    path('biofeedback/', biofeedback_views.biofeedback_dashboard, name='biofeedback_dashboard'),
    path('biofeedback/devices/', biofeedback_views.device_list, name='device_list'),
    path('biofeedback/devices/connect/', biofeedback_views.connect_device, name='connect_device'),
    path('biofeedback/devices/<int:device_id>/', biofeedback_views.device_detail, name='device_detail'),
    path('biofeedback/devices/<int:device_id>/disconnect/', biofeedback_views.disconnect_device, name='disconnect_device'),
    path('biofeedback/daily/<str:date_str>/', biofeedback_views.daily_summary_view, name='daily_summary'),
    path('biofeedback/alerts/', biofeedback_views.alert_dashboard, name='alert_dashboard'),
    path('biofeedback/alerts/<int:alert_id>/acknowledge/', biofeedback_views.acknowledge_alert, name='acknowledge_alert'),
    path('biofeedback/settings/', biofeedback_views.biofeedback_settings, name='biofeedback_settings'),
    path('api/biofeedback/hr/', biofeedback_views.heart_rate_timeline, name='api_hr_timeline'),
    path('api/biofeedback/sleep/', biofeedback_views.sleep_timeline, name='api_sleep_timeline'),
    path('api/biofeedback/stats/', biofeedback_views.biofeedback_statistics, name='api_biofeedback_stats'),
    path('api/biofeedback/emotions/', biofeedback_views.emotion_correlation, name='api_emotion_correlation'),
    
    # Gamification & Habits
    path('gamification/', gamification_views.gamification_dashboard, name='gamification_dashboard'),
    path('gamification/badges/', gamification_views.badges_view, name='badges_view'),
    path('gamification/badges/<int:badge_id>/', gamification_views.badges_view, name='badge_detail'),
    path('gamification/streak/', gamification_views.streak_detail, name='streak_detail'),
    path('gamification/rewards/', gamification_views.reward_shop, name='reward_shop'),
    path('gamification/rewards/<int:reward_id>/redeem/', gamification_views.redeem_reward, name='redeem_reward'),
    path('gamification/leaderboard/', gamification_views.leaderboard_view, name='leaderboard_view'),
    path('gamification/profile/', gamification_views.profile_stats, name='gamification_profile'),
    path('api/gamification/stats/', gamification_views.user_stats_api, name='api_gamification_stats'),
    path('api/gamification/badges/progress/', gamification_views.badges_progress_api, name='api_badges_progress'),
    
    # Insights & Explainability
    path('insights/', insights_views.insights_dashboard, name='insights_dashboard'),
    path('insights/<int:insight_id>/', insights_views.insight_detail, name='insight_detail'),
    path('insights/<int:insight_id>/export/', insights_views.export_insight_json, name='export_insight_json'),
    path('insights/<int:insight_id>/export/csv/', insights_views.export_insight_csv, name='export_insight_csv'),
    path('insights/<int:insight_id>/export/create/', insights_views.create_insight_export, name='create_insight_export'),
    path('insights/exports/<int:export_id>/download/', insights_views.download_insight_export, name='download_insight_export'),

    # Admin exports list/detail (staff-only)
    path('admin/insight_exports/', admin_views.insight_export_list, name='admin_insight_exports'),
    path('admin/insight_exports/<int:export_id>/', admin_views.insight_export_detail, name='admin_insight_export_detail'),
    path('admin/insight_exports/<int:export_id>/regenerate/', admin_views.insight_export_regenerate, name='admin_insight_export_regenerate'),
    
    # Life events and social features
    path('life_events/', life_event_views.life_events_view, name='life_events_view'),
    path('create_life_event/', life_event_views.create_life_event, name='create_life_event'),
    path('event/<int:event_id>/preparation/', life_event_views.get_event_preparation, name='get_event_preparation'),
    path('event/<int:event_id>/followup/', life_event_views.complete_event_followup, name='complete_event_followup'),
    path('music_recommendations/', life_event_views.get_music_recommendations, name='get_music_recommendations'),
    path('music/<int:recommendation_id>/rate/', life_event_views.rate_music_recommendation, name='rate_music_recommendation'),
    path('relationship_insights/', life_event_views.relationship_insights_view, name='relationship_insights_view'),
    path('social_skill/<int:skill_id>/update/', life_event_views.update_social_skill, name='update_social_skill'),
    
    # API endpoints for complete user data
    path('api/user/profile/', api_views.user_profile_data, name='api_user_profile'),
    path('api/user/emotions/', api_views.user_emotion_data, name='api_user_emotions'),
    path('api/user/productivity/', api_views.user_productivity_data, name='api_user_productivity'),
    path('api/user/engagement/', api_views.user_engagement_data, name='api_user_engagement'),
    path('api/user/companion/', api_views.user_companion_data, name='api_user_companion'),
    path('api/user/mental-health/', api_views.user_mental_health_data, name='api_user_mental_health'),
    path('api/user/complete/', api_views.user_complete_profile, name='api_user_complete'),
]
