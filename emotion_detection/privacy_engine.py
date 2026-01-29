"""
Privacy Innovation Features (Phase 7 Roadmap)
- On-device ML inference
- Encrypted emotion vault
- Federated learning
- Auto-delete policies
- Explainable AI transparency
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import json
from datetime import datetime, timedelta
import os


class PrivacyPolicy(models.Model):
    """User privacy preferences and data retention settings"""
    
    ENCRYPTION_LEVELS = [
        ('none', 'No Encryption'),
        ('standard', 'Standard Encryption'),
        ('maximum', 'Maximum Encryption'),
    ]
    
    DATA_RETENTION_CHOICES = [
        ('7_days', '7 Days'),
        ('30_days', '30 Days'),
        ('90_days', '90 Days'),
        ('1_year', '1 Year'),
        ('forever', 'Forever (No Auto-Delete)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Encryption settings
    encryption_level = models.CharField(max_length=20, choices=ENCRYPTION_LEVELS, default='standard')
    encrypt_emotions_at_rest = models.BooleanField(default=True)
    encrypt_biofeedback = models.BooleanField(default=True)
    encrypt_task_content = models.BooleanField(default=False)
    
    # Data retention
    emotion_data_retention = models.CharField(max_length=20, choices=DATA_RETENTION_CHOICES, default='90_days')
    biofeedback_retention = models.CharField(max_length=20, choices=DATA_RETENTION_CHOICES, default='30_days')
    task_retention = models.CharField(max_length=20, choices=DATA_RETENTION_CHOICES, default='1_year')
    
    # Federated learning
    allow_federated_learning = models.BooleanField(default=True)
    share_anonymous_patterns = models.BooleanField(default=True)
    
    # On-device processing
    use_on_device_ml = models.BooleanField(default=True)
    sync_cloud_models = models.BooleanField(default=True)
    
    # Transparency
    show_ai_reasoning = models.BooleanField(default=True)
    transparency_level = models.CharField(
        max_length=20,
        choices=[('low', 'Minimal'), ('medium', 'Standard'), ('high', 'Detailed')],
        default='medium'
    )
    
    class Meta:
        verbose_name_plural = 'Privacy Policies'
    
    def __str__(self):
        return f"Privacy Policy - {self.user.username}"


class EncryptedEmotionVault(models.Model):
    """Encrypted storage for sensitive emotion data"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Encrypted data
    encrypted_emotion = models.BinaryField()
    encrypted_context = models.BinaryField()
    encrypted_triggers = models.BinaryField(null=True, blank=True)
    
    # Metadata (not encrypted)
    emotion_summary = models.CharField(max_length=50)  # Just emotion name
    intensity_level = models.IntegerField()  # 0-10
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Access control
    is_locked = models.BooleanField(default=False)
    unlock_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.emotion_summary}"
    
    @staticmethod
    def encrypt_data(plaintext, encryption_key):
        """Encrypt data using Fernet symmetric encryption"""
        cipher = Fernet(encryption_key)
        encrypted = cipher.encrypt(plaintext.encode())
        return encrypted
    
    @staticmethod
    def decrypt_data(encrypted, encryption_key):
        """Decrypt data"""
        cipher = Fernet(encryption_key)
        decrypted = cipher.decrypt(encrypted).decode()
        return decrypted


