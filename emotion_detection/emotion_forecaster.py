import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Q
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import MinMaxScaler
import json

from .autonomous_models import EmotionEvent
from tasks.models import Task


class EmotionForecaster:
    """
    Predictive emotion forecasting using LSTM (Long Short-Term Memory)
    Predicts emotions for next 3 hours with circadian rhythm modeling
    """
    
    def __init__(self, user, lookback_hours=72):
        self.user = user
        self.lookback_hours = lookback_hours
        self.current_time = timezone.now()
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.emotion_encoding = {
            'happy': 0, 'sad': 1, 'angry': 2, 'fearful': 3,
            'disgusted': 4, 'surprised': 5, 'neutral': 6,
            'stressed': 7, 'calm': 8, 'focused': 9
        }
        
    def get_historical_data(self):
        """Get historical emotion data for training"""
        cutoff_time = self.current_time - timedelta(hours=self.lookback_hours)
        
        emotion_records = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=cutoff_time
        ).order_by('timestamp').values_list('timestamp', 'emotion', 'confidence')
        
        data = []
        for timestamp, emotion, confidence in emotion_records:
            hour = timestamp.hour
            emotion_encoded = self.emotion_encoding.get(emotion, 6)
            
            data.append({
                'timestamp': timestamp,
                'hour': hour,
                'emotion': emotion,
                'emotion_encoded': emotion_encoded,
                'confidence': confidence
            })
        
        return pd.DataFrame(data)
    
    def add_circadian_features(self, df):
        """Add circadian rhythm features to data"""
        if df.empty:
            return df
        
        # Hour-based features (circadian patterns)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Day of week
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Time of day patterns (morning, afternoon, evening, night)
        df['is_morning'] = ((df['hour'] >= 6) & (df['hour'] < 12)).astype(int)
        df['is_afternoon'] = ((df['hour'] >= 12) & (df['hour'] < 18)).astype(int)
        df['is_evening'] = ((df['hour'] >= 18) & (df['hour'] < 24)).astype(int)
        df['is_night'] = ((df['hour'] >= 0) & (df['hour'] < 6)).astype(int)
        
        return df
    
    def add_sleep_debt_feature(self, df):
        """Add sleep debt accumulation tracking"""
        # This would integrate with biofeedback sleep data
        # For now, use a simple model: each day increases debt, sleep resets
        
        if df.empty:
            return df
        
        sleep_debt = []
        current_debt = 0
        current_date = None
        
        for _, row in df.iterrows():
            if current_date != row['timestamp'].date():
                # New day - check if user slept well
                current_debt = max(0, current_debt - 8)  # Assume 8hr sleep
                current_date = row['timestamp'].date()
            
            # Accumulate debt during day (0.5 per hour awake)
            if row['is_morning'] or row['is_afternoon'] or row['is_evening']:
                current_debt += 0.5
            
            sleep_debt.append(min(24, current_debt))  # Cap at 24 hours
        
        df['sleep_debt_hours'] = sleep_debt
        return df
    
    def add_task_load_features(self, df):
        """Add task load and stress context"""
        if df.empty:
            return df
        
        task_load = []
        
        for _, row in df.iterrows():
            timestamp = row['timestamp']
            hour_start = timestamp.replace(minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            # Count tasks created/updated in this hour
            task_count = Task.objects.filter(
                user=self.user,
                updated_at__gte=hour_start,
                updated_at__lt=hour_end
            ).count()
            
            task_load.append(task_count)
        
        df['task_load_hourly'] = task_load
        return df
    
    def prepare_lstm_data(self, df, sequence_length=12):
        """Prepare data for LSTM model (sequence of 12 hourly readings)"""
        if df.empty or len(df) < sequence_length:
            return None, None
        
        # Select features for LSTM
        features = ['emotion_encoded', 'confidence', 'hour_sin', 'hour_cos',
                   'sleep_debt_hours', 'task_load_hourly']
        
        X = df[features].values
        y = df['emotion_encoded'].values
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Create sequences
        X_sequences = []
        y_sequences = []
        
        for i in range(len(X_scaled) - sequence_length):
            X_sequences.append(X_scaled[i:i+sequence_length])
            y_sequences.append(y[i+sequence_length])
        
        if not X_sequences:
            return None, None
        
        return np.array(X_sequences), np.array(y_sequences)
    
    def build_lstm_model(self, input_shape):
        """Build LSTM neural network model"""
        model = keras.Sequential([
            keras.layers.LSTM(64, activation='relu', return_sequences=True, input_shape=input_shape),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(32, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(len(self.emotion_encoding), activation='softmax')
        ])
        
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        return model
    
    def train_model(self, df):
        """Train LSTM model on user's emotional data"""
        if df.empty or len(df) < 24:  # Need at least 24 hours of data
            return False
        
        # Prepare data
        X, y = self.prepare_lstm_data(df, sequence_length=12)
        
        if X is None:
            return False
        
        # Build and train model
        self.model = self.build_lstm_model((X.shape[1], X.shape[2]))
        
        self.model.fit(X, y, epochs=50, batch_size=4, verbose=0, validation_split=0.2)
        
        return True
    
    def forecast_emotions(self, hours_ahead=3):
        """
        Forecast emotions for next N hours
        Returns: List of {time, emotion, confidence, reasoning}
        """
        # Get historical data
        df = self.get_historical_data()
        
        if df.empty:
            return self._fallback_forecast(hours_ahead)
        
        # Add features
        df = self.add_circadian_features(df)
        df = self.add_sleep_debt_feature(df)
        df = self.add_task_load_features(df)
        
        # Train model if needed
        if self.model is None:
            if not self.train_model(df):
                return self._fallback_forecast(hours_ahead)
        
        # Generate forecast
        forecasts = []
        current_time = self.current_time
        last_emotion = df.iloc[-1] if not df.empty else None
        
        for hour_offset in range(1, hours_ahead + 1):
            forecast_time = current_time + timedelta(hours=hour_offset)
            
            # Create feature vector for forecast time
            features = self._create_forecast_features(forecast_time, last_emotion)
            
            # Predict emotion
            prediction = self.model.predict(features, verbose=0)
            emotion_idx = np.argmax(prediction[0])
            confidence = float(prediction[0][emotion_idx])
            
            # Decode emotion
            emotion_name = [k for k, v in self.emotion_encoding.items() if v == emotion_idx][0]
            
            # Generate reasoning
            reasoning = self._generate_forecast_reasoning(
                forecast_time, emotion_name, confidence, df
            )
            
            forecasts.append({
                'time': forecast_time.isoformat(),
                'hour_offset': hour_offset,
                'emotion': emotion_name,
                'confidence': confidence,
                'reasoning': reasoning
            })
        
        return forecasts
    
    def _create_forecast_features(self, forecast_time, last_emotion):
        """Create feature vector for a specific time"""
        from emotion_detection.models import EmotionEvent
        from tasks.models import Task
        
        hour = forecast_time.hour
        day_of_week = forecast_time.weekday()
        
        # Get actual current emotion encoded value
        last_emotion_encoded = self.emotion_encoding.get('neutral', 6)
        if last_emotion:
            last_emotion_encoded = self.emotion_encoding.get(
                last_emotion.get('emotion', 'neutral'), 6
            )
        
        # Calculate actual confidence from recent predictions
        recent_emotions = EmotionEvent.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(hours=4)
        ).order_by('-timestamp')[:5]
        
        confidence = sum([e.confidence or 0.7 for e in recent_emotions]) / max(1, len(recent_emotions))
        
        # Get actual sleep debt calculation
        from emotion_detection.biofeedback_models import BiofeedbackData
        sleep_records = BiofeedbackData.objects.filter(
            user=self.user,
            timestamp__gte=self.current_time - timedelta(days=7),
            metric_type='sleep'
        ).values_list('value', flat=True)
        
        sleep_debt = max(0, 8 - (sum(sleep_records) / max(1, len(sleep_records))))
        
        # Get actual task load
        recent_tasks = Task.objects.filter(
            user=self.user,
            created_at__gte=self.current_time - timedelta(hours=24)
        ).count()
        
        task_load = min(4.0, recent_tasks / 6.0)  # 6 tasks = 1.0 load
        
        features = np.array([[
            last_emotion_encoded,
            float(confidence),
            np.sin(2 * np.pi * hour / 24),  # hour_sin
            np.cos(2 * np.pi * hour / 24),  # hour_cos
            float(sleep_debt),
            float(task_load)
        ]])
        
        features_scaled = self.scaler.transform(features)
        return features_scaled.reshape(1, 1, -1)
    
    def _fallback_forecast(self, hours_ahead):
        """Fallback forecast when model unavailable"""
        forecasts = []
        
        for hour_offset in range(1, hours_ahead + 1):
            forecast_time = self.current_time + timedelta(hours=hour_offset)
            
            # Simple circadian-based fallback
            emotion = self._circadian_emotion_fallback(forecast_time.hour)
            
            forecasts.append({
                'time': forecast_time.isoformat(),
                'hour_offset': hour_offset,
                'emotion': emotion,
                'confidence': 0.6,
                'reasoning': 'Fallback forecast based on typical circadian patterns'
            })
        
        return forecasts
    
    def _circadian_emotion_fallback(self, hour):
        """Simple emotion forecast based on time of day"""
        if 6 <= hour < 10:
            return 'calm'  # Morning calm
        elif 10 <= hour < 14:
            return 'focused'  # Peak focus
        elif 14 <= hour < 17:
            return 'stressed'  # Afternoon slump
        elif 17 <= hour < 21:
            return 'excited'  # Evening energy
        else:
            return 'calm'  # Night
    
    def _generate_forecast_reasoning(self, forecast_time, emotion, confidence, df):
        """Generate human-readable reasoning for forecast"""
        hour = forecast_time.hour
        
        reasons = []
        
        # Circadian rhythm
        if 6 <= hour < 10:
            reasons.append("Morning hours typically calm")
        elif 10 <= hour < 14:
            reasons.append("Peak focus hours")
        elif 14 <= hour < 17:
            reasons.append("Afternoon energy dip")
        
        # Confidence level
        if confidence < 0.6:
            reasons.append("Low confidence - unusual patterns")
        
        # Recent trends
        if not df.empty:
            recent_emotions = df.tail(5)['emotion'].value_counts()
            if emotion in recent_emotions.index:
                reasons.append(f"Recent pattern: {emotion} is common")
        
        return " | ".join(reasons) if reasons else "Typical pattern"
    
    def identify_stress_peaks(self, forecast_hours=3):
        """Identify when stress levels will peak"""
        forecasts = self.forecast_emotions(hours_ahead=forecast_hours)
        
        stress_emotions = ['stressed', 'anxious', 'angry']
        peaks = []
        
        for forecast in forecasts:
            if forecast['emotion'] in stress_emotions:
                peaks.append({
                    'time': forecast['time'],
                    'emotion': forecast['emotion'],
                    'severity': forecast['confidence'],
                    'recommendation': self._get_stress_intervention(forecast['emotion'])
                })
        
        return peaks
    
    def identify_focus_windows(self, forecast_hours=3):
        """Identify optimal focus windows in next hours"""
        forecasts = self.forecast_emotions(hours_ahead=forecast_hours)
        
        focus_emotions = ['focused', 'calm', 'excited']
        windows = []
        
        for forecast in forecasts:
            if forecast['emotion'] in focus_emotions:
                windows.append({
                    'time': forecast['time'],
                    'emotion': forecast['emotion'],
                    'quality': forecast['confidence'],
                    'duration_minutes': 60,  # Typical focus window
                    'recommendation': f"Perfect time for {self._get_task_type_for_emotion(forecast['emotion'])}"
                })
        
        return windows
    
    def _get_stress_intervention(self, emotion):
        """Get intervention recommendation for stress"""
        interventions = {
            'stressed': 'Take 5-minute break, practice breathing',
            'anxious': 'Grounding exercise recommended',
            'angry': 'Physical activity or pause recommended'
        }
        return interventions.get(emotion, 'Take a break')
    
    def _get_task_type_for_emotion(self, emotion):
        """Get recommended task type for emotion"""
        recommendations = {
            'focused': 'complex problem-solving',
            'calm': 'creative or detailed work',
            'excited': 'collaborative or novel tasks'
        }
        return recommendations.get(emotion, 'deep work')
    
    def predict_energy_crashes(self, forecast_hours=6):
        """Predict when energy will crash"""
        forecasts = self.forecast_emotions(hours_ahead=forecast_hours)
        
        crashes = []
        low_energy_emotions = ['drained', 'sad', 'calm']
        
        for i, forecast in enumerate(forecasts):
            if forecast['emotion'] in low_energy_emotions:
                # Check if previous emotion was high-energy
                if i > 0 and forecasts[i-1]['emotion'] in ['excited', 'focused', 'happy']:
                    crashes.append({
                        'time': forecast['time'],
                        'hours_from_now': forecast['hour_offset'],
                        'severity': 1 - forecast['confidence'],  # Low confidence = unexpected
                        'recommendation': 'Schedule recovery break or light tasks'
                    })
        
        return crashes


class EmotionForecastCache:
    """Cache forecasts to avoid excessive model retraining"""
    
    def __init__(self, user):
        self.user = user
        self.cache = {}
        self.last_update = None
        
    def get_cached_forecast(self, hours_ahead=3):
        """Get cached forecast if fresh"""
        if self._is_cache_fresh():
            return self.cache.get(hours_ahead)
        return None
    
    def update_cache(self, hours_ahead, forecast):
        """Update cache with new forecast"""
        self.cache[hours_ahead] = forecast
        self.last_update = timezone.now()
    
    def _is_cache_fresh(self, max_age_minutes=30):
        """Check if cache is still fresh"""
        if not self.last_update:
            return False
        
        age = (timezone.now() - self.last_update).total_seconds() / 60
        return age < max_age_minutes
