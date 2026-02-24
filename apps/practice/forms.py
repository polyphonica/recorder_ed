from django import forms

from .models import PracticeEntry


class PracticeEntryForm(forms.ModelForm):
    """Form for students to log their practice sessions"""

    class Meta:
        model = PracticeEntry
        fields = [
            'practice_date', 'duration_minutes', 'child_profile',
            'pieces_practiced', 'exercises_practiced',
            'focus_areas', 'struggles', 'achievements',
            'enjoyment_rating',
            'preparing_for_exam', 'preparing_for_performance'
        ]
        widgets = {
            'practice_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '30',
                'min': '1',
                'max': '300'
            }),
            'child_profile': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'pieces_practiced': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'e.g., Sonata in F - mvmt 1, G Major scale, A Minor arpeggio'
            }),
            'exercises_practiced': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'e.g., Long tones, Tonguing exercises, Finger exercises'
            }),
            'focus_areas': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'What did you focus on today? (e.g., bars 12-16 tempo, breathing technique)'
            }),
            'struggles': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Any difficulties? (optional)'
            }),
            'achievements': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Any breakthroughs or improvements? (optional)'
            }),
            'enjoyment_rating': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'preparing_for_exam': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'preparing_for_performance': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        labels = {
            'practice_date': 'Practice Date',
            'duration_minutes': 'Practice Duration (minutes)',
            'child_profile': 'Who Practiced?',
            'pieces_practiced': 'Pieces/Songs Practiced',
            'exercises_practiced': 'Technical Exercises',
            'focus_areas': 'What I Focused On',
            'struggles': 'Challenges',
            'achievements': 'Wins & Breakthroughs',
            'enjoyment_rating': 'How enjoyable was this practice?',
            'preparing_for_exam': 'Preparing for an exam',
            'preparing_for_performance': 'Preparing for a performance/recital',
        }
        help_texts = {
            'practice_date': 'When did you practice?',
            'duration_minutes': 'How long did you practice?',
            'child_profile': 'Leave blank if you are the student',
            'preparing_for_exam': 'Check this if practicing for an upcoming exam',
            'preparing_for_performance': 'Check this if practicing for a recital or performance',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set today's date as default
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['practice_date'].initial = timezone.now().date()

        # Filter child_profile to only show user's children
        if user:
            from apps.accounts.models import ChildProfile
            self.fields['child_profile'].queryset = ChildProfile.objects.filter(guardian=user)

            # If user has no children, hide the field
            if not self.fields['child_profile'].queryset.exists():
                self.fields['child_profile'].widget = forms.HiddenInput()
                self.fields['child_profile'].required = False

        # Make optional fields clearly marked
        self.fields['exercises_practiced'].required = False
        self.fields['struggles'].required = False
        self.fields['achievements'].required = False
        self.fields['enjoyment_rating'].required = False
