from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q
from django.core.files.storage import default_storage
import json
import io

from .companion_models import (
    CompanionProfile, Conversation, Message, JournalEntry,
    LifeCoachingSession, StreakTracker, Achievement, UserAchievement,
    HumanSupportAgent, SupportSession, CrisisDetection, DailyCompanionInteraction
)
from .companion_engine import companion_engine
from tasks.models import Task
import tempfile
import os
from .companion_models import Persona, PersonaVariant
from .forms import PersonaForm, PersonaVariantForm, ProfilePersonaSelectForm

@login_required
def companion_dashboard(request):
    """Unified dashboard for all user data"""
    # Routes to the same unified dashboard template via API
    return render(request, 'dashboard/unified_dashboard.html')

@login_required
def start_conversation(request):
    """Start a new conversation with the AI companion"""
    if request.method == 'POST':
        try:
            conversation_type = request.POST.get('conversation_type', 'text')
            
            # Create conversation
            conversation = Conversation.objects.create(
                user=request.user,
                session_id=f"{request.user.id}_{timezone.now().timestamp()}",
                conversation_type=conversation_type,
                user_emotion_at_start=request.POST.get('initial_emotion', 'neutral')
            )
            
            return JsonResponse({
                'status': 'success',
                'conversation_id': conversation.session_id,
                'conversation_type': conversation_type
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def send_message(request):
    """Send a message to the AI companion"""
    if request.method == 'POST':
        try:
            conversation_id = request.POST.get('conversation_id')
            message_text = request.POST.get('message', '')
            message_type = request.POST.get('message_type', 'text')
            
            # Get conversation
            conversation = get_object_or_404(
                Conversation, 
                user=request.user, 
                session_id=conversation_id
            )
            
            if message_type == 'text':
                # Process text message
                response = companion_engine.process_text_message(
                    request.user, message_text, conversation_id
                )
                
                return JsonResponse({
                    'status': 'success',
                    'response': response
                })
                
            elif message_type == 'voice':
                # Handle voice message
                audio_file = request.FILES.get('audio_file')
                if audio_file:
                    response = companion_engine.process_voice_message(
                        request.user, audio_file, conversation_id
                    )
                    
                    return JsonResponse({
                        'status': 'success',
                        'response': response
                    })
                    
            elif message_type == 'video':
                # Handle video message
                video_file = request.FILES.get('video_file')
                if video_file:
                    response = companion_engine.process_video_message(
                        request.user, video_file, conversation_id
                    )
                    
                    return JsonResponse({
                        'status': 'success',
                        'response': response
                    })
            
            return JsonResponse({'status': 'error', 'message': 'Invalid message type'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_voice_response(request):
    """Generate voice response for AI text"""
    if request.method == 'POST':
        try:
            text = request.POST.get('text', '')
            conversation_id = request.POST.get('conversation_id')
            
            # Generate voice response
            voice_result = companion_engine.generate_voice_response(
                request.user, text, conversation_id
            )
            
            if 'error' in voice_result:
                return JsonResponse({'status': 'error', 'message': voice_result['error']})
            
            # Return audio data
            return HttpResponse(
                voice_result['audio_data'],
                content_type='audio/wav',
                headers={
                    'Content-Disposition': 'inline; filename="response.wav"',
                    'X-Duration': str(voice_result['duration'])
                }
            )
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def journal_view(request):
    """Memory journal view"""
    user = request.user
    
    # Get journal entries
    journal_entries = JournalEntry.objects.filter(
        user=user
    ).order_by('-entry_date')
    
    # Get emotion statistics
    emotion_stats = {}
    for entry in journal_entries:
        emotion = entry.primary_emotion
        emotion_stats[emotion] = emotion_stats.get(emotion, 0) + 1
    
    # Get today's entry
    today = timezone.now().date()
    today_entry = journal_entries.filter(entry_date=today).first()
    
    context = {
        'journal_entries': journal_entries,
        'emotion_stats': emotion_stats,
        'today_entry': today_entry,
    }
    
    return render(request, 'companion/journal.html', context)

@login_required
def create_journal_entry(request):
    """Create a new journal entry"""
    if request.method == 'POST':
        try:
            user = request.user
            
            # Get or create today's entry
            today = timezone.now().date()
            entry, created = JournalEntry.objects.get_or_create(
                user=user,
                entry_date=today,
                defaults={
                    'entry_type': 'manual',
                    'primary_emotion': request.POST.get('emotion', 'neutral'),
                    'emotion_intensity': float(request.POST.get('intensity', 0.5)),
                    'life_events': json.loads(request.POST.get('life_events', '[]')),
                    'key_moments': request.POST.get('key_moments', ''),
                    'challenges': request.POST.get('challenges', ''),
                    'achievements': request.POST.get('achievements', ''),
                    'personal_reflection': request.POST.get('reflection', ''),
                    'gratitude_notes': request.POST.get('gratitude', ''),
                }
            )
            
            if not created:
                # Update existing entry
                entry.primary_emotion = request.POST.get('emotion', 'neutral')
                entry.emotion_intensity = float(request.POST.get('intensity', 0.5))
                entry.life_events = json.loads(request.POST.get('life_events', '[]'))
                entry.key_moments = request.POST.get('key_moments', '')
                entry.challenges = request.POST.get('challenges', '')
                entry.achievements = request.POST.get('achievements', '')
                entry.personal_reflection = request.POST.get('reflection', '')
                entry.gratitude_notes = request.POST.get('gratitude', '')
                entry.save()
            
            # Generate AI insights
            ai_insights = _generate_journal_insights(user, entry)
            entry.ai_insights = ai_insights
            entry.save()
            
            # Update streak
            _update_streak(user, 'journal')
            
            return JsonResponse({
                'status': 'success',
                'message': 'Journal entry saved',
                'insights': ai_insights
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def coaching_view(request):
    """Life coaching and mentorship view"""
    user = request.user
    
    # Get coaching sessions
    coaching_sessions = LifeCoachingSession.objects.filter(
        user=user
    ).order_by('-session_date')
    
    # Get coaching areas
    coaching_areas = LifeCoachingSession._meta.get_field('coaching_area').choices
    
    # Get progress statistics
    progress_stats = {}
    for area, _ in coaching_areas:
        sessions = coaching_sessions.filter(coaching_area=area)
        if sessions.exists():
            avg_rating = sessions.aggregate(avg=Avg('progress_rating'))['avg'] or 0
            progress_stats[area] = {
                'sessions_count': sessions.count(),
                'avg_rating': avg_rating,
                'last_session': sessions.first().session_date
            }
    
    context = {
        'coaching_sessions': coaching_sessions,
        'coaching_areas': coaching_areas,
        'progress_stats': progress_stats,
    }
    
    return render(request, 'companion/coaching.html', context)

@login_required
def start_coaching_session(request):
    """Start a new coaching session"""
    if request.method == 'POST':
        try:
            user = request.user
            coaching_area = request.POST.get('coaching_area')
            
            # Create coaching session
            session = LifeCoachingSession.objects.create(
                user=user,
                coaching_area=coaching_area,
                session_duration=int(request.POST.get('duration', 30))
            )
            
            # Generate coaching content
            coaching_content = _generate_coaching_content(user, coaching_area)
            
            session.goals_discussed = coaching_content['goals']
            session.strategies_provided = coaching_content['strategies']
            session.ai_coaching_notes = coaching_content['notes']
            session.personalized_advice = coaching_content['advice']
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'content': coaching_content
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def avatar_interaction(request):
    """Video avatar interaction view"""
    user = request.user
    
    # Get user's companion profile
    profile, created = CompanionProfile.objects.get_or_create(user=user)
    
    context = {
        'profile': profile,
        'avatar_styles': ['friendly', 'professional', 'playful', 'spiritual', 'energetic'],
        'available_voices': ['friendly_warm', 'caring_gentle', 'professional', 'energetic', 'calm', 'playful'],
    }
    
    return render(request, 'companion/avatar.html', context)

@login_required
def update_companion_profile(request):
    """Update companion profile and personalization"""
    if request.method == 'POST':
        try:
            user = request.user
            profile = CompanionProfile.objects.get(user=user)
            
            # Update profile
            profile.personality_type = request.POST.get('personality_type')
            profile.communication_tone = request.POST.get('communication_tone')
            profile.companion_name = request.POST.get('companion_name', 'Abigael')
            
            # Voice preferences
            profile.preferred_voice = request.POST.get('preferred_voice')
            profile.voice_speed = float(request.POST.get('voice_speed', 1.0))
            profile.voice_pitch = float(request.POST.get('voice_pitch', 1.0))
            
            # Avatar preferences
            profile.avatar_style = request.POST.get('avatar_style')
            profile.avatar_mood = request.POST.get('avatar_mood')
            
            profile.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Profile updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def human_support_view(request):
    """Human support and crisis intervention view"""
    user = request.user
    
    # Get available support agents
    available_agents = HumanSupportAgent.objects.filter(is_available=True)
    
    # Get user's support sessions
    support_sessions = SupportSession.objects.filter(
        user=user
    ).order_by('-scheduled_time')
    
    # Check for recent crisis detections
    recent_crises = CrisisDetection.objects.filter(
        user=user,
        detected_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-detected_at')
    
    context = {
        'available_agents': available_agents,
        'support_sessions': support_sessions,
        'recent_crises': recent_crises,
    }
    
    return render(request, 'companion/human_support.html', context)

@login_required
def request_human_support(request):
    """Request support from human agent"""
    if request.method == 'POST':
        try:
            user = request.user
            agent_id = request.POST.get('agent_id')
            session_type = request.POST.get('session_type', 'chat')
            scheduled_time = request.POST.get('scheduled_time')
            
            # Get agent
            agent = get_object_or_404(HumanSupportAgent, id=agent_id)
            
            # Parse scheduled time
            if scheduled_time:
                scheduled_datetime = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                scheduled_datetime = timezone.make_aware(scheduled_datetime)
            else:
                scheduled_datetime = timezone.now() + timedelta(minutes=30)
            
            # Create support session
            session = SupportSession.objects.create(
                user=user,
                agent=agent,
                session_type=session_type,
                scheduled_time=scheduled_datetime,
                duration_minutes=30
            )
            
            # Update agent current sessions
            agent.current_sessions += 1
            agent.save()
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'scheduled_time': scheduled_datetime.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# --- Persona admin and user selection views ---
@login_required
def persona_admin_list(request):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    personas = Persona.objects.all().order_by('-created_at')
    return render(request, 'companion/persona_list.html', {'personas': personas})


@login_required
def persona_admin_create(request):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    if request.method == 'POST':
        form = PersonaForm(request.POST)
        if form.is_valid():
            persona = form.save(commit=False)
            persona.created_by = request.user
            persona.save()
            return redirect('persona_admin_list')
    else:
        form = PersonaForm()

    return render(request, 'companion/persona_edit.html', {'form': form, 'create': True})


@login_required
def persona_admin_edit(request, persona_id):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    persona = get_object_or_404(Persona, id=persona_id)

    if request.method == 'POST':
        form = PersonaForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            return redirect('persona_admin_list')
    else:
        form = PersonaForm(instance=persona)

    return render(request, 'companion/persona_edit.html', {'form': form, 'create': False, 'persona': persona})


@login_required
def persona_variant_list(request, persona_id=None):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    if persona_id:
        persona = get_object_or_404(Persona, id=persona_id)
        variants = PersonaVariant.objects.filter(persona=persona).order_by('-id')
    else:
        variants = PersonaVariant.objects.all().order_by('-id')

    return render(request, 'companion/persona_variant_list.html', {'variants': variants, 'persona_id': persona_id})


@login_required
def persona_variant_create(request, persona_id=None):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    initial = {}
    if persona_id:
        initial['persona'] = get_object_or_404(Persona, id=persona_id)

    if request.method == 'POST':
        form = PersonaVariantForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('persona_variant_list')
    else:
        form = PersonaVariantForm(initial=initial)

    return render(request, 'companion/persona_variant_edit.html', {'form': form, 'create': True})


@login_required
def persona_variant_edit(request, variant_id):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    variant = get_object_or_404(PersonaVariant, id=variant_id)

    if request.method == 'POST':
        form = PersonaVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            return redirect('persona_variant_list')
    else:
        form = PersonaVariantForm(instance=variant)

    return render(request, 'companion/persona_variant_edit.html', {'form': form, 'create': False, 'variant': variant})


@login_required
def persona_select(request):
    """Allow a user to view available personas and select one for their companion."""
    user = request.user
    profile, _ = CompanionProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = ProfilePersonaSelectForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('companion_dashboard')
    else:
        form = ProfilePersonaSelectForm(instance=profile)
        # Limit variants to the selected persona for display
        try:
            if profile.selected_persona:
                form.fields['selected_persona_variant'].queryset = profile.selected_persona.variants.filter(is_active=True)
        except Exception:
            form.fields['selected_persona_variant'].queryset = PersonaVariant.objects.none()

    personas = Persona.objects.filter(is_public=True).order_by('name')

    return render(request, 'companion/persona_select.html', {
        'form': form,
        'personas': personas,
        'profile': profile
    })


@login_required
def persona_variants_json(request, persona_id):
    """Return active variants for a persona as JSON."""
    try:
        persona = get_object_or_404(Persona, id=persona_id)
        variants = persona.variants.filter(is_active=True)
        data = []
        for v in variants:
            item = {'id': v.id, 'name': v.name}
            if request.user.is_staff:
                item['edit_url'] = reverse('persona_variant_edit', args=[v.id])
            data.append(item)

        # Also include a create URL for staff users
        create_url = None
        if request.user.is_staff:
            try:
                create_url = reverse('persona_variant_create_for_persona', args=[persona.id])
            except Exception:
                create_url = reverse('persona_variant_create')

        return JsonResponse({'variants': data, 'create_url': create_url})
    except Exception as e:
        return JsonResponse({'variants': [], 'create_url': None})

@login_required
def detect_crisis(request):
    """Crisis detection and escalation"""
    if request.method == 'POST':
        try:
            user = request.user
            message_text = request.POST.get('message', '')
            
            # Detect crisis indicators
            crisis_keywords = [
                'suicidal', 'kill myself', 'end my life', 'want to die',
                'hurt myself', 'self harm', 'addiction', 'abuse',
                'depressed', 'overwhelmed', 'can\'t cope'
            ]
            
            message_lower = message_text.lower()
            detected_keywords = [kw for kw in crisis_keywords if kw in message_lower]
            
            if detected_keywords:
                # Determine severity
                severity = _calculate_crisis_severity(detected_keywords)
                
                # Create crisis detection record
                crisis = CrisisDetection.objects.create(
                    user=user,
                    crisis_type=_classify_crisis_type(detected_keywords),
                    trigger_keywords=detected_keywords,
                    severity_level=severity,
                    escalated_to_human=severity >= 3
                )
                
                # Escalate if needed
                if severity >= 3:
                    _escalate_crisis(crisis, user)
                
                return JsonResponse({
                    'status': 'crisis_detected',
                    'severity': severity,
                    'message': 'Support resources are available'
                })
            
            return JsonResponse({'status': 'no_crisis'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def achievements_view(request):
    """Achievements and gamification view"""
    user = request.user
    
    # Get user's achievements
    user_achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
    
    # Get available achievements
    all_achievements = Achievement.objects.all()
    
    # Get streak tracker
    streak_tracker, created = StreakTracker.objects.get_or_create(user=user)
    
    # Calculate progress for unearned achievements
    achievement_progress = []
    for achievement in all_achievements:
        if not user_achievements.filter(achievement=achievement).exists():
            progress = _calculate_achievement_progress(user, achievement)
            achievement_progress.append({
                'achievement': achievement,
                'progress': progress
            })
    
    context = {
        'user_achievements': user_achievements,
        'achievement_progress': achievement_progress,
        'streak_tracker': streak_tracker,
        'total_points': streak_tracker.points_earned,
        'current_level': streak_tracker.level,
    }
    
    return render(request, 'companion/achievements.html', context)

@login_required
def daily_companion_interaction(request):
    """Handle daily companion interactions (greetings, reminders, reflections)"""
    user = request.user
    today = timezone.now().date()
    
    # Get or create today's interaction
    daily_interaction, created = DailyCompanionInteraction.objects.get_or_create(
        user=user, date=today
    )
    
    if request.method == 'POST':
        try:
            interaction_type = request.POST.get('type')
            
            if interaction_type == 'morning_greeting':
                # Generate morning greeting
                greeting = _generate_morning_greeting(user)
                daily_interaction.morning_greeting_sent = True
                daily_interaction.morning_greeting_response = greeting
                daily_interaction.save()
                
                return JsonResponse({
                    'status': 'success',
                    'greeting': greeting
                })
                
            elif interaction_type == 'evening_reflection':
                # Generate evening reflection
                reflection = _generate_evening_reflection(user)
                daily_interaction.evening_reflection_sent = True
                daily_interaction.evening_reflection_response = reflection
                daily_interaction.save()
                
                return JsonResponse({
                    'status': 'success',
                    'reflection': reflection
                })
                
            elif interaction_type == 'reminder':
                # Handle reminder response
                reminder_id = request.POST.get('reminder_id')
                response = request.POST.get('response', '')
                
                reminders = daily_interaction.reminders_sent or []
                reminders.append({
                    'id': reminder_id,
                    'response': response,
                    'timestamp': timezone.now().isoformat()
                })
                daily_interaction.reminders_sent = reminders
                daily_interaction.save()
                
                return JsonResponse({'status': 'success'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    # Get today's interaction status
    return JsonResponse({
        'status': 'success',
        'morning_greeting_sent': daily_interaction.morning_greeting_sent,
        'evening_reflection_sent': daily_interaction.evening_reflection_sent,
        'reminders_sent': daily_interaction.reminders_sent,
        'interaction_quality': daily_interaction.interaction_quality
    })

# Helper functions
def _generate_journal_insights(user, entry):
    """Generate AI insights for journal entry"""
    try:
        from .empathy_engine import empathy_engine
        
        prompt = f"""
        Analyze this journal entry and provide insights:
        
        Emotion: {entry.primary_emotion} (intensity: {entry.emotion_intensity})
        Key moments: {entry.key_moments}
        Challenges: {entry.challenges}
        Achievements: {entry.achievements}
        
        Provide 2-3 insights about patterns, growth areas, and suggestions.
        Keep it encouraging and actionable.
        """
        
        insights = empathy_engine.generate_empathetic_message('neutral', context=prompt)
        return insights
        
    except Exception as e:
        print(f"Journal insights error: {e}")
        return "Take time to reflect on your experiences. Every challenge is an opportunity for growth."

def _generate_coaching_content(user, coaching_area):
    """Generate coaching content for specific area"""
    coaching_content = {
        'fitness': {
            'goals': ['Establish consistent exercise routine', 'Set realistic fitness targets', 'Track progress regularly'],
            'strategies': ['Start with 15-20 minutes daily', 'Mix cardio and strength training', 'Include flexibility work'],
            'notes': 'Physical activity boosts both physical and mental health',
            'advice': 'Listen to your body and progress at your own pace'
        },
        'career': {
            'goals': ['Define career objectives', 'Develop necessary skills', 'Build professional network'],
            'strategies': ['Set SMART goals', 'Seek mentorship opportunities', 'Continuous learning'],
            'notes': 'Career growth is a marathon, not a sprint',
            'advice': 'Focus on progress, not perfection'
        },
        'studies': {
            'goals': ['Create study schedule', 'Set learning objectives', 'Practice regularly'],
            'strategies': ['Use active learning techniques', 'Take regular breaks', 'Test your knowledge'],
            'notes': 'Learning is most effective when consistent',
            'advice': 'Celebrate small victories along the way'
        },
        'productivity': {
            'goals': ['Optimize time management', 'Minimize distractions', 'Maintain work-life balance'],
            'strategies': ['Use time-blocking', 'Take regular breaks', 'Prioritize important tasks'],
            'notes': 'Productivity is about working smarter, not harder',
            'advice': 'Remember to rest and recharge'
        }
    }
    
    return coaching_content.get(coaching_area, coaching_content['productivity'])

def _update_streak(user, activity_type):
    """Update user streak tracker"""
    streak_tracker, created = StreakTracker.objects.get_or_create(user=user)
    
    today = timezone.now().date()
    
    if streak_tracker.last_activity_date == today:
        # Already updated today
        if activity_type == 'journal':
            streak_tracker.daily_checkins += 1
        elif activity_type == 'conversation':
            streak_tracker.conversations_completed += 1
        elif activity_type == 'coaching':
            streak_tracker.coaching_sessions += 1
    else:
        # New day - check if streak continues
        yesterday = today - timedelta(days=1)
        if streak_tracker.last_activity_date == yesterday:
            streak_tracker.current_streak += 1
        else:
            streak_tracker.current_streak = 1
        
        streak_tracker.last_activity_date = today
        
        # Update longest streak
        if streak_tracker.current_streak > streak_tracker.longest_streak:
            streak_tracker.longest_streak = streak_tracker.current_streak
        
        # Add points
        streak_tracker.points_earned += 10
        if streak_tracker.points_earned >= streak_tracker.level * 100:
            streak_tracker.level += 1
    
    streak_tracker.save()

def _calculate_crisis_severity(keywords):
    """Calculate crisis severity based on keywords"""
    high_severity = ['suicidal', 'kill myself', 'end my life', 'want to die']
    medium_severity = ['hurt myself', 'self harm', 'addiction', 'abuse']
    low_severity = ['depressed', 'overwhelmed', 'can\'t cope']
    
    if any(kw in keywords for kw in high_severity):
        return 4  # High concern
    elif any(kw in keywords for kw in medium_severity):
        return 3  # Moderate concern
    elif any(kw in keywords for kw in low_severity):
        return 2  # Low concern
    else:
        return 1  # Minimal concern

def _classify_crisis_type(keywords):
    """Classify crisis type based on keywords"""
    if any('suicidal' in kw or 'kill myself' in kw or 'end my life' in kw or 'want to die' in kw for kw in keywords):
        return 'suicidal_ideation'
    elif any('hurt myself' in kw or 'self harm' in kw for kw in keywords):
        return 'mental_health'
    elif any('addiction' in kw for kw in keywords):
        return 'addiction'
    elif any('abuse' in kw for kw in keywords):
        return 'abuse'
    else:
        return 'emotional_crisis'

def _escalate_crisis(crisis, user):
    """Escalate crisis to human support"""
    crisis.escalated_to_human = True
    crisis.save()
    
    # Find available crisis specialist
    crisis_agents = HumanSupportAgent.objects.filter(
        role='crisis_specialist',
        is_available=True
    )
    
    if crisis_agents.exists():
        agent = crisis_agents.first()
        
        # Create emergency support session
        SupportSession.objects.create(
            user=user,
            agent=agent,
            session_type='voice',
            scheduled_time=timezone.now(),
            duration_minutes=60
        )
    
    # Implement emergency hotline integration
    if crisis.crisis_severity > 0.8:
        _notify_emergency_contacts(user, crisis)
        _log_emergency_incident(user, crisis)
    
    print(f"Crisis escalated for user {user.username}: {crisis.crisis_type}")

def _notify_emergency_contacts(user, crisis):
    """Notify emergency contacts when crisis detected"""
    from django.core.mail import send_mail
    from emotion_detection.models import EmergencyContact
    
    try:
        contacts = EmergencyContact.objects.filter(user=user, is_active=True)
        
        for contact in contacts:
            email_body = f"""
Emergency Alert: {contact.user.username} may be experiencing a crisis.

Crisis Type: {crisis.crisis_type}
Severity: {crisis.crisis_severity:.2%}
Time: {crisis.detected_at.isoformat()}

Please check on them or contact emergency services if appropriate.
            """
            
            send_mail(
                f'Emergency Alert: {user.username}',
                email_body,
                'noreply@abigaelai.com',
                [contact.contact_email],
                fail_silently=True
            )
    except Exception as e:
        print(f"Error notifying emergency contacts: {e}")

def _log_emergency_incident(user, crisis):
    """Log emergency incidents for review and analytics"""
    from emotion_detection.models import EmergencyIncidentLog
    
    try:
        EmergencyIncidentLog.objects.create(
            user=user,
            crisis_type=crisis.crisis_type,
            severity=crisis.crisis_severity,
            triggered_at=crisis.detected_at,
            action_taken='emergency_contact_notified' if crisis.crisis_severity > 0.8 else 'monitored',
            notes=f"Auto-escalation triggered by crisis detection system"
        )
    except Exception as e:
        print(f"Error logging emergency incident: {e}")

def _calculate_achievement_progress(user, achievement):
    """Calculate progress towards achievement"""
    progress = 0.0
    
    if achievement.achievement_type == 'streak':
        streak_tracker = StreakTracker.objects.get(user=user)
        required_streak = achievement.criteria.get('streak_days', 7)
        progress = min(1.0, streak_tracker.current_streak / required_streak)
    
    elif achievement.achievement_type == 'journal':
        journal_count = JournalEntry.objects.filter(user=user).count()
        required_entries = achievement.criteria.get('entries', 30)
        progress = min(1.0, journal_count / required_entries)
    
    elif achievement.achievement_type == 'coaching':
        coaching_count = LifeCoachingSession.objects.filter(user=user).count()
        required_sessions = achievement.criteria.get('sessions', 10)
        progress = min(1.0, coaching_count / required_sessions)
    
    return progress

def _generate_morning_greeting(user):
    """Generate personalized morning greeting"""
    profile = CompanionProfile.objects.get(user=user)
    
    greetings = {
        'caring_friend': "Good morning! I'm here to support you today. How are you feeling?",
        'supportive_mentor': "Good morning! Ready to make today productive and positive?",
        'intelligent_coach': "Good morning! Let's set some positive intentions for today.",
        'motivational_guide': "Rise and shine! Today is full of possibilities!",
        'empathetic_listener': "Good morning. I'm here to listen whenever you need me."
    }
    
    greeting = greetings.get(profile.personality_type, "Good morning! How can I support you today?")
    
    return f"{profile.companion_name}: {greeting}"

def _generate_evening_reflection(user):
    """Generate personalized evening reflection"""
    profile = CompanionProfile.objects.get(user=user)
    
    # Get today's activities
    today = timezone.now().date()
    conversations = Conversation.objects.filter(
        user=user,
        started_at__date=today
    ).count()
    
    reflections = {
        'caring_friend': "Time to reflect. How was your day? I'm proud of you for showing up.",
        'supportive_mentor': "Let's reflect on today's progress. Every step forward matters.",
        'intelligent_coach': "Evening reflection time. What did you learn about yourself today?",
        'motivational_guide': "Day's end! Let's celebrate your wins and plan for tomorrow.",
        'empathetic_listener': "Evening reflection. I'm here to listen to your thoughts."
    }
    
    reflection = reflections.get(profile.personality_type, "Time to reflect on your day.")
    
    return f"{profile.companion_name}: {reflection}"
