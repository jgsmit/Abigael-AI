import cv2
import numpy as np
from fer import FER
from django.utils import timezone
from .models import EmotionDetectionSession, EmotionSnapshot
import threading
import time

class EmotionDetector:
    def __init__(self):
        self.detector = FER(mtcnn=True)
        self.cap = None
        self.current_session = None
        self.is_running = False
        self.detection_thread = None
        
    def start_detection(self, user):
        """Start emotion detection for a user"""
        if self.is_running:
            self.stop_detection()
            
        self.current_session = EmotionDetectionSession.objects.create(user=user)
        self.is_running = True
        self.detection_thread = threading.Thread(target=self._detect_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        
    def stop_detection(self):
        """Stop emotion detection"""
        self.is_running = False
        if self.current_session:
            self.current_session.end_time = timezone.now()
            self.current_session.is_active = False
            self.current_session.save()
            self.current_session = None
            
        if self.cap:
            self.cap.release()
            self.cap = None
            
    def _detect_loop(self):
        """Main detection loop running in separate thread"""
        self.cap = cv2.VideoCapture(0)
        
        while self.is_running and self.current_session:
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            # Detect emotions
            emotions = self.detector.detect_emotions(frame)
            
            if emotions:
                # Get the first detected face
                emotion_data = emotions[0]
                box = emotion_data['box']
                emotions_dict = emotion_data['emotions']
                
                # Find dominant emotion
                dominant_emotion = max(emotions_dict, key=emotions_dict.get)
                confidence = emotions_dict[dominant_emotion]
                
                # Save snapshot
                EmotionSnapshot.objects.create(
                    session=self.current_session,
                    emotions=emotions_dict,
                    dominant_emotion=dominant_emotion,
                    confidence=confidence,
                    face_detected=True,
                    face_coordinates={
                        'x': box[0],
                        'y': box[1],
                        'w': box[2],
                        'h': box[3]
                    }
                )
            else:
                # No face detected
                EmotionSnapshot.objects.create(
                    session=self.current_session,
                    dominant_emotion='neutral',
                    confidence=0.0,
                    face_detected=False
                )
                
            time.sleep(2)  # Detect every 2 seconds
            
    def get_current_emotion(self):
        """Get the most recent emotion for the current session"""
        if not self.current_session:
            return None
            
        latest_snapshot = self.current_session.snapshots.last()
        if latest_snapshot:
            return {
                'emotion': latest_snapshot.dominant_emotion,
                'confidence': latest_snapshot.confidence,
                'all_emotions': latest_snapshot.emotions
            }
        return None

# Global detector instance
emotion_detector = EmotionDetector()

def get_emotion_recommendations(current_emotion, user_tasks):
    """Get task recommendations based on current emotion"""
    emotion_task_mapping = {
        'focused': ['writing', 'coding', 'analysis'],
        'calm': ['reading', 'planning', 'organization'],
        'happy': ['creative', 'collaboration', 'learning'],
        'stressed': ['simple', 'organization', 'break'],
        'neutral': ['maintenance', 'review', 'planning'],
        'sad': ['comfort', 'simple', 'creative'],
        'angry': ['physical', 'focused', 'break'],
        'surprised': ['learning', 'exploration', 'research'],
    }
    
    recommendations = []
    
    if current_emotion:
        preferred_task_types = emotion_task_mapping.get(current_emotion, [])
        
        for task in user_tasks:
            # Check if task matches preferred types
            task_lower = task.title.lower()
            for task_type in preferred_task_types:
                if task_type in task_lower:
                    recommendations.append(task)
                    break
                    
    # Sort by priority and return top recommendations
    recommendations.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x.priority], reverse=True)
    return recommendations[:5]  # Return top 5 recommendations
