from django import forms

from apps.scheduling.models import ReminderSettings


class ReminderSettingsForm(forms.ModelForm):
    class Meta:
        model = ReminderSettings
        fields = [
            'workshop_reminders_enabled',
            'workshop_reminder_hours',
            'lesson_reminders_enabled',
            'lesson_reminder_hours',
        ]
        widgets = {
            'workshop_reminder_hours': forms.NumberInput(attrs={'min': 1, 'max': 168, 'class': 'input input-bordered w-24'}),
            'lesson_reminder_hours': forms.NumberInput(attrs={'min': 1, 'max': 168, 'class': 'input input-bordered w-24'}),
        }
        help_texts = {
            'workshop_reminder_hours': 'Hours in advance (1–168)',
            'lesson_reminder_hours': 'Hours in advance (1–168)',
        }