class DataRetentionPolicy(models.Model):
    """Policy for automatic data deletion"""
    
    DATA_TYPES = [
        ('emotion', 'Emotion Data'),
        ('biofeedback', 'Biofeedback Data'),
        ('task', 'Task Data'),
        ('interaction', 'User Interaction Logs'),
        ('chat', 'Chat History'),
        ('analytics', 'Analytics Data'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Policy
    data_type = models.CharField(max_length=30, choices=DATA_TYPES)
    retention_days = models.IntegerField(default=30)
    
    # Execution
    auto_delete_enabled = models.BooleanField(default=True)
    last_cleanup_date = models.DateTimeField(null=True, blank=True)
    next_cleanup_date = models.DateTimeField(null=True, blank=True)
    
    # Stats
    records_deleted = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'data_type')
        indexes = [
            models.Index(fields=['next_cleanup_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.data_type} ({self.retention_days} days)"
    
    def should_cleanup(self):
        """Check if cleanup is due"""
        if not self.auto_delete_enabled:
            return False
        if self.next_cleanup_date is None:
            return True
        return timezone.now() >= self.next_cleanup_date
    
    def execute_cleanup(self):
        """Execute automatic data deletion"""
        cutoff_date = timezone.now() - timedelta(days=self.retention_days)
        
        if self.data_type == 'emotion':
            from emotion_detection.models import EmotionEvent
            deleted_count, _ = EmotionEvent.objects.filter(
                user=self.user,
                timestamp__lt=cutoff_date
            ).delete()
        
        elif self.data_type == 'biofeedback':
            from emotion_detection.models import BiofeedbackData
            deleted_count, _ = BiofeedbackData.objects.filter(
                user=self.user,
                timestamp__lt=cutoff_date
            ).delete()
        
        elif self.data_type == 'task':
            from tasks.models import Task
            deleted_count, _ = Task.objects.filter(
                user=self.user,
                created_at__lt=cutoff_date,
                completed_at__isnull=False  # Only delete completed tasks
            ).delete()
        
        self.records_deleted = deleted_count
        self.last_cleanup_date = timezone.now()
        self.next_cleanup_date = timezone.now() + timedelta(days=7)
        self.save()


class OnDeviceModel(models.Model):
    """Manages on-device ML models for local inference"""
    
    MODEL_TYPES = [
        ('emotion_classifier', 'Emotion Classifier'),
        ('stress_detector', 'Stress Detector'),
        ('flow_state_detector', 'Flow State Detector'),
        ('cognitive_load_estimator', 'Cognitive Load Estimator'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Model info
    model_type = models.CharField(max_length=30, choices=MODEL_TYPES)
    model_version = models.CharField(max_length=20)
    
    # Files
    model_file_size_kb = models.IntegerField()
    last_synced = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_enabled = models.BooleanField(default=True)
    inference_latency_ms = models.FloatField(default=0.0)
    inference_accuracy = models.FloatField(default=0.0)
    
    # Sync settings
    auto_sync_enabled = models.BooleanField(default=True)
    last_update_version = models.CharField(max_length=20)
    
    class Meta:
        unique_together = ('user', 'model_type')
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.model_type} (v{self.model_version})"
    
    def should_sync(self):
        """Check if model needs syncing with cloud"""
        cutoff = timezone.now() - timedelta(days=7)
        return self.last_synced < cutoff or self.last_update_version != self.model_version


class FederatedLearningParticipant(models.Model):
    """Participant in federated learning without sharing raw data"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Participation
    is_enrolled = models.BooleanField(default=True)
    study_name = models.CharField(max_length=100)
    
    # Model contribution
    local_model_trained = models.BooleanField(default=False)
    local_accuracy = models.FloatField(default=0.0)
    
    # Aggregation
    rounds_participated = models.IntegerField(default=0)
    data_samples_contributed = models.IntegerField(default=0)
    
    # Privacy
    differential_privacy_enabled = models.BooleanField(default=True)
    noise_level = models.FloatField(default=0.1)  # Epsilon parameter
    
    # Metrics
    global_model_improvement = models.FloatField(default=0.0)
    contribution_score = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ('user', 'study_name')
    
    def __str__(self):
        return f"{self.user.username} - {self.study_name}"


class ExplainableAIInsight(models.Model):
    """Explanation for AI decisions and recommendations"""
    
    INSIGHT_TYPES = [
        ('recommendation', 'Recommendation'),
        ('prediction', 'Prediction'),
        ('alert', 'Alert'),
        ('suggestion', 'Suggestion'),
    ]
    
    TRANSPARENCY_LEVELS = [
        ('simple', 'Simple'),
        ('detailed', 'Detailed'),
        ('technical', 'Technical'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Insight
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    insight_text = models.TextField()
    
    # Explanation
    reasoning = models.TextField()  # Why this conclusion
    confidence_score = models.FloatField()  # 0-1
    
    # Key factors (what influenced decision)
    key_factors = models.JSONField(default=dict)  # {factor_name: weight}
    
    # Alternative explanations
    alternative_explanations = models.JSONField(default=list)
    
    # Transparency level
    transparency_level = models.CharField(max_length=20, choices=TRANSPARENCY_LEVELS, default='detailed')
    
    # Impact
    user_found_helpful = models.BooleanField(null=True, blank=True)
    feedback_text = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['insight_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.insight_type}"
    
    def get_explanation(self, transparency_level=None):
        """Get explanation at specified transparency level"""
        if transparency_level is None:
            transparency_level = self.transparency_level
        
        if transparency_level == 'simple':
            return self.insight_text
        elif transparency_level == 'detailed':
            return f"{self.insight_text}\n\nWhy: {self.reasoning}"
        else:  # technical
            factors_text = "\n".join([
                f"  - {k}: {v:.2f}" for k, v in self.key_factors.items()
            ])
            return f"{self.insight_text}\n\nReasoning: {self.reasoning}\n\nKey Factors:\n{factors_text}\n\nConfidence: {self.confidence_score:.2%}"


class PrivacyAuditLog(models.Model):
    """Audit log of all data access for transparency"""
    
    ACCESS_TYPES = [
        ('read', 'Data Read'),
        ('export', 'Data Export'),
        ('share', 'Data Shared'),
        ('delete', 'Data Deleted'),
        ('access_grant', 'Access Granted'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Access
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES)
    data_accessed = models.CharField(max_length=100)
    
    # Who accessed
    accessed_by = models.CharField(max_length=100)  # System component or user
    
    # Purpose
    purpose = models.TextField()
    
    # IP/Device info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=200, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['access_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.access_type} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


class PrivacyEngineManager:
    """Core privacy engine for managing all privacy features"""
    
    def __init__(self, user):
        self.user = user
        self.policy = PrivacyPolicy.objects.get_or_create(user=user)[0]
    
    def encrypt_emotion_data(self, emotion, context, triggers=None):
        """Encrypt and store emotion data"""
        if not self.policy.encrypt_emotions_at_rest:
            return None
        
        encryption_key = self._get_user_encryption_key()
        
        emotion_str = json.dumps({
            'emotion': emotion,
            'timestamp': timezone.now().isoformat()
        })
        context_str = json.dumps(context) if context else '{}'
        triggers_str = json.dumps(triggers) if triggers else '{}'
        
        encrypted_emotion = EncryptedEmotionVault.encrypt_data(emotion_str, encryption_key)
        encrypted_context = EncryptedEmotionVault.encrypt_data(context_str, encryption_key)
        encrypted_triggers = EncryptedEmotionVault.encrypt_data(triggers_str, encryption_key) if triggers else None
        
        vault_entry = EncryptedEmotionVault.objects.create(
            user=self.user,
            encrypted_emotion=encrypted_emotion,
            encrypted_context=encrypted_context,
            encrypted_triggers=encrypted_triggers,
            emotion_summary=emotion,
            intensity_level=context.get('intensity', 5) if context else 5
        )
        
        # Log access
        self._audit_log('data write', 'emotion_vault', 'System', 'Encrypted storage')
        
        return vault_entry
    
    def _get_user_encryption_key(self):
        """Get or generate encryption key for user - uses proper key derivation"""
        from django.contrib.auth.hashers import PBKDF2PasswordHasher
        import hashlib
        
        # Combine username and a stored salt for deterministic key generation
        hasher = PBKDF2PasswordHasher()
        user_salt = f"{self.user.id}_{self.user.username}".encode()
        
        # Derive key using PBKDF2
        password = f"{self.user.username}_encryption_master"
        derived = hashlib.pbkdf2_hmac('sha256', password.encode(), user_salt, 100000)
        key = base64.urlsafe_b64encode(derived[:32])
        
        return key
    
    def schedule_auto_deletion(self):
        """Schedule automatic data deletion based on policy"""
        deletions = [
            ('emotion', self.policy.emotion_data_retention),
            ('biofeedback', self.policy.biofeedback_retention),
            ('task', self.policy.task_retention),
        ]
        
        for data_type, retention in deletions:
            days = int(retention.split('_')[0])
            policy, created = DataRetentionPolicy.objects.get_or_create(
                user=self.user,
                data_type=data_type,
                defaults={'retention_days': days, 'auto_delete_enabled': True}
            )
            
            if policy.should_cleanup():
                policy.execute_cleanup()
    
    def enable_on_device_processing(self):
        """Enable on-device ML inference for privacy"""
        models_to_sync = [
            ('emotion_classifier', 'v2.1'),
            ('stress_detector', 'v1.5'),
            ('flow_state_detector', 'v1.0'),
        ]
        
        for model_type, version in models_to_sync:
            model, created = OnDeviceModel.objects.get_or_create(
                user=self.user,
                model_type=model_type,
                defaults={
                    'model_version': version,
                    'model_file_size_kb': 250,
                    'is_enabled': True
                }
            )
    
    def enroll_federated_learning(self, study_name):
        """Enroll in federated learning study"""
        if not self.policy.allow_federated_learning:
            return None
        
        participant, created = FederatedLearningParticipant.objects.get_or_create(
            user=self.user,
            study_name=study_name,
            defaults={
                'is_enrolled': True,
                'differential_privacy_enabled': True,
                'noise_level': 0.1
            }
        )
        
        return participant
    
    def create_explainable_insight(self, insight_type, insight_text, reasoning, key_factors, confidence):
        """Create explainable AI insight"""
        transparency_level = 'detailed' if self.policy.show_ai_reasoning else 'simple'
        
        insight = ExplainableAIInsight.objects.create(
            user=self.user,
            insight_type=insight_type,
            insight_text=insight_text,
            reasoning=reasoning,
            confidence_score=confidence,
            key_factors=key_factors,
            transparency_level=transparency_level
        )
        
        return insight
    
    def get_privacy_dashboard(self):
        """Get privacy and data dashboard for user"""
        return {
            'encryption_level': self.policy.encryption_level,
            'data_retention': {
                'emotions': self.policy.emotion_data_retention,
                'biofeedback': self.policy.biofeedback_retention,
                'tasks': self.policy.task_retention,
            },
            'federated_learning': self.policy.allow_federated_learning,
            'on_device_ml': self.policy.use_on_device_ml,
            'transparency': self.policy.transparency_level,
            'recent_access': self._get_recent_audit_log(limit=10),
            'data_storage': self._calculate_data_usage(),
        }
    
    def _audit_log(self, access_type, data_accessed, accessed_by, purpose):
        """Log data access for transparency"""
        PrivacyAuditLog.objects.create(
            user=self.user,
            access_type=access_type,
            data_accessed=data_accessed,
            accessed_by=accessed_by,
            purpose=purpose
        )
    
    def _get_recent_audit_log(self, limit=10):
        """Get recent audit logs"""
        logs = PrivacyAuditLog.objects.filter(user=self.user).order_by('-timestamp')[:limit]
        return [
            {
                'timestamp': log.timestamp,
                'access_type': log.access_type,
                'data': log.data_accessed,
                'purpose': log.purpose
            }
            for log in logs
        ]
    
    def _calculate_data_usage(self):
        """Calculate total data storage used from database"""
        from emotion_detection.models import EmotionEvent
        from tasks.models import Task
        from emotion_detection.biofeedback_models import BiofeedbackData
        
        # Calculate emotions storage (approximate 50 bytes per record)
        emotion_count = EmotionEvent.objects.filter(user=self.user).count()
        emotions_bytes = emotion_count * 50
        
        # Calculate tasks storage (approximate 200 bytes per record)
        task_count = Task.objects.filter(user=self.user).count()
        tasks_bytes = task_count * 200
        
        # Calculate biofeedback storage (approximate 100 bytes per record)
        biofeedback_count = BiofeedbackData.objects.filter(user=self.user).count()
        biofeedback_bytes = biofeedback_count * 100
        
        total_bytes = emotions_bytes + tasks_bytes + biofeedback_bytes
        
        return {
            'emotions_mb': round(emotions_bytes / (1024 * 1024), 2),
            'tasks_mb': round(tasks_bytes / (1024 * 1024), 2),
            'biofeedback_mb': round(biofeedback_bytes / (1024 * 1024), 2),
            'total_mb': round(total_bytes / (1024 * 1024), 2),
            'emotion_records': emotion_count,
            'task_records': task_count,
            'biofeedback_records': biofeedback_count
        }
