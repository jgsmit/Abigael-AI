"""Views for multimodal journaling and emotional timeline."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import json

from .companion_models import JournalEntry, JournalMedia
from .forms import JournalEntryForm


@login_required
def journal_timeline(request):
    """View emotional timeline with journal entries."""
    user = request.user
    
    # Get date range filter
    days_back = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days_back)
    
    # Get entries
    entries = JournalEntry.objects.filter(
        user=user,
        entry_date__gte=start_date,
        is_private=True  # Only private entries shown to user
    ).order_by('-entry_date')
    
    # Emotion frequency
    emotion_freq = {}
    for e in entries:
        emotion_freq[e.primary_emotion] = emotion_freq.get(e.primary_emotion, 0) + 1
    
    # Secondary emotions
    all_secondary = []
    for e in entries:
        all_secondary.extend(e.secondary_emotions)
    
    context = {
        'entries': entries,
        'days_back': days_back,
        'emotion_frequency': emotion_freq,
        'secondary_emotions': all_secondary,
    }
    
    return render(request, 'companion/journal_timeline.html', context)


@login_required
def create_journal_entry_multimodal(request):
    """Create a journal entry with multimodal support."""
    if request.method == 'POST':
        try:
            user = request.user
            today = timezone.now().date()
            
            # Get or create today's entry
            entry, created = JournalEntry.objects.get_or_create(
                user=user,
                entry_date=today,
                defaults={
                    'entry_type': request.POST.get('entry_type', 'manual'),
                    'primary_emotion': request.POST.get('emotion', 'neutral'),
                    'emotion_intensity': float(request.POST.get('intensity', 0.5)),
                }
            )
            
            if not created:
                entry.primary_emotion = request.POST.get('emotion', 'neutral')
                entry.emotion_intensity = float(request.POST.get('intensity', 0.5))
                entry.entry_type = request.POST.get('entry_type', 'manual')
            
            # Text and reflection
            entry.personal_reflection = request.POST.get('reflection', '')
            entry.emotion_notes = request.POST.get('emotion_notes', '')
            entry.gratitude_notes = request.POST.get('gratitude', '')
            
            # Secondary emotions
            secondary = request.POST.get('secondary_emotions', '[]')
            try:
                entry.secondary_emotions = json.loads(secondary)
            except:
                entry.secondary_emotions = []
            
            # Tags
            tags = request.POST.get('tags', '').split(',')
            entry.tags = [t.strip() for t in tags if t.strip()]
            
            # Life events
            entry.life_events = json.loads(request.POST.get('life_events', '[]'))
            entry.key_moments = request.POST.get('key_moments', '')
            entry.challenges = request.POST.get('challenges', '')
            entry.achievements = request.POST.get('achievements', '')
            
            entry.save()
            
            # Handle media files
            if 'media' in request.FILES:
                for media_file in request.FILES.getlist('media'):
                    # Detect media type
                    content_type = media_file.content_type
                    if content_type.startswith('image'):
                        media_type = 'image'
                        entry.has_images = True
                    elif content_type.startswith('audio'):
                        media_type = 'audio'
                        entry.has_audio = True
                    elif content_type.startswith('video'):
                        media_type = 'video'
                        entry.has_video = True
                    else:
                        continue
                    
                    media = JournalMedia.objects.create(
                        journal_entry=entry,
                        media_type=media_type,
                        file=media_file,
                        file_size_bytes=media_file.size
                    )
            
            entry.save()
            
            return JsonResponse({
                'status': 'success',
                'entry_id': entry.id,
                'message': 'Journal entry created'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def journal_entry_detail(request, entry_id):
    """View a single journal entry with media."""
    entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
    media = entry.media.all()
    
    context = {
        'entry': entry,
        'media': media,
    }
    
    return render(request, 'companion/journal_entry_detail.html', context)


@login_required
def journal_timeline_json(request):
    """API endpoint for emotional timeline data."""
    try:
        user = request.user
        days_back = int(request.GET.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days_back)
        
        entries = JournalEntry.objects.filter(
            user=user,
            entry_date__gte=start_date,
            is_private=True
        ).order_by('-entry_date')
        
        data = []
        for e in entries:
            data.append({
                'id': e.id,
                'date': str(e.entry_date),
                'emotion': e.primary_emotion,
                'intensity': e.emotion_intensity,
                'entry_type': e.entry_type,
                'has_media': e.has_images or e.has_audio or e.has_video,
                'tags': e.tags,
            })
        
        return JsonResponse({'entries': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def search_journal_entries(request):
    """Search journal entries by emotion, tags, date range."""
    try:
        user = request.user
        query = request.GET.get('q', '').lower()
        emotion_filter = request.GET.get('emotion', '')
        tags_filter = request.GET.get('tags', '').split(',')
        days_back = int(request.GET.get('days', 30))
        
        start_date = timezone.now().date() - timedelta(days=days_back)
        
        entries = JournalEntry.objects.filter(
            user=user,
            entry_date__gte=start_date,
            is_private=True
        )
        
        # Filter by emotion
        if emotion_filter:
            entries = entries.filter(
                Q(primary_emotion=emotion_filter) |
                Q(secondary_emotions__contains=[{'emotion': emotion_filter}])
            )
        
        # Filter by tags
        if tags_filter and tags_filter[0]:
            for tag in tags_filter:
                tag = tag.strip()
                if tag:
                    entries = entries.filter(
                        Q(tags__contains=[tag]) | Q(auto_tags__contains=[tag])
                    )
        
        # Full text search
        if query:
            entries = entries.filter(
                Q(personal_reflection__icontains=query) |
                Q(emotion_notes__icontains=query) |
                Q(gratitude_notes__icontains=query) |
                Q(key_moments__icontains=query)
            )
        
        data = []
        for e in entries:
            data.append({
                'id': e.id,
                'date': str(e.entry_date),
                'emotion': e.primary_emotion,
                'preview': e.personal_reflection[:100],
                'tags': e.tags,
            })
        
        return JsonResponse({'results': data, 'count': len(data)})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def export_journal_entries(request):
    """Export journal entries as JSON or CSV."""
    try:
        user = request.user
        days_back = int(request.GET.get('days', 365))
        export_format = request.GET.get('format', 'json')
        
        start_date = timezone.now().date() - timedelta(days=days_back)
        
        entries = JournalEntry.objects.filter(
            user=user,
            entry_date__gte=start_date,
            is_private=True
        ).order_by('-entry_date')
        
        if export_format == 'json':
            data = []
            for e in entries:
                data.append({
                    'date': str(e.entry_date),
                    'emotion': e.primary_emotion,
                    'intensity': e.emotion_intensity,
                    'reflection': e.personal_reflection,
                    'gratitude': e.gratitude_notes,
                    'challenges': e.challenges,
                    'achievements': e.achievements,
                    'tags': e.tags,
                    'media_count': e.media.count(),
                })
            
            return JsonResponse({'entries': data})
        
        elif export_format == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="journal_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Date', 'Emotion', 'Intensity', 'Reflection', 'Gratitude', 'Challenges', 'Achievements', 'Tags'])
            
            for e in entries:
                writer.writerow([
                    str(e.entry_date),
                    e.primary_emotion,
                    e.emotion_intensity,
                    e.personal_reflection[:100],
                    e.gratitude_notes[:100],
                    e.challenges[:100],
                    e.achievements[:100],
                    ','.join(e.tags)
                ])
            
            return response
        
        return JsonResponse({'error': 'Invalid format'}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
