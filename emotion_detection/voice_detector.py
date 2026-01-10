import sounddevice as sd
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
import speech_recognition as sr
import pyaudio_analysis as pa
from django.utils import timezone
from .models import EmotionDetectionSession, VoiceEmotionRecord
import threading
import time
import json

class VoiceEmotionDetector:
    def __init__(self):
        self.sample_rate = 44100
        self.chunk_duration = 2  # seconds
        self.is_recording = False
        self.recording_thread = None
        self.current_session = None
        self.r = sr.Recognizer()
        
        # Voice emotion characteristics
        self.emotion_profiles = {
            'stressed': {'pitch_range': 'high', 'energy': 'high', 'tempo': 'fast'},
            'calm': {'pitch_range': 'low', 'energy': 'low', 'tempo': 'slow'},
            'excited': {'pitch_range': 'high', 'energy': 'high', 'tempo': 'fast'},
            'sad': {'pitch_range': 'low', 'energy': 'low', 'tempo': 'slow'},
            'angry': {'pitch_range': 'high', 'energy': 'high', 'tempo': 'fast'},
            'focused': {'pitch_range': 'medium', 'energy': 'medium', 'tempo': 'steady'}
        }
    
    def start_voice_detection(self, user):
        """Start voice emotion detection"""
        if self.is_recording:
            self.stop_voice_detection()
            
        self.current_session = EmotionDetectionSession.objects.create(user=user)
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
    def stop_voice_detection(self):
        """Stop voice emotion detection"""
        self.is_recording = False
        if self.current_session:
            self.current_session.end_time = timezone.now()
            self.current_session.is_active = False
            self.current_session.save()
            self.current_session = None
    
    def _record_loop(self):
        """Main recording loop"""
        while self.is_recording and self.current_session:
            try:
                # Record audio chunk
                audio_data = sd.rec(
                    int(self.sample_rate * self.chunk_duration),
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32'
                )
                sd.wait()  # Wait for recording to complete
                
                # Analyze voice characteristics
                emotion_data = self._analyze_voice(audio_data.flatten())
                
                if emotion_data:
                    # Save voice emotion record
                    VoiceEmotionRecord.objects.create(
                        session=self.current_session,
                        emotion=emotion_data['emotion'],
                        confidence=emotion_data['confidence'],
                        pitch_mean=emotion_data['pitch_mean'],
                        pitch_std=emotion_data['pitch_std'],
                        energy=emotion_data['energy'],
                        tempo=emotion_data['tempo'],
                        spectral_features=emotion_data['spectral_features']
                    )
                    
            except Exception as e:
                print(f"Voice recording error: {e}")
                
            time.sleep(1)  # Brief pause between recordings
    
    def _analyze_voice(self, audio_data):
        """Analyze voice characteristics for emotion detection"""
        try:
            # Extract pitch (fundamental frequency)
            pitches = self._extract_pitch(audio_data)
            
            # Calculate energy (RMS)
            energy = np.sqrt(np.mean(audio_data**2))
            
            # Calculate tempo (speaking rate approximation)
            tempo = self._estimate_tempo(audio_data)
            
            # Extract spectral features
            spectral_features = self._extract_spectral_features(audio_data)
            
            # Determine emotion based on voice characteristics
            emotion = self._classify_voice_emotion(pitches, energy, tempo, spectral_features)
            
            return {
                'emotion': emotion,
                'confidence': 0.75,  # Placeholder confidence
                'pitch_mean': np.mean(pitches) if len(pitches) > 0 else 0,
                'pitch_std': np.std(pitches) if len(pitches) > 0 else 0,
                'energy': energy,
                'tempo': tempo,
                'spectral_features': spectral_features
            }
            
        except Exception as e:
            print(f"Voice analysis error: {e}")
            return None
    
    def _extract_pitch(self, audio_data):
        """Extract fundamental frequency (pitch) from audio"""
        # Use autocorrelation for pitch detection
        autocorr = np.correlate(audio_data, audio_data, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find peaks in autocorrelation
        peaks, _ = signal.find_peaks(autocorr, height=0.1)
        
        if len(peaks) > 0:
            # Convert peak positions to frequencies
            pitches = []
            for peak in peaks[:10]:  # Take first 10 peaks
                if peak > 0:
                    freq = self.sample_rate / peak
                    if 50 < freq < 500:  # Human voice range
                        pitches.append(freq)
            return pitches
        return []
    
    def _estimate_tempo(self, audio_data):
        """Estimate speaking tempo from audio"""
        # Simple tempo estimation based on energy fluctuations
        energy_envelope = np.abs(audio_data)
        
        # Find peaks in energy envelope (syllable-like patterns)
        peaks, _ = signal.find_peaks(energy_envelope, height=np.mean(energy_envelope))
        
        if len(peaks) > 1:
            # Calculate average time between peaks
            intervals = np.diff(peaks) / self.sample_rate
            avg_interval = np.mean(intervals)
            
            # Convert to tempo (peaks per second)
            tempo = 1.0 / avg_interval if avg_interval > 0 else 0
            return min(tempo, 10)  # Cap at reasonable maximum
        return 0
    
    def _extract_spectral_features(self, audio_data):
        """Extract spectral features from audio"""
        # Compute FFT
        fft_vals = fft(audio_data)
        fft_freq = fftfreq(len(audio_data), 1/self.sample_rate)
        
        # Calculate spectral centroid (brightness)
        magnitude = np.abs(fft_vals[:len(fft_vals)//2])
        freqs = fft_freq[:len(fft_freq)//2]
        
        if np.sum(magnitude) > 0:
            spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
        else:
            spectral_centroid = 0
        
        # Calculate spectral rolloff
        cumsum = np.cumsum(magnitude)
        rolloff_point = 0.85 * np.sum(magnitude)
        rolloff_idx = np.where(cumsum >= rolloff_point)[0]
        
        if len(rolloff_idx) > 0:
            spectral_rolloff = freqs[rolloff_idx[0]]
        else:
            spectral_rolloff = freqs[-1]
        
        return {
            'centroid': spectral_centroid,
            'rolloff': spectral_rolloff,
            'energy_distribution': magnitude.tolist()[:100]  # First 100 frequency bins
        }
    
    def _classify_voice_emotion(self, pitches, energy, tempo, spectral_features):
        """Classify emotion based on voice characteristics"""
        pitch_mean = np.mean(pitches) if len(pitches) > 0 else 0
        pitch_std = np.std(pitches) if len(pitches) > 0 else 0
        
        # Simple rule-based emotion classification
        if energy > 0.1 and tempo > 3 and pitch_mean > 200:
            return 'stressed'
        elif energy < 0.05 and tempo < 2 and pitch_mean < 150:
            return 'calm'
        elif energy > 0.08 and tempo > 2.5 and pitch_std > 50:
            return 'excited'
        elif energy < 0.04 and tempo < 1.5 and pitch_mean < 120:
            return 'sad'
        elif energy > 0.07 and tempo > 2 and pitch_mean > 180:
            return 'angry'
        elif 0.04 < energy < 0.08 and 1.5 < tempo < 3:
            return 'focused'
        else:
            return 'neutral'

# Global voice detector instance
voice_detector = VoiceEmotionDetector()
