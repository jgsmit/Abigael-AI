from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q
import json

from .companion_models import CompanionProfile, DailyCompanionInteraction
from .life_event_models import (
    LifeEvent, EventPreparation, EventFollowUp, 
    MusicRecommendation, RelationshipInsight, SocialSkillDevelopment
)
from .companion_engine import companion_engine
from .empathy_engine import empathy_engine
import openai

@login_required
def life_events_view(request):
    """Life events management dashboard"""
    user = request.user
    
    # Get upcoming events
    upcoming_events = LifeEvent.objects.filter(
        user=user,
        event_date__gte=timezone.now(),
        status__in=['scheduled', 'preparing']
    ).order_by('event_date')[:10]
    
    # Get recent events for follow-up
    recent_events = LifeEvent.objects.filter(
        user=user,
        event_date__lte=timezone.now() - timedelta(hours=2),
        status='completed'
    ).order_by('-event_date')[:5]
    
    # Get relationship insights
    relationship_insights = RelationshipInsight.objects.filter(
        user=user
    ).order_by('-interaction_date')[:5]
    
    # Get music recommendations
    recent_music = MusicRecommendation.objects.filter(
        user=user
    ).order_by('-created_at')[:10]
    
    context = {
        'upcoming_events': upcoming_events,
        'recent_events': recent_events,
        'relationship_insights': relationship_insights,
        'music_recommendations': recent_music,
    }
    
    return render(request, 'companion/life_events.html', context)

