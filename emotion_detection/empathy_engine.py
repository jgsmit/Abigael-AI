import openai
import json
from django.conf import settings
from django.utils import timezone
from tasks.models import Task, EmotionRecord
from emotion_detection.emotion_detector import emotion_detector
from emotion_detection.voice_detector import voice_detector
from emotion_detection.typing_detector import typing_detector
import random

class EmpathyEngine:
    def __init__(self):
        # Configure OpenAI (you'll need to set up API key in settings)
        if hasattr(settings, 'OPENAI_API_KEY'):
            openai.api_key = settings.OPENAI_API_KEY
        self.client = None
        
        # Empathy response templates for different emotions
        self.empathy_templates = {
            'stressed': [
                "I notice you seem stressed. Maybe take a short break? A 5-minute walk could help clear your mind.",
                "You're showing signs of stress. How about tackling something simpler first to build momentum?",
                "Stress levels are high right now. Consider deep breathing exercises before diving into complex tasks."
            ],
            'calm': [
                "You're feeling calm - perfect state for focused work! This is ideal for your important tasks.",
                "Your calm demeanor is great for analytical work. Ready to tackle that complex project?",
                "Peaceful energy detected! This is the perfect time for creative problem-solving."
            ],
            'focused': [
                "You're in the zone! Your focus is sharp - let's make the most of this productive state.",
                "Deep focus detected! This is prime time for your most challenging tasks.",
                "Your concentration is excellent. Perfect timing for that detailed work you've been putting off."
            ],
            'excited': [
                "I sense excitement! Great energy for collaborative tasks or learning something new.",
                "Your enthusiasm is contagious! Perfect time for creative brainstorming or team work.",
                "Excited mood detected! Ideal for innovative thinking and breaking new ground."
            ],
            'tired': [
                "You seem tired. Maybe handle some lighter tasks or take a power nap first?",
                "Fatigue detected. Be kind to yourself - perhaps some administrative tasks would be better now.",
                "Low energy observed. Consider organizing your workspace or planning tomorrow instead."
            ],
            'sad': [
                "I notice you're feeling down. Sometimes gentle, comforting tasks can help lift your spirits.",
                "Your mood seems low. How about something creative or comforting? Music might help too.",
                "Sadness detected. Maybe tackle something simple and achievable to build confidence."
            ],
            'angry': [
                "Anger detected. Physical activity or organizing tasks might help channel this energy productively.",
                "I sense frustration. Maybe break down that overwhelming task into smaller, manageable steps?",
                "Your anger suggests high energy - let's direct it toward something constructive."
            ]
        }
        
        # Motivational messages for task completion
        self.completion_messages = [
            "Excellent work! You're building great momentum!",
            "Fantastic progress! Your productivity is impressive today.",
            "Well done! Each completed task brings you closer to your goals.",
            "Amazing! You're crushing your tasks today.",
            "Great job! Your focus and dedication are paying off.",
            "Outstanding work! You're on fire today!",
            "Brilliant! Keep up this incredible momentum."
        ]
        
        # Break suggestions
        self.break_suggestions = [
            "Time for a 5-minute stretch break!",
            "How about a quick walk around the room?",
            "Try some deep breathing exercises for 2 minutes.",
            "Grab a glass of water and take a moment to recharge.",
            "Step away from the screen for a quick eye break.",
            "Do some shoulder rolls to release tension."
        ]
    
    def generate_empathetic_message(self, user_emotion, current_task=None, context=None):
        """Generate an empathetic message based on user's emotional state"""
        try:
            # Try OpenAI API first if available
            if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                return self._generate_ai_message(user_emotion, current_task, context)
            else:
                # Fallback to template-based responses
                return self._generate_template_message(user_emotion, current_task, context)
        except Exception as e:
            print(f"Empathy engine error: {e}")
            return self._generate_template_message(user_emotion, current_task, context)
    
    def _generate_ai_message(self, user_emotion, current_task, context):
        """Generate message using OpenAI API"""
        try:
            prompt = self._build_empathy_prompt(user_emotion, current_task, context)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an empathetic AI productivity assistant. Provide brief, supportive, and actionable messages based on the user's emotional state."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._generate_template_message(user_emotion, current_task, context)
    
    def _build_empathy_prompt(self, emotion, task, context):
        """Build prompt for AI message generation"""
        prompt = f"The user is feeling {emotion}. "
        
        if task:
            prompt += f"They're currently working on: '{task.title}'. "
        
        if context:
            prompt += f"Additional context: {context}. "
        
        prompt += """
        Provide a brief, empathetic response that:
        1. Acknowledges their emotional state
        2. Offers relevant productivity advice
        3. Is encouraging and supportive
        4. Is under 50 words
        """
        
        return prompt
    
    def _generate_template_message(self, emotion, current_task, context):
        """Generate message using predefined templates"""
        templates = self.empathy_templates.get(emotion, [
            "How are you feeling? Let's find the right task for your current state."
        ])
        
        base_message = random.choice(templates)
        
        # Add task-specific context if available
        if current_task:
            task_suggestions = self._get_task_specific_suggestion(emotion, current_task)
            base_message += f" {task_suggestions}"
        
        return base_message
    
    def _get_task_specific_suggestion(self, emotion, task):
        """Get task-specific suggestion based on emotion"""
        task_lower = task.title.lower()
        
        if emotion == 'stressed':
            if any(word in task_lower for word in ['report', 'analysis', 'complex']):
                return "Maybe break this down into smaller steps first."
        elif emotion == 'calm':
            if any(word in task_lower for word in ['plan', 'organize', 'design']):
                return "Perfect timing for thoughtful work like this."
        elif emotion == 'focused':
            if any(word in task_lower for word in ['code', 'write', 'create']):
                return "Your focus is ideal for deep work on this."
        elif emotion == 'tired':
            if any(word in task_lower for word in ['review', 'organize', 'clean']):
                return "This seems manageable for your current energy level."
        
        return ""
    
    def generate_motivation_message(self, task_completed=False):
        """Generate motivational message"""
        if task_completed:
            return random.choice(self.completion_messages)
        else:
            return "You're doing great! Keep up the good work."
    
    def suggest_break(self, emotion='neutral'):
        """Suggest appropriate break based on emotion"""
        if emotion == 'stressed':
            return "Try deep breathing: Inhale for 4 counts, hold for 4, exhale for 6. Repeat 5 times."
        elif emotion == 'tired':
            return "A quick 5-minute power nap could boost your energy significantly."
        elif emotion == 'focused':
            return "You're in flow! But a 2-minute stretch break will help maintain this state."
        else:
            return random.choice(self.break_suggestions)
    
    def analyze_productivity_pattern(self, user, time_period_hours=24):
        """Analyze user's productivity patterns and provide insights"""
        try:
            # Get recent emotion records
            from datetime import timedelta
            cutoff_time = timezone.now() - timedelta(hours=time_period_hours)
            
            emotion_records = EmotionRecord.objects.filter(
                user=user,
                timestamp__gte=cutoff_time
            ).order_by('-timestamp')
            
            # Get completed tasks in this period
            completed_tasks = Task.objects.filter(
                user=user,
                status='completed',
                completed_at__gte=cutoff_time
            )
            
            # Analyze patterns
            insights = self._analyze_emotion_productivity_correlation(emotion_records, completed_tasks)
            
            return insights
        except Exception as e:
            print(f"Pattern analysis error: {e}")
            return {"message": "Unable to analyze patterns right now."}
    
    def _analyze_emotion_productivity_correlation(self, emotion_records, completed_tasks):
        """Analyze correlation between emotions and task completion"""
        emotion_counts = {}
        task_emotions = {}
        
        # Count emotion occurrences
        for record in emotion_records:
            emotion = record.emotion
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            # Check if task was completed during this emotion
            if record.task and record.task in completed_tasks:
                task_emotions[emotion] = task_emotions.get(emotion, 0) + 1
        
        # Generate insights
        insights = []
        
        if emotion_counts:
            most_common_emotion = max(emotion_counts, key=emotion_counts.get)
            insights.append(f"Your most common emotion was {most_common_emotion} today.")
        
        if task_emotions:
            most_productive_emotion = max(task_emotions, key=task_emotions.get)
            insights.append(f"You completed most tasks while feeling {most_productive_emotion}.")
        
        # Provide recommendations
        if 'focused' in emotion_counts and emotion_counts['focused'] > 3:
            insights.append("You had good focus periods - consider scheduling important tasks during similar times.")
        
        if 'stressed' in emotion_counts and emotion_counts['stressed'] > 5:
            insights.append("High stress detected - consider incorporating more breaks or stress management techniques.")
        
        return {
            "insights": insights,
            "emotion_distribution": emotion_counts,
            "productivity_by_emotion": task_emotions
        }
    
    def get_comprehensive_emotion_state(self, user):
        """Get comprehensive emotion state from all sensors"""
        emotion_data = {
            'facial': None,
            'voice': None,
            'typing': None,
            'combined': None,
            'confidence': 0.0
        }
        
        try:
            # Get facial emotion
            facial_data = emotion_detector.get_current_emotion()
            if facial_data:
                emotion_data['facial'] = facial_data['emotion']
                emotion_data['confidence'] += facial_data['confidence'] * 0.4  # Weight: 40%
            
            # Get voice emotion (most recent)
            from emotion_detection.voice_typing_models import VoiceEmotionRecord
            recent_voice = VoiceEmotionRecord.objects.filter(
                session__user=user
            ).order_by('-timestamp').first()
            
            if recent_voice:
                emotion_data['voice'] = recent_voice.emotion
                emotion_data['confidence'] += recent_voice.confidence * 0.3  # Weight: 30%
            
            # Get typing emotion
            typing_data = typing_detector.get_current_typing_emotion()
            if typing_data:
                emotion_data['typing'] = typing_data['emotion']
                emotion_data['confidence'] += typing_data['confidence'] * 0.3  # Weight: 30%
            
            # Determine combined emotion (simple majority voting)
            emotions = [e for e in [emotion_data['facial'], emotion_data['voice'], emotion_data['typing']] if e]
            if emotions:
                from collections import Counter
                emotion_counts = Counter(emotions)
                emotion_data['combined'] = emotion_counts.most_common(1)[0][0]
            
        except Exception as e:
            print(f"Comprehensive emotion analysis error: {e}")
        
        return emotion_data

# Global empathy engine instance
empathy_engine = EmpathyEngine()
