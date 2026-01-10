from django.urls import path
from . import companion_views, life_event_views

urlpatterns = [
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
    path('human_support/', companion_views.human_support_view, name='human_support_view'),
    path('request_human_support/', companion_views.request_human_support, name='request_human_support'),
    path('detect_crisis/', companion_views.detect_crisis, name='detect_crisis'),
    path('achievements/', companion_views.achievements_view, name='achievements_view'),
    path('daily_interaction/', companion_views.daily_companion_interaction, name='daily_companion_interaction'),
    
    # Life events and social features
    path('life_events/', life_event_views.life_events_view, name='life_events_view'),
    path('create_life_event/', life_event_views.create_life_event, name='create_life_event'),
    path('event/<int:event_id>/preparation/', life_event_views.get_event_preparation, name='get_event_preparation'),
    path('event/<int:event_id>/followup/', life_event_views.complete_event_followup, name='complete_event_followup'),
    path('music_recommendations/', life_event_views.get_music_recommendations, name='get_music_recommendations'),
    path('music/<int:recommendation_id>/rate/', life_event_views.rate_music_recommendation, name='rate_music_recommendation'),
    path('relationship_insights/', life_event_views.relationship_insights_view, name='relationship_insights_view'),
    path('social_skill/<int:skill_id>/update/', life_event_views.update_social_skill, name='update_social_skill'),
]