@login_required
def create_life_event(request):
    """Create a new life event"""
    if request.method == 'POST':
        try:
            user = request.user
            
            # Parse event data
            event_data = json.loads(request.body)
            
            # Create life event
            event = LifeEvent.objects.create(
                user=user,
                event_type=event_data.get('event_type'),
                title=event_data.get('title'),
                description=event_data.get('description', ''),
                event_date=datetime.fromisoformat(event_data.get('event_date')),
                duration_minutes=int(event_data.get('duration_minutes', 60)),
                location=event_data.get('location', ''),
                participants=event_data.get('participants', []),
                expected_emotion=event_data.get('expected_emotion', 'neutral')
            )
            
            # Generate AI preparation advice
            preparation_advice = _generate_event_preparation(user, event)
            event.ai_preparation_advice = preparation_advice
            event.save()
            
            # Create preparation record
            preparation = EventPreparation.objects.create(
                user=user,
                life_event=event,
                preparation_type=f"{event.event_type}_prep"
            )
            
            # Generate specific preparation content
            _populate_preparation_content(preparation, event)
            preparation.save()
            
            return JsonResponse({
                'status': 'success',
                'event_id': event.id,
                'preparation_advice': preparation_advice
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_event_preparation(request, event_id):
    """Get AI-generated preparation for specific event"""
    try:
        user = request.user
        event = get_object_or_404(LifeEvent, id=event_id, user=user)
        
        # Get or create preparation
        preparation, created = EventPreparation.objects.get_or_create(
            user=user,
            life_event=event,
            preparation_type=f"{event.event_type}_prep"
        )
        
        if created:
            _populate_preparation_content(preparation, event)
            preparation.save()
        
        return JsonResponse({
            'status': 'success',
            'preparation': {
                'talking_points': preparation.talking_points,
                'conversation_starters': preparation.conversation_starters,
                'confidence_boosters': preparation.confidence_boosters,
                'anxiety_reduction_tips': preparation.anxiety_reduction_tips,
                'outfit_suggestions': preparation.outfit_suggestions,
                'timing_advice': preparation.timing_advice
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def complete_event_followup(request, event_id):
    """Handle post-event follow-up and analysis"""
    if request.method == 'POST':
        try:
            user = request.user
            event = get_object_or_404(LifeEvent, id=event_id, user=user)
            
            # Parse follow-up data
            followup_data = json.loads(request.body)
            
            # Update event with outcome
            event.actual_emotion_before = followup_data.get('emotion_before', '')
            event.actual_emotion_after = followup_data.get('emotion_after', '')
            event.outcome_rating = int(followup_data.get('outcome_rating', 3))
            event.outcome_notes = followup_data.get('outcome_notes', '')
            event.status = 'completed'
            event.save()
            
            # Create follow-up record
            followup = EventFollowUp.objects.create(
                user=user,
                life_event=event,
                follow_up_triggered=True,
                follow_up_time=timezone.now(),
                user_feeling=followup_data.get('current_feeling', ''),
                user_satisfaction=int(followup_data.get('satisfaction', 3)),
                user_feedback=followup_data.get('feedback', '')
            )
            
            # Generate AI analysis and recommendations
            ai_analysis = _generate_event_analysis(user, event, followup_data)
            followup.ai_emotion_analysis = ai_analysis['emotion_analysis']
            followup.ai_performance_insights = ai_analysis['performance_insights']
            followup.ai_improvement_areas = ai_analysis['improvement_areas']
            followup.ai_encouragement = ai_analysis['encouragement']
            followup.recommended_actions = ai_analysis['recommended_actions']
            followup.recommended_music = ai_analysis['music_recommendations']
            followup.save()
            
            # Check if human support is needed
            if int(followup_data.get('satisfaction', 3)) <= 2:
                followup.needs_human_support = True
                followup.support_type_requested = 'emotional_support'
                followup.save()
            
            return JsonResponse({
                'status': 'success',
                'analysis': ai_analysis,
                'needs_support': followup.needs_human_support
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_music_recommendations(request):
    """Get mood-based music recommendations"""
    if request.method == 'POST':
        try:
            user = request.user
            
            # Parse request data
            music_data = json.loads(request.body)
            current_emotion = music_data.get('current_emotion', 'neutral')
            activity_context = music_data.get('activity_context', 'relaxing')
            
            # Generate music recommendations
            recommendations = _generate_music_recommendations(user, current_emotion, activity_context)
            
            # Save recommendation record
            music_rec = MusicRecommendation.objects.create(
                user=user,
                current_emotion=current_emotion,
                activity_context=activity_context,
                genre=recommendations['primary_genre'],
                mood=recommendations['mood'],
                energy_level=recommendations['energy_level'],
                song_suggestions=recommendations['songs'],
                playlist_recommendations=recommendations['playlists']
            )
            
            return JsonResponse({
                'status': 'success',
                'recommendations': recommendations,
                'recommendation_id': music_rec.id
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def rate_music_recommendation(request, recommendation_id):
    """Rate and provide feedback on music recommendations"""
    if request.method == 'POST':
        try:
            user = request.user
            music_rec = get_object_or_404(MusicRecommendation, id=recommendation_id, user=user)
            
            # Parse rating data
            rating_data = json.loads(request.body)
            
            # Update recommendation with feedback
            music_rec.user_rating = int(rating_data.get('rating', 3))
            music_rec.user_skipped = rating_data.get('skipped', False)
            music_rec.user_listened_duration = int(rating_data.get('listened_duration', 0))
            music_rec.save()
            
            # Generate new recommendations based on feedback
            if music_rec.user_rating >= 3:
                # User liked it - find similar music
                new_recommendations = _generate_similar_music(user, music_rec)
            else:
                # User didn't like it - try different approach
                new_recommendations = _generate_alternative_music(user, music_rec.current_emotion)
            
            return JsonResponse({
                'status': 'success',
                'new_recommendations': new_recommendations
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def relationship_insights_view(request):
    """Relationship insights and social skills development"""
    user = request.user
    
    # Get relationship insights
    insights = RelationshipInsight.objects.filter(user=user).order_by('-interaction_date')[:10]
    
    # Get social skills development
    social_skills = SocialSkillDevelopment.objects.filter(user=user)
    
    # Calculate relationship metrics
    relationship_stats = {}
    for insight in insights:
        relationship_type = insight.relationship_type
        if relationship_type not in relationship_stats:
            relationship_stats[relationship_type] = {
                'count': 0,
                'avg_strength': 0,
                'recent_emotions': []
            }
        
        relationship_stats[relationship_type]['count'] += 1
        if insight.relationship_strength_rating:
            relationship_stats[relationship_type]['avg_strength'] += insight.relationship_strength_rating
        
        if insight.user_emotion_after:
            relationship_stats[relationship_type]['recent_emotions'].append(insight.user_emotion_after)
    
    # Calculate averages
    for rel_type in relationship_stats:
        if relationship_stats[rel_type]['count'] > 0:
            relationship_stats[rel_type]['avg_strength'] /= relationship_stats[rel_type]['count']
    
    context = {
        'relationship_insights': insights,
        'social_skills': social_skills,
        'relationship_stats': relationship_stats,
    }
    
    return render(request, 'companion/relationship_insights.html', context)

@login_required
def update_social_skill(request, skill_id):
    """Update social skill progress"""
    if request.method == 'POST':
        try:
            user = request.user
            skill = get_object_or_404(SocialSkillDevelopment, id=skill_id, user=user)
            
            # Parse update data
            update_data = json.loads(request.body)
            
            # Update skill progress
            skill.current_level = int(update_data.get('current_level', skill.current_level))
            skill.practice_sessions += int(update_data.get('practice_sessions', 0))
            skill.improvement_notes = update_data.get('improvement_notes', skill.improvement_notes)
            
            # Generate new AI coaching content
            if skill.current_level > skill.target_level:
                skill.target_level = skill.current_level + 1
            
            ai_coaching = _generate_skill_coaching(user, skill)
            skill.ai_skill_assessment = ai_coaching['assessment']
            skill.ai_practice_exercises = ai_coaching['exercises']
            skill.ai_improvement_plan = ai_coaching['plan']
            skill.save()
            
            return JsonResponse({
                'status': 'success',
                'coaching': ai_coaching,
                'level_up': skill.current_level > int(update_data.get('previous_level', skill.current_level))
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# Helper functions
def _generate_event_preparation(user, event):
    """Generate AI preparation advice for events"""
    try:
        prompt = f"""
        Generate preparation advice for a {event.event_type} titled "{event.title}".
        
        Event details:
        - Type: {event.event_type}
        - Description: {event.description}
        - Duration: {event.duration_minutes} minutes
        - Location: {event.location}
        - Participants: {event.participants}
        
        Provide practical, encouraging advice covering:
        1. Mental preparation and confidence building
        2. Conversation topics or talking points
        3. Anxiety reduction techniques
        4. Timing and logistics tips
        
        Keep it supportive and actionable. Max 200 words.
        """
        
        response = empathy_engine.generate_empathetic_message('neutral', context=prompt)
        return response
        
    except Exception as e:
        print(f"Event preparation error: {e}")
        return "Take a few deep breaths and remember you're prepared. You've got this!"

def _populate_preparation_content(preparation, event):
    """Populate preparation content based on event type"""
    if event.event_type == 'meeting':
        preparation.talking_points = [
            "Key project updates",
            "Questions for team members",
            "Action items from last meeting"
        ]
        preparation.conversation_starters = [
            "Great to see everyone. Let's start with...",
            "I'd like to share some progress on..."
        ]
        preparation.confidence_boosters = [
            "Review your notes one more time",
            "Remember your expertise in this area",
            "Take 3 deep breaths before speaking"
        ]
        
    elif event.event_type == 'date':
        preparation.talking_points = [
            "Recent interesting experiences",
            "Hobbies and passions",
            "Future goals and dreams"
        ]
        preparation.conversation_starters = [
            "I've been meaning to ask you about...",
            "Tell me more about your experience with..."
        ]
        preparation.confidence_boosters = [
            "Focus on connection, not perfection",
            "Remember they want to get to know you",
            "Be genuinely curious about them"
        ]
        
    elif event.event_type == 'interview':
        preparation.talking_points = [
            "Your key strengths",
            "Relevant experience",
            "Questions about the role",
            "Company research insights"
        ]
        preparation.conversation_starters = [
            "Thank you for taking the time to meet with me",
            "I'm excited about this opportunity because..."
        ]
        preparation.confidence_boosters = [
            "You were chosen for a reason",
            "Practice your STAR method responses",
            "Research shows preparation reduces anxiety by 40%"
        ]
    
    # Add general anxiety reduction tips
    preparation.anxiety_reduction_tips = [
        "5-4-3-2-1 breathing technique",
        "Visualize successful outcomes",
        "Power pose for 2 minutes beforehand",
        "Listen to calming music on the way"
    ]

def _generate_event_analysis(user, event, followup_data):
    """Generate AI analysis of event outcomes"""
    try:
        prompt = f"""
        Analyze this event outcome and provide supportive insights:
        
        Event: {event.title} ({event.event_type})
        Expected emotion: {event.expected_emotion}
        Actual emotion before: {followup_data.get('emotion_before')}
        Actual emotion after: {followup_data.get('emotion_after')}
        Outcome rating: {followup_data.get('outcome_rating')}/6
        User feedback: {followup_data.get('feedback')}
        
        Provide:
        1. Emotional pattern analysis
        2. Performance insights (what went well)
        3. Specific improvement areas
        4. Encouraging message
        5. 3 actionable next steps
        6. Music recommendations for current mood
        
        Be empathetic, constructive, and supportive. Max 300 words.
        """
        
        # Use empathy engine for analysis
        analysis_text = empathy_engine.generate_empathetic_message(
            followup_data.get('emotion_after', 'neutral'), 
            context=prompt
        )
        
        # Parse and structure the analysis
        return {
            'emotion_analysis': f"Emotion shifted from {followup_data.get('emotion_before')} to {followup_data.get('emotion_after')}",
            'performance_insights': "You showed courage and growth in this situation.",
            'improvement_areas': [
                "Practice deep breathing before high-stress events",
                "Prepare 2-3 conversation starters in advance",
                "Set realistic emotional expectations"
            ],
            'encouragement': "Every experience is a stepping stone. You're learning and growing!",
            'recommended_actions': [
                "Reflect on what you learned about yourself",
                "Practice self-compassion for the outcome",
                "Prepare differently for similar future events"
            ],
            'music_recommendations': _generate_mood_music(followup_data.get('emotion_after', 'neutral'))
        }
        
    except Exception as e:
        print(f"Event analysis error: {e}")
        return {
            'emotion_analysis': "Emotional patterns detected",
            'performance_insights': "You showed up and participated - that's what matters",
            'improvement_areas': ["Continue practicing self-awareness"],
            'encouragement': "Growth comes from experience. Keep going!",
            'recommended_actions': ["Take time to reflect", "Be kind to yourself"],
            'music_recommendations': []
        }

def _generate_music_recommendations(user, emotion, activity):
    """Generate music recommendations based on emotion and activity"""
    music_mapping = {
        'stressed': {
            'working': {'genre': 'Ambient', 'mood': 'Calming', 'energy': 2},
            'relaxing': {'genre': 'Classical', 'mood': 'Peaceful', 'energy': 1},
            'post_event': {'genre': 'Lo-fi', 'mood': 'Gentle', 'energy': 2}
        },
        'happy': {
            'working': {'genre': 'Pop', 'mood': 'Uplifting', 'energy': 4},
            'relaxing': {'genre': 'Indie', 'mood': 'Bright', 'energy': 3},
            'post_event': {'genre': 'Dance', 'mood': 'Celebratory', 'energy': 5}
        },
        'sad': {
            'working': {'genre': 'Acoustic', 'mood': 'Gentle', 'energy': 2},
            'relaxing': {'genre': 'Soul', 'mood': 'Comforting', 'energy': 2},
            'post_event': {'genre': 'Ambient', 'mood': 'Supportive', 'energy': 1}
        },
        'focused': {
            'working': {'genre': 'Electronic', 'mood': 'Driving', 'energy': 4},
            'studying': {'genre': 'Classical', 'mood': 'Concentration', 'energy': 3},
            'preparing_event': {'genre': 'Instrumental', 'mood': 'Focused', 'energy': 3}
        }
    }
    
    # Get recommendation based on emotion and activity
    base_rec = music_mapping.get(emotion, music_mapping['neutral'])
    rec = base_rec.get(activity, base_rec['working'])
    
    # Generate song suggestions (mock data - in real app would use music API)
    songs = [
        f"{rec['genre']} Focus Mix - Track 1",
        f"{rec['genre']} Focus Mix - Track 2",
        f"{rec['genre']} Focus Mix - Track 3"
    ]
    
    playlists = [
        f"{rec['mood']} {rec['genre']} Playlist",
        f"Productive {rec['genre']} Session",
        f"Emotional Support {rec['genre']}"
    ]
    
    return {
        'primary_genre': rec['genre'],
        'mood': rec['mood'],
        'energy_level': rec['energy'],
        'songs': songs,
        'playlists': playlists,
        'artists': [f"Various {rec['genre']} Artists"]
    }

def _generate_mood_music(emotion):
    """Generate basic music recommendations for mood"""
    mood_music = {
        'stressed': ['Calming Piano', 'Nature Sounds', 'Meditation Music'],
        'happy': ['Upbeat Pop', 'Feel-Good Classics', 'Dance Hits'],
        'sad': ['Comforting Acoustic', 'Gentle Classical', 'Soothing Jazz'],
        'focused': ['Concentration Electronic', 'Study Classical', 'Ambient Focus'],
        'neutral': ['Light Indie', 'Soft Rock', 'Easy Listening']
    }
    return mood_music.get(emotion, mood_music['neutral'])

def _generate_similar_music(user, previous_rec):
    """Generate similar music recommendations"""
    return {
        'songs': [
            f"More {previous_rec.genre} - Similar Vibe",
            f"{previous_rec.genre} Discovery - Track 1"
        ],
        'playlists': [
            f"More {previous_rec.mood} {previous_rec.genre}",
            f"Expanded {previous_rec.genre} Collection"
        ]
    }

def _generate_alternative_music(user, emotion):
    """Generate alternative music recommendations"""
    alternatives = {
        'stressed': ['Jazz', 'Nature Sounds', 'Chillhop'],
        'happy': ['Folk', 'Reggae', 'Electronic'],
        'sad': ['Blues', 'Classical', 'Ambient'],
        'focused': ['Minimal Techno', 'Baroque', 'Soundtrack']
    }
    
    alt_genres = alternatives.get(emotion, ['Indie', 'Pop', 'Rock'])
    
    return {
        'songs': [f"{genre} Alternative Mix" for genre in alt_genres],
        'playlists': [f"Different {genre} Experience" for genre in alt_genres]
    }

def _generate_skill_coaching(user, skill):
    """Generate AI coaching for social skill development"""
    coaching_prompts = {
        'communication': "Focus on active listening and clear expression",
        'empathy': "Practice perspective-taking and emotional validation",
        'confidence': "Use power poses and positive self-talk",
        'listening': "Maintain eye contact and ask clarifying questions",
        'conflict_resolution': "Use 'I feel' statements and seek win-win solutions"
    }
    
    base_coaching = coaching_prompts.get(skill.skill_category, "Practice regularly and stay positive")
    
    return {
        'assessment': f"Your {skill.skill_category} skills are developing well. Current level {skill.current_level} shows good progress.",
        'exercises': [
            f"Daily {skill.skill_category} practice for 10 minutes",
            f"Role-play scenarios related to {skill.skill_category}",
            f"Watch and learn from {skill.skill_category} experts"
        ],
        'plan': f"To reach level {skill.target_level}, focus on: {base_coaching}. Practice consistently and track your progress."
    }
