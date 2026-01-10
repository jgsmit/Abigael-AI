import whisper
import speech_recognition as sr
from elevenlabs.client import ElevenLabs
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
import io
import json
import tempfile
import os
from .companion_models import Conversation, Message, CompanionProfile

class SpeechToTextEngine:
    """Speech-to-text conversion using Whisper and Google Speech API"""
    
    def __init__(self):
        # Load Whisper model
        self.whisper_model = whisper.load_model("base")
        self.recognizer = sr.Recognizer()
        
        # Initialize ElevenLabs client if API key is available
        self.elevenlabs_client = None
        if hasattr(settings, 'ELEVENLABS_API_KEY'):
            self.elevenlabs_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    
    def transcribe_audio(self, audio_file, user=None):
        """Convert audio to text using Whisper"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_file.read())
                temp_file_path = temp_file.name
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(temp_file_path)
            text = result['text']
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return {
                'text': text,
                'language': result.get('language', 'en'),
                'confidence': 0.85  # Whisper doesn't provide confidence, using default
            }
            
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return None
    
    def transcribe_with_google(self, audio_data, user=None):
        """Fallback transcription using Google Speech API"""
        try:
            # Convert audio data to AudioFile
            audio_file = sr.AudioFile(io.BytesIO(audio_data))
            
            # Recognize speech
            with sr.Microphone() as source:
                audio = self.recognizer.record(source, duration=10)
            
            text = self.recognizer.recognize_google(audio)
            
            return {
                'text': text,
                'language': 'en',
                'confidence': 0.8
            }
            
        except Exception as e:
            print(f"Google Speech API error: {e}")
            return None

class TextToSpeechEngine:
    """Text-to-speech conversion using ElevenLabs and fallback engines"""
    
    def __init__(self):
        self.elevenlabs_client = None
        if hasattr(settings, 'ELEVENLABS_API_KEY'):
            self.elevenlabs_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    
    def synthesize_speech(self, text, voice_id=None, user=None):
        """Convert text to speech using ElevenLabs"""
        if not self.elevenlabs_client:
            return self._fallback_tts(text, user)
        
        try:
            # Get user's preferred voice
            if user:
                profile = getattr(user, 'companionprofile', None)
                if profile:
                    voice_id = voice_id or self._get_user_voice_id(profile)
            
            # Default voice if none specified
            voice_id = voice_id or "Adam"
            
            # Generate speech
            audio = self.elevenlabs_client.generate(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )
            
            # Convert to bytes
            audio_bytes = b''.join(chunk for chunk in audio)
            
            return {
                'audio_data': audio_bytes,
                'voice_used': voice_id,
                'duration': len(audio_bytes) / 16000  # Approximate duration
            }
            
        except Exception as e:
            print(f"ElevenLabs TTS error: {e}")
            return self._fallback_tts(text, user)
    
    def _fallback_tts(self, text, user=None):
        """Fallback TTS using system TTS"""
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            
            # Configure voice based on user preferences
            if user:
                profile = getattr(user, 'companionprofile', None)
                if profile:
                    voices = engine.getProperty('voices')
                    # Try to find a voice matching user preferences
                    for voice in voices:
                        if profile.preferred_voice.lower() in voice.name.lower():
                            engine.setProperty('voice', voice.id)
                            break
                    
                    # Set speed and pitch
                    engine.setProperty('rate', int(200 * profile.voice_speed))
                    engine.setProperty('pitch', profile.voice_pitch)
            
            # Save to bytes
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                engine.save_to_file(text, temp_file.name)
                
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                
                os.unlink(temp_file.name)
            
            return {
                'audio_data': audio_bytes,
                'voice_used': 'system_tts',
                'duration': len(audio_bytes) / 16000
            }
            
        except Exception as e:
            print(f"Fallback TTS error: {e}")
            return None
    
    def _get_user_voice_id(self, profile):
        """Get user's preferred ElevenLabs voice ID"""
        voice_mapping = {
            'friendly_warm': 'Adam',
            'caring_gentle': 'Bella',
            'professional': 'Sam',
            'energetic': 'Josh',
            'calm': 'Rachel',
            'playful': 'Domi'
        }
        return voice_mapping.get(profile.preferred_voice, 'Adam')

