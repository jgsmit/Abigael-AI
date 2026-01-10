from pynput import keyboard
import time
import numpy as np
from collections import deque
from django.utils import timezone
from .voice_typing_models import TypingPattern, TypingEvent, TypingEmotionProfile
import threading

class TypingEmotionDetector:
    def __init__(self):
        self.listener = None
        self.is_monitoring = False
        self.current_pattern = None
        self.user = None
        
        # Typing data tracking
        self.key_press_times = deque(maxlen=100)
        self.key_durations = deque(maxlen=100)
        self.current_key_start = None
        self.last_key_time = None
        
        # Emotion profiles based on typing patterns
        self.emotion_typing_profiles = {
            'stressed': {
                'speed': 'fast',
                'rhythm': 'irregular',
                'errors': 'high',
                'pressure': 'heavy'
            },
            'calm': {
                'speed': 'moderate',
                'rhythm': 'regular',
                'errors': 'low',
                'pressure': 'light'
            },
            'focused': {
                'speed': 'steady',
                'rhythm': 'regular',
                'errors': 'medium',
                'pressure': 'moderate'
            },
            'excited': {
                'speed': 'fast',
                'rhythm': 'irregular',
                'errors': 'medium',
                'pressure': 'variable'
            },
            'tired': {
                'speed': 'slow',
                'rhythm': 'irregular',
                'errors': 'high',
                'pressure': 'light'
            }
        }
    
    def start_monitoring(self, user):
        """Start typing pattern monitoring"""
        if self.is_monitoring:
            self.stop_monitoring()
            
        self.user = user
        self.current_pattern = TypingPattern.objects.create(user=user)
        self.is_monitoring = True
        
        # Start keyboard listener
        self.listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.listener.start()
        
        # Start emotion analysis thread
        analysis_thread = threading.Thread(target=self._analyze_typing_patterns)
        analysis_thread.daemon = True
        analysis_thread.start()
    
    def stop_monitoring(self):
        """Stop typing pattern monitoring"""
        self.is_monitoring = False
        if self.listener:
            self.listener.stop()
            self.listener = None
            
        if self.current_pattern:
            self.current_pattern.is_active = False
            self.current_pattern.save()
            self.current_pattern = None
    
    def _on_key_press(self, key):
        """Handle key press event"""
        if not self.is_monitoring:
            return
            
        try:
            current_time = time.time()
            key_char = str(key.char) if hasattr(key, 'char') else str(key)
            
            # Record key press start time
            self.current_key_start = current_time
            
            # Calculate time since previous key
            if self.last_key_time:
                time_since_previous = (current_time - self.last_key_time) * 1000  # Convert to ms
            else:
                time_since_previous = 0
                
            self.last_key_time = current_time
            
        except Exception as e:
            print(f"Key press error: {e}")
    
    def _on_key_release(self, key):
        """Handle key release event"""
        if not self.is_monitoring or not self.current_key_start:
            return
            
        try:
            current_time = time.time()
            key_char = str(key.char) if hasattr(key, 'char') else str(key)
            
            # Calculate press duration
            press_duration = (current_time - self.current_key_start) * 1000  # Convert to ms
            
            # Calculate typing speed (keys per minute)
            if len(self.key_press_times) > 1:
                time_window = current_time - self.key_press_times[0]
                if time_window > 0:
                    typing_speed = (len(self.key_press_times) / time_window) * 60
                else:
                    typing_speed = 0
            else:
                typing_speed = 0
            
            # Calculate rhythm variance
            if len(self.key_durations) > 1:
                rhythm_variance = np.var(list(self.key_durations))
            else:
                rhythm_variance = 0
            
            # Store typing event
            TypingEvent.objects.create(
                pattern=self.current_pattern,
                key_code=key.vk if hasattr(key, 'vk') else 0,
                key_pressed=key_char,
                press_duration=press_duration,
                time_since_previous=(self.last_key_time and (current_time - self.last_key_time) * 1000) or 0,
                typing_speed=typing_speed,
                rhythm_variance=rhythm_variance
            )
            
            # Update tracking data
            self.key_press_times.append(current_time)
            self.key_durations.append(press_duration)
            
            # Infer emotion from typing pattern
            inferred_emotion = self._infer_emotion_from_typing(
                typing_speed, press_duration, rhythm_variance
            )
            
            # Update the last event with inferred emotion
            last_event = TypingEvent.objects.filter(pattern=self.current_pattern).last()
            if last_event:
                last_event.inferred_emotion = inferred_emotion
                last_event.confidence = 0.7  # Base confidence
                last_event.save()
            
        except Exception as e:
            print(f"Key release error: {e}")
    
    def _analyze_typing_patterns(self):
        """Analyze typing patterns and update emotion profiles"""
        while self.is_monitoring and self.current_pattern:
            try:
                # Get recent typing events
                recent_events = TypingEvent.objects.filter(
                    pattern=self.current_pattern
                ).order_by('-timestamp')[:50]
                
                if len(recent_events) >= 10:
                    # Calculate aggregate metrics
                    speeds = [event.typing_speed for event in recent_events if event.typing_speed > 0]
                    durations = [event.press_duration for event in recent_events if event.press_duration > 0]
                    variances = [event.rhythm_variance for event in recent_events if event.rhythm_variance > 0]
                    
                    if speeds and durations and variances:
                        avg_speed = np.mean(speeds)
                        avg_duration = np.mean(durations)
                        avg_variance = np.mean(variances)
                        
                        # Classify emotion based on patterns
                        emotion = self._classify_typing_emotion(avg_speed, avg_duration, avg_variance)
                        
                        # Update user's typing emotion profile
                        profile, created = TypingEmotionProfile.objects.get_or_create(
                            user=self.user,
                            emotion=emotion
                        )
                        
                        if not created:
                            # Update profile with new data
                            profile.avg_typing_speed = ((profile.avg_typing_speed * profile.sample_size) + avg_speed) / (profile.sample_size + 1)
                            profile.avg_press_duration = ((profile.avg_press_duration * profile.sample_size) + avg_duration) / (profile.sample_size + 1)
                            profile.avg_rhythm_variance = ((profile.avg_rhythm_variance * profile.sample_size) + avg_variance) / (profile.sample_size + 1)
                            profile.sample_size += 1
                            profile.save()
                
                time.sleep(30)  # Analyze every 30 seconds
                
            except Exception as e:
                print(f"Typing analysis error: {e}")
                time.sleep(30)
    
    def _infer_emotion_from_typing(self, typing_speed, press_duration, rhythm_variance):
        """Infer emotion from current typing pattern"""
        # Rule-based emotion inference
        if typing_speed > 300 and rhythm_variance > 100:
            return 'stressed'
        elif typing_speed < 100 and rhythm_variance > 80:
            return 'tired'
        elif 150 < typing_speed < 250 and rhythm_variance < 50:
            return 'focused'
        elif typing_speed > 250 and rhythm_variance < 80:
            return 'excited'
        elif 100 < typing_speed < 200 and rhythm_variance < 30:
            return 'calm'
        else:
            return 'neutral'
    
    def _classify_typing_emotion(self, avg_speed, avg_duration, avg_variance):
        """Classify emotion from aggregate typing patterns"""
        # More sophisticated classification using multiple metrics
        if avg_speed > 280 and avg_variance > 120:
            return 'stressed'
        elif avg_speed < 80 and avg_variance > 100:
            return 'tired'
        elif 120 < avg_speed < 220 and avg_variance < 40:
            return 'focused'
        elif avg_speed > 220 and avg_variance < 60:
            return 'excited'
        elif 80 < avg_speed < 180 and avg_variance < 25:
            return 'calm'
        else:
            return 'neutral'
    
    def get_current_typing_emotion(self):
        """Get the most recent typing emotion inference"""
        if not self.current_pattern:
            return None
            
        latest_event = TypingEvent.objects.filter(
            pattern=self.current_pattern
        ).order_by('-timestamp').first()
        
        if latest_event and latest_event.inferred_emotion:
            return {
                'emotion': latest_event.inferred_emotion,
                'confidence': latest_event.confidence,
                'typing_speed': latest_event.typing_speed,
                'rhythm_variance': latest_event.rhythm_variance
            }
        return None

# Global typing detector instance
typing_detector = TypingEmotionDetector()
