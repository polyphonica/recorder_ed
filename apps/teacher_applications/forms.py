"""
Forms for teacher applications.
"""
from django import forms
from django.utils import timezone
from .models import TeacherApplication


class TeacherApplicationForm(forms.ModelForm):
    """Form for prospective teachers to apply to teach on the platform"""

    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Your phone number (optional)'
        }),
        label='Phone Number',
        help_text='Optional - helps us contact you faster'
    )

    teaching_biography = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'Tell us about your teaching experience, musical background, and approach to teaching...',
            'rows': 6
        }),
        label='Teaching Biography & Experience',
        help_text='Share your teaching journey, experience level, and what makes your teaching unique'
    )

    qualifications = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'List any relevant qualifications, certifications, or professional memberships...',
            'rows': 4
        }),
        label='Qualifications',
        help_text='Formal qualifications are not required, but please share any you have'
    )

    subjects = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Recorder, Flute, Music Theory'
        }),
        label='Subjects You Teach',
        help_text='List the instruments or subjects you teach'
    )

    dbs_check = forms.ChoiceField(
        choices=TeacherApplication.DBS_STATUS_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary'
        }),
        label='DBS Check / Background Check Status',
        help_text='Required for teaching children in the UK'
    )

    teaching_format = forms.MultipleChoiceField(
        choices=TeacherApplication.TEACHING_FORMAT_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        label='Preferred Teaching Format',
        help_text='Select all that apply'
    )

    availability = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'e.g., Weekday afternoons, Saturday mornings...',
            'rows': 3
        }),
        label='General Availability',
        help_text='When are you generally available to teach?'
    )

    terms_agreed = forms.BooleanField(
        required=True,
        label='I understand and agree',
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        help_text=(
            'I understand that: (1) The platform administrator or representative may request to '
            'observe my online lessons, (2) I will be subject to a platform commission on lesson '
            'fees, (3) I must comply with safeguarding requirements when teaching children, '
            '(4) Formal qualifications are not required but teaching competence will be assessed'
        )
    )

    class Meta:
        model = TeacherApplication
        fields = ['name', 'email', 'phone', 'teaching_biography', 'qualifications',
                  'subjects', 'availability', 'terms_agreed']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'your.email@example.com'
            }),
        }

    def clean_teaching_format(self):
        """Convert list of teaching formats to comma-separated string."""
        formats = self.cleaned_data.get('teaching_format', [])
        return ','.join(formats) if formats else ''

    def save(self, commit=True):
        """Save the application with terms agreement timestamp and map field names."""
        application = super().save(commit=False)

        # Map form field names to model field names
        application.dbs_check_status = self.cleaned_data.get('dbs_check')
        application.teaching_formats = self.cleaned_data.get('teaching_format')

        # Set terms agreement timestamp
        if application.terms_agreed:
            application.terms_agreed_at = timezone.now()

        if commit:
            application.save()

        return application
