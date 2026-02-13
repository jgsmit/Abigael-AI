from django import forms
from .companion_models import Persona, PersonaVariant, CompanionProfile, JournalEntry, JournalMedia
from .biofeedback_models import BiofeedbackDevice, BiofeedbackIntegrationConfig
from .gamification_models import RewardOption


class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = ['name', 'description', 'traits', 'default_tone', 'default_voice', 'is_public']
        widgets = {
            'traits': forms.Textarea(attrs={'rows': 4}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class PersonaVariantForm(forms.ModelForm):
    class Meta:
        model = PersonaVariant
        fields = ['persona', 'name', 'description', 'overrides', 'is_active']
        widgets = {
            'overrides': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class ProfilePersonaSelectForm(forms.ModelForm):
    class Meta:
        model = CompanionProfile
        fields = ['selected_persona', 'selected_persona_variant']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # By default, don't show all variants until a persona is selected
        try:
            if self.instance and self.instance.selected_persona:
                self.fields['selected_persona_variant'].queryset = self.instance.selected_persona.variants.filter(is_active=True)
            else:
                self.fields['selected_persona_variant'].queryset = PersonaVariant.objects.none()
        except Exception:
            self.fields['selected_persona_variant'].queryset = PersonaVariant.objects.none()


class JournalEntryForm(forms.ModelForm):
    """Form for creating multimodal journal entries."""
    secondary_emotions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'JSON: [{"emotion":"anxious","intensity":0.5}]'}),
        help_text='Optional secondary emotions as JSON'
    )
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'comma-separated tags'}),
        help_text='User-defined tags'
    )
    media_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        help_text='Optional images, audio, or video files'
    )

    class Meta:
        model = JournalEntry
        fields = [
            'entry_type', 'primary_emotion', 'emotion_intensity', 'emotion_notes',
            'personal_reflection', 'gratitude_notes', 'key_moments', 'challenges', 'achievements'
        ]
        widgets = {
            'entry_type': forms.Select(attrs={'class': 'form-control'}),
            'emotion_intensity': forms.NumberInput(attrs={'type': 'range', 'min': '0', 'max': '1', 'step': '0.1'}),
            'emotion_notes': forms.Textarea(attrs={'rows': 2}),
            'personal_reflection': forms.Textarea(attrs={'rows': 4}),
            'gratitude_notes': forms.Textarea(attrs={'rows': 2}),
            'key_moments': forms.Textarea(attrs={'rows': 2}),
            'challenges': forms.Textarea(attrs={'rows': 2}),
            'achievements': forms.Textarea(attrs={'rows': 2}),
        }


class JournalMediaForm(forms.ModelForm):
    """Form for adding media to journal entries."""
    class Meta:
        model = JournalMedia
        fields = ['file', 'created_at']
        widgets = {
            'file': forms.FileInput(),
            'created_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class BiofeedbackDeviceForm(forms.ModelForm):
    """Form for connecting a biofeedback device."""
    class Meta:
        model = BiofeedbackDevice
        fields = ['device_name', 'device_type', 'device_id', 'sync_frequency_minutes']
        widgets = {
            'device_name': forms.TextInput(attrs={'placeholder': 'e.g., My Fitbit'}),
            'device_type': forms.Select(),
            'device_id': forms.TextInput(attrs={'placeholder': 'Device ID from wearable'}),
            'sync_frequency_minutes': forms.NumberInput(attrs={'min': '15', 'max': '1440'}),
        }
        help_texts = {
            'device_id': 'The unique identifier for your device (usually found in settings)',
            'sync_frequency_minutes': 'How often to sync data (in minutes, 15-1440)',
        }


class BiofeedbackConfigForm(forms.ModelForm):
    """Form for biofeedback settings and thresholds."""
    class Meta:
        model = BiofeedbackIntegrationConfig
        fields = [
            'high_stress_threshold',
            'high_heart_rate_threshold',
            'low_sleep_threshold',
            'enable_alerts',
            'enable_sleep_tracking',
            'enable_stress_tracking',
            'auto_trigger_interventions',
            'share_with_therapist',
        ]
        widgets = {
            'high_stress_threshold': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '5'}),
            'high_heart_rate_threshold': forms.NumberInput(attrs={'min': '60', 'max': '200'}),
            'low_sleep_threshold': forms.NumberInput(attrs={'min': '3', 'max': '12', 'step': '0.5'}),
            'enable_alerts': forms.CheckboxInput(),
            'enable_sleep_tracking': forms.CheckboxInput(),
            'enable_stress_tracking': forms.CheckboxInput(),
            'auto_trigger_interventions': forms.CheckboxInput(),
            'share_with_therapist': forms.CheckboxInput(),
        }
        labels = {
            'high_stress_threshold': 'Alert me when stress exceeds (0-100)',
            'high_heart_rate_threshold': 'Alert me when heart rate exceeds (BPM)',
            'low_sleep_threshold': 'Alert me when sleep is below (hours)',
            'enable_alerts': 'Enable biofeedback alerts',
            'enable_sleep_tracking': 'Track sleep data',
            'enable_stress_tracking': 'Track stress levels',
            'auto_trigger_interventions': 'Automatically trigger interventions based on biofeedback',
            'share_with_therapist': 'Share biofeedback data with my therapist',
        }


class LeaderboardVisibilityForm(forms.Form):
    """Form for leaderboard visibility settings."""
    is_public = forms.BooleanField(required=False, label="Show on leaderboard")
    anonymized = forms.BooleanField(required=False, label="Hide my name (show initials only)")
    
    class Meta:
        fields = ['is_public', 'anonymized']


class RewardRedemptionForm(forms.Form):
    """Form for redeeming rewards."""
    reward = forms.ModelChoiceField(
        queryset=RewardOption.objects.filter(is_active=True),
        widget=forms.RadioSelect,
        label="Choose a reward"
    )
    
    class Meta:
        fields = ['reward']