class AvatarInteractionEngine:
    """Real-time avatar interaction with WebRTC and D-ID integration"""
    
    def __init__(self):
        self.d_id_api_key = getattr(settings, 'D_ID_API_KEY', None)
        self.active_sessions = {}
    
    def create_avatar_session(self, user, conversation_id):
        """Create a new avatar interaction session"""
        session_id = f"{user.id}_{conversation_id}"
        
        session_data = {
            'user_id': user.id,
            'conversation_id': conversation_id,
            'created_at': timezone.now(),
            'avatar_style': self._get_user_avatar_style(user),
            'is_active': True
        }
        
        self.active_sessions[session_id] = session_data
        
        return session_id
    
    def generate_avatar_response(self, session_id, text, emotion=None):
        """Generate avatar animation and lip-sync for response"""
        if session_id not in self.active_sessions:
            return None
        
        try:
            # This would integrate with D-ID API for avatar generation
            # For now, return mock data
            avatar_data = {
                'session_id': session_id,
                'text': text,
                'emotion': emotion or 'neutral',
                'lip_sync_data': self._generate_lip_sync_data(text),
                'animation_data': self._generate_animation_data(emotion),
                'duration': len(text.split()) * 0.5  # Approximate duration
            }
            
            return avatar_data
            
        except Exception as e:
            print(f"Avatar generation error: {e}")
            return None
    
    def _generate_lip_sync_data(self, text):
        """Generate lip-sync data for text (mock implementation)"""
        # This would normally use D-ID's lip-sync API
        words = text.split()
        lip_sync = []
        
        for i, word in enumerate(words):
            lip_sync.append({
                'word': word,
                'start_time': i * 0.5,
                'end_time': (i + 1) * 0.5,
                'visemes': self._text_to_visemes(word)
            })
        
        return lip_sync
    
    def _generate_animation_data(self, emotion):
        """Generate animation data based on emotion"""
        animations = {
            'happy': 'smile_blink',
            'sad': 'concerned_nod',
            'angry': 'firm_gesture',
            'focused': 'attentive_nod',
            'calm': 'gentle_smile',
            'excited': 'enthusiastic_gesture',
            'neutral': 'neutral_expression'
        }
        
        return {
            'animation': animations.get(emotion, 'neutral_expression'),
            'intensity': 0.7,
            'duration': 2.0
        }
    
    def _text_to_visemes(self, word):
        """Convert word to visemes (mock implementation)"""
        # Simple mapping - in reality would be more sophisticated
        viseme_map = {
            'a': 'AE', 'b': 'BMP', 'c': 'E', 'd': 'D', 'e': 'E',
            'f': 'FV', 'g': 'E', 'h': 'E', 'i': 'E', 'j': 'D',
            'k': 'E', 'l': 'E', 'm': 'BMP', 'n': 'E', 'o': 'O',
            'p': 'BMP', 'q': 'O', 'r': 'E', 's': 'E', 't': 'D',
            'u': 'WQ', 'v': 'FV', 'w': 'WQ', 'x': 'E', 'y': 'E',
            'z': 'E'
        }
        
        visemes = []
        for char in word.lower():
            if char in viseme_map:
                visemes.append(viseme_map[char])
        
        return visemes or ['E']
    
    def _get_user_avatar_style(self, user):
        """Get user's preferred avatar style"""
        profile = getattr(user, 'companionprofile', None)
        if profile:
            return profile.avatar_style
        return 'friendly'
    
    def end_avatar_session(self, session_id):
        """End avatar interaction session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['is_active'] = False
            del self.active_sessions[session_id]

class CompanionChatEngine:
    """Enhanced chat engine for Abigael AI companion"""
    
    def __init__(self):
        self.stt_engine = SpeechToTextEngine()
        self.tts_engine = TextToSpeechEngine()
        self.avatar_engine = AvatarInteractionEngine()
    
    def process_text_message(self, user, text, conversation_id):
        """Process text message and generate AI response"""
        try:
            # Get user's companion profile
            profile = getattr(user, 'companionprofile', None)
            
            # Detect user emotion from text
            emotion = self._detect_text_emotion(text)
            
            # Generate empathetic response
            response = self._generate_companion_response(user, text, emotion, profile)
            
            # Log message
            conversation = Conversation.objects.get_or_create(
                user=user,
                session_id=conversation_id,
                defaults={
                    'conversation_type': 'text',
                    'user_emotion_at_start': emotion
                }
            )
            
            # Save user message
            Message.objects.create(
                conversation=conversation,
                message_type='user',
                content=text,
                user_emotion=emotion,
                sentiment_score=self._calculate_sentiment(text)
            )
            
            # Save AI response
            Message.objects.create(
                conversation=conversation,
                message_type='ai',
                content=response['text'],
                emotion_detected=emotion,
                empathy_level=response.get('empathy_score', 0.8),
                response_strategy=response.get('strategy', 'empathetic'),
                personalization_applied=profile is not None
            )
            
            return response
            
        except Exception as e:
            print(f"Text message processing error: {e}")
            return {'text': "I'm here to support you. How can I help today?"}
    
    def process_voice_message(self, user, audio_file, conversation_id):
        """Process voice message and generate AI response"""
        try:
            # Transcribe audio
            transcription = self.stt_engine.transcribe_audio(audio_file, user)
            
            if not transcription:
                return {'error': 'Could not transcribe audio'}
            
            text = transcription['text']
            
            # Process as text message
            response = self.process_text_message(user, text, conversation_id)
            
            # Add voice metadata to response
            response['transcription'] = transcription
            
            return response
            
        except Exception as e:
            print(f"Voice message processing error: {e}")
            return {'error': 'Could not process voice message'}
    
    def generate_voice_response(self, user, text, conversation_id):
        """Generate voice response for AI text"""
        try:
            # Get user's companion profile
            profile = getattr(user, 'companionprofile', None)
            
            # Generate speech
            speech_result = self.tts_engine.synthesize_speech(text, user=user)
            
            if not speech_result:
                return {'error': 'Could not generate speech'}
            
            return speech_result
            
        except Exception as e:
            print(f"Voice response generation error: {e}")
            return {'error': 'Could not generate voice response'}
    
    def process_video_message(self, user, audio_file, conversation_id):
        """Process video message with avatar interaction"""
        try:
            # Transcribe audio
            transcription = self.stt_engine.transcribe_audio(audio_file, user)
            
            if not transcription:
                return {'error': 'Could not transcribe video audio'}
            
            text = transcription['text']
            
            # Generate AI response
            response = self.process_text_message(user, text, conversation_id)
            
            # Create avatar session
            session_id = self.avatar_engine.create_avatar_session(user, conversation_id)
            
            # Generate avatar response
            avatar_response = self.avatar_engine.generate_avatar_response(
                session_id, response['text']
            )
            
            if avatar_response:
                response['avatar_data'] = avatar_response
                response['session_id'] = session_id
            
            return response
            
        except Exception as e:
            print(f"Video message processing error: {e}")
            return {'error': 'Could not process video message'}
    
    def _detect_text_emotion(self, text):
        """Detect emotion from text using simple keyword analysis"""
        emotion_keywords = {
            'happy': ['happy', 'joy', 'excited', 'great', 'wonderful', 'amazing', 'love'],
            'sad': ['sad', 'depressed', 'down', 'unhappy', 'cry', 'tears', 'hurt'],
            'angry': ['angry', 'mad', 'furious', 'frustrated', 'annoyed', 'upset'],
            'stressed': ['stressed', 'overwhelmed', 'anxious', 'worried', 'nervous'],
            'calm': ['calm', 'peaceful', 'relaxed', 'serene', 'tranquil'],
            'focused': ['focused', 'concentrating', 'working', 'studying', 'determined'],
            'tired': ['tired', 'exhausted', 'fatigued', 'sleepy', 'drained']
        }
        
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            emotion_scores[emotion] = score
        
        if emotion_scores:
            return max(emotion_scores, key=emotion_scores.get)
        
        return 'neutral'
    
    def _generate_companion_response(self, user, text, emotion, profile):
        """Generate empathetic companion response"""
        try:
            from .empathy_engine import empathy_engine
            
            # Build context for response generation
            context = {
                'companion_name': profile.companion_name if profile else 'Abigael',
                'personality_type': profile.personality_type if profile else 'caring_friend',
                'communication_tone': profile.communication_tone if profile else 'casual',
                'relationship_depth': profile.relationship_depth if profile else 0.0
            }
            
            # Generate response using empathy engine
            response_text = empathy_engine.generate_empathetic_message(
                emotion, 
                context=json.dumps(context)
            )
            
            # Calculate empathy score
            empathy_score = self._calculate_empathy_score(response_text, emotion)
            
            return {
                'text': response_text,
                'empathy_score': empathy_score,
                'strategy': 'empathetic_companion',
                'personalized': profile is not None
            }
            
        except Exception as e:
            print(f"Companion response generation error: {e}")
            return {
                'text': "I'm here for you. Tell me what's on your mind.",
                'empathy_score': 0.5,
                'strategy': 'fallback',
                'personalized': False
            }
    
    def _calculate_empathy_score(self, response_text, emotion):
        """Calculate empathy score based on response content"""
        empathy_indicators = [
            'understand', 'feel', 'here for you', 'support', 'care',
            'listen', 'help', 'together', 'safe', 'comfort'
        ]
        
        response_lower = response_text.lower()
        empathy_count = sum(1 for indicator in empathy_indicators if indicator in response_lower)
        
        # Normalize to 0-1 scale
        max_possible = len(empathy_indicators)
        empathy_score = min(1.0, empathy_count / max_possible)
        
        return empathy_score
    
    def _calculate_sentiment(self, text):
        """Simple sentiment analysis"""
        positive_words = ['good', 'great', 'happy', 'love', 'wonderful', 'amazing']
        negative_words = ['bad', 'terrible', 'hate', 'sad', 'angry', 'frustrated']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 0.7
        elif negative_count > positive_count:
            return 0.3
        else:
            return 0.5

# Global companion engine instance
companion_engine = CompanionChatEngine()
