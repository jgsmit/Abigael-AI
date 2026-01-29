import requests
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .biofeedback_models import (
    BiofeedbackDevice, HeartRateRecord, SleepRecord, 
    ActivityRecord, StressRecord, BiofeedbackSession
)
import threading
import time

class BiofeedbackIntegrator:
    def __init__(self):
        self.is_syncing = False
        self.sync_thread = None
        
        # API endpoints for different services
        self.api_endpoints = {
            'fitbit': {
                'base_url': 'https://api.fitbit.com/1/user/-/',
                'auth_url': 'https://www.fitbit.com/oauth2/authorize',
                'token_url': 'https://api.fitbit.com/oauth2/token'
            },
            'apple_health': {
                # Note: Apple Health requires iOS app integration
                'base_url': None
            },
            'garmin': {
                'base_url': 'https://connectapi.garmin.com/',
                'auth_url': 'https://connect.garmin.com/oauthConfirm'
            }
        }
    
    def register_device(self, user, device_type, device_name, access_token=None, device_id=None):
        """Register a new biofeedback device"""
        device = BiofeedbackDevice.objects.create(
            user=user,
            device_name=device_name,
            device_type=device_type,
            device_id=device_id or f"{device_type}_{user.id}_{int(time.time())}",
            access_token=access_token or ''
        )
        return device
    
    def start_sync(self, user):
        """Start continuous sync for user's devices"""
        if self.is_syncing:
            return False
            
        self.is_syncing = True
        self.sync_thread = threading.Thread(target=self._sync_loop, args=(user,))
        self.sync_thread.daemon = True
        self.sync_thread.start()
        return True
    
    def stop_sync(self):
        """Stop biofeedback sync"""
        self.is_syncing = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
            self.sync_thread = None
    
    def _sync_loop(self, user):
        """Main sync loop"""
        while self.is_syncing:
            try:
                # Get all active devices for user
                devices = BiofeedbackDevice.objects.filter(user=user, is_active=True)
                
                for device in devices:
                    if device.device_type == 'fitbit':
                        self._sync_fitbit_data(device)
                    elif device.device_type == 'garmin':
                        self._sync_garmin_data(device)
                    # Add other device types as needed
                
                # Update device sync time
                devices.update(last_sync=timezone.now())
                
                # Sleep for 5 minutes between syncs
                time.sleep(300)
                
            except Exception as e:
                print(f"Biofeedback sync error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _sync_fitbit_data(self, device):
        """Sync data from Fitbit device"""
        try:
            if not device.access_token:
                return
                
            headers = {
                'Authorization': f'Bearer {device.access_token}',
                'Accept': 'application/json'
            }
            
            # Sync heart rate data (last 24 hours)
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            
            # Get heart rate data
            hr_url = f"{self.api_endpoints['fitbit']['base_url']}activities/heart/date/{yesterday}/{today}/1min.json"
            response = requests.get(hr_url, headers=headers)
            
            if response.status_code == 200:
                hr_data = response.json()
                self._process_fitbit_heart_rate(device, hr_data)
            
            # Get sleep data
            sleep_url = f"{self.api_endpoints['fitbit']['base_url']}sleep/date/{yesterday}/{today}.json"
            response = requests.get(sleep_url, headers=headers)
            
            if response.status_code == 200:
                sleep_data = response.json()
                self._process_fitbit_sleep(device, sleep_data)
            
            # Get activity data
            activity_url = f"{self.api_endpoints['fitbit']['base_url']}activities/date/{today}.json"
            response = requests.get(activity_url, headers=headers)
            
            if response.status_code == 200:
                activity_data = response.json()
                self._process_fitbit_activity(device, activity_data)
                
        except Exception as e:
            print(f"Fitbit sync error: {e}")
    
    def _process_fitbit_heart_rate(self, device, hr_data):
        """Process Fitbit heart rate data"""
        try:
            if 'activities-heart' in hr_data and 'activities-heart-intraday' in hr_data:
                # Process daily summary
                for day_data in hr_data['activities-heart']:
                    date_str = day_data['dateTime']
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Create or update biofeedback session
                    session, created = BiofeedbackSession.objects.get_or_create(
                        user=device.user,
                        start_time=datetime.combine(date, datetime.min.time()),
                        defaults={'end_time': datetime.combine(date + timedelta(days=1), datetime.min.time())}
                    )
                    
                    # Update session metrics
                    if 'restingHeartRate' in day_data:
                        session.avg_heart_rate = day_data['restingHeartRate']
                        session.save()
                
                # Process intraday data
                intraday_data = hr_data['activities-heart-intraday']
                if 'dataset' in intraday_data:
                    for record in intraday_data['dataset']:
                        timestamp_str = record['time']
                        heart_rate = record['value']
                        
                        # Parse timestamp
                        timestamp = datetime.strptime(timestamp_str, '%H:%M:%S')
                        full_timestamp = datetime.combine(
                            datetime.now().date(), 
                            timestamp.time()
                        )
                        
                        # Create heart rate record
                        HeartRateRecord.objects.update_or_create(
                            device=device,
                            timestamp=full_timestamp,
                            defaults={'heart_rate': heart_rate}
                        )
                        
        except Exception as e:
            print(f"Heart rate processing error: {e}")
    
    def _process_fitbit_sleep(self, device, sleep_data):
        """Process Fitbit sleep data"""
        try:
            if 'sleep' in sleep_data:
                for sleep in sleep_data['sleep']:
                    sleep_date = datetime.strptime(sleep['dateOfSleep'], '%Y-%m-%d').date()
                    start_time = datetime.strptime(sleep['startTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    end_time = datetime.strptime(sleep['endTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    
                    # Calculate sleep duration
                    duration = (end_time - start_time).total_seconds() / 3600  # Convert to hours
                    
                    SleepRecord.objects.update_or_create(
                        device=device,
                        sleep_date=sleep_date,
                        defaults={
                            'bedtime': start_time,
                            'wake_time': end_time,
                            'total_sleep_hours': duration,
                            'sleep_score': sleep.get('efficiency', 0),
                            'deep_sleep_hours': sleep.get('levels', {}).get('summary', {}).get('deep', {}).get('minutes', 0) / 60,
                            'rem_sleep_hours': sleep.get('levels', {}).get('summary', {}).get('rem', {}).get('minutes', 0) / 60,
                            'light_sleep_hours': sleep.get('levels', {}).get('summary', {}).get('light', {}).get('minutes', 0) / 60,
                        }
                    )
                    
        except Exception as e:
            print(f"Sleep data processing error: {e}")
    
    def _process_fitbit_activity(self, device, activity_data):
        """Process Fitbit activity data"""
        try:
            if 'summary' in activity_data:
                summary = activity_data['summary']
                
                # Create activity record for the day
                ActivityRecord.objects.update_or_create(
                    device=device,
                    timestamp=datetime.combine(datetime.now().date(), datetime.min.time()),
                    activity_type='daily_summary',
                    defaults={
                        'steps_count': summary.get('steps', 0),
                        'calories_burned': summary.get('caloriesOut', 0),
                        'active_zone_minutes': summary.get('activeZoneMinutes', {}).get('total', 0),
                        'distance_km': summary.get('distances', [{}])[0].get('distance', 0) / 1000,  # Convert to km
                    }
                )
                
        except Exception as e:
            print(f"Activity data processing error: {e}")
    
    def _sync_garmin_data(self, device):
        """Sync data from Garmin device using Garmin Connect API"""
        try:
            from garminconnect import Garmin
            
            client = Garmin(device.auth_token)
            
            # Get heart rate data
            hr_data = client.get_heart_rates(0)
            if hr_data:
                for reading in hr_data:
                    BiofeedbackData.objects.update_or_create(
                        user=device.user,
                        device=device,
                        metric_type='heart_rate',
                        timestamp=reading.get('timestamp'),
                        defaults={'value': reading.get('value', 0), 'unit': 'bpm'}
                    )
            
            # Get stress data
            stress_data = client.get_stress_data()
            if stress_data:
                for reading in stress_data:
                    BiofeedbackData.objects.update_or_create(
                        user=device.user,
                        device=device,
                        metric_type='stress',
                        timestamp=reading.get('timestamp'),
                        defaults={'value': reading.get('value', 0), 'unit': '0-100'}
                    )
            
            # Get sleep data
            sleep_data = client.get_sleep_data()
            if sleep_data:
                for reading in sleep_data:
                    BiofeedbackData.objects.update_or_create(
                        user=device.user,
                        device=device,
                        metric_type='sleep',
                        timestamp=reading.get('timestamp'),
                        defaults={'value': reading.get('duration_minutes', 0) / 60, 'unit': 'hours'}
                    )
            
            device.last_sync = timezone.now()
            device.sync_status = 'success'
            device.save()
            
        except Exception as e:
            device.sync_status = 'failed'
            device.error_message = str(e)
            device.save()
            print(f"Garmin sync error: {e}")
    
    def get_current_stress_level(self, user):
        """Get current stress level from biofeedback data"""
        try:
            # Get most recent stress record
            recent_stress = StressRecord.objects.filter(
                device__user=user
            ).order_by('-timestamp').first()
            
            if recent_stress:
                return recent_stress.stress_level
            
            # Estimate stress from heart rate if no direct stress data
            recent_hr = HeartRateRecord.objects.filter(
                device__user=user
            ).order_by('-timestamp').first()
            
            if recent_hr:
                # Simple stress estimation based on heart rate
                resting_hr = 70  # Average resting heart rate
                if recent_hr.heart_rate > resting_hr + 20:
                    return min(80, (recent_hr.heart_rate - resting_hr) * 2)
                elif recent_hr.heart_rate < resting_hr - 10:
                    return 20  # Very relaxed
                else:
                    return 40  # Normal
            
            return 50  # Default to neutral
            
        except Exception as e:
            print(f"Stress level error: {e}")
            return 50
    
    def get_energy_level(self, user):
        """Get current energy level from biofeedback data"""
        try:
            # Get today's activity
            today = timezone.now().date()
            today_activity = ActivityRecord.objects.filter(
                device__user=user,
                timestamp__date=today
            ).first()
            
            # Get last night's sleep
            last_night = today - timedelta(days=1)
            last_sleep = SleepRecord.objects.filter(
                device__user=user,
                sleep_date=last_night
            ).first()
            
            energy_score = 50  # Default neutral
            
            # Factor in sleep quality
            if last_sleep:
                sleep_quality = last_sleep.sleep_score or 50
                energy_score += (sleep_quality - 50) * 0.3
            
            # Factor in activity level
            if today_activity:
                steps = today_activity.steps_count
                if steps > 10000:
                    energy_score += 20
                elif steps > 5000:
                    energy_score += 10
                elif steps < 2000:
                    energy_score -= 10
            
            # Get current heart rate
            current_hr = HeartRateRecord.objects.filter(
                device__user=user
            ).order_by('-timestamp').first()
            
            if current_hr:
                # Higher heart rate might indicate more energy (within reason)
                if 60 <= current_hr.heart_rate <= 100:
                    energy_score += (current_hr.heart_rate - 80) * 0.5
            
            return max(0, min(100, energy_score))
            
        except Exception as e:
            print(f"Energy level error: {e}")
            return 50
    
    def analyze_emotion_biofeedback_correlation(self, user, emotion, days=30):
        """Analyze correlation between emotion and biofeedback data"""
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get emotion records
            from tasks.models import EmotionRecord
            emotion_records = EmotionRecord.objects.filter(
                user=user,
                emotion=emotion,
                timestamp__gte=cutoff_date
            )
            
            if not emotion_records.exists():
                return None
            
            # Get corresponding biofeedback data
            heart_rates = []
            stress_levels = []
            
            for record in emotion_records:
                # Get heart rate around emotion timestamp
                hr_record = HeartRateRecord.objects.filter(
                    device__user=user,
                    timestamp__gte=record.timestamp - timedelta(minutes=5),
                    timestamp__lte=record.timestamp + timedelta(minutes=5)
                ).first()
                
                if hr_record:
                    heart_rates.append(hr_record.heart_rate)
                
                # Get stress level around emotion timestamp
                stress_record = StressRecord.objects.filter(
                    device__user=user,
                    timestamp__gte=record.timestamp - timedelta(minutes=5),
                    timestamp__lte=record.timestamp + timedelta(minutes=5)
                ).first()
                
                if stress_record:
                    stress_levels.append(stress_record.stress_level)
            
            # Calculate averages
            avg_heart_rate = sum(heart_rates) / len(heart_rates) if heart_rates else 0
            avg_stress_level = sum(stress_levels) / len(stress_levels) if stress_levels else 0
            
            return {
                'emotion': emotion,
                'avg_heart_rate': avg_heart_rate,
                'avg_stress_level': avg_stress_level,
                'sample_size': len(emotion_records),
                'period_days': days
            }
            
        except Exception as e:
            print(f"Biofeedback correlation error: {e}")
            return None
    
    def get_sleep_quality_impact(self, user, days=7):
        """Analyze how sleep quality affects next-day emotions and productivity"""
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get sleep records
            sleep_records = SleepRecord.objects.filter(
                device__user=user,
                sleep_date__gte=cutoff_date
            ).order_by('sleep_date')
            
            analysis_results = []
            
            for sleep in sleep_records:
                next_day = sleep.sleep_date + timedelta(days=1)
                
                # Get next day's emotions
                from tasks.models import EmotionRecord
                next_day_emotions = EmotionRecord.objects.filter(
                    user=user,
                    timestamp__date=next_day
                )
                
                # Get next day's completed tasks
                from tasks.models import Task
                completed_tasks = Task.objects.filter(
                    user=user,
                    status='completed',
                    completed_at__date=next_day
                ).count()
                
                analysis_results.append({
                    'sleep_date': sleep.sleep_date,
                    'sleep_quality': sleep.sleep_score or 0,
                    'total_sleep_hours': sleep.total_sleep_hours,
                    'next_day_emotions': list(next_day_emotions.values_list('emotion', flat=True)),
                    'next_day_tasks_completed': completed_tasks
                })
            
            return analysis_results
            
        except Exception as e:
            print(f"Sleep quality analysis error: {e}")
            return []

# Global biofeedback integrator instance
biofeedback_integrator = BiofeedbackIntegrator()
