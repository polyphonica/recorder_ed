from django import forms
from django.contrib.auth import get_user_model

from .models import SightReadingExample, SightReadingSet, SightReadingAssignment

User = get_user_model()


class SightReadingExampleForm(forms.ModelForm):
    class Meta:
        model = SightReadingExample
        fields = ['title', 'grade_level', 'image', 'teacher_notes', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g. Grade 1 Piece A',
            }),
            'grade_level': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': "e.g. 1, Beginner, Intermediate",
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'teacher_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Private notes about this example (only you can see this)…',
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }
        help_texts = {
            'is_public': 'Make this example visible to all teachers in the shared library',
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'name'):
            ext = image.name.rsplit('.', 1)[-1].lower()
            if ext not in ('jpg', 'jpeg', 'png', 'webp'):
                raise forms.ValidationError('Only JPG, PNG, and WebP images are allowed.')
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image must be under 5MB.')
        return image


class SightReadingSetForm(forms.ModelForm):
    class Meta:
        model = SightReadingSet
        fields = ['name', 'description', 'grade_level', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g. Grade 1 Rhythm Set A',
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Optional description…',
            }),
            'grade_level': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': "e.g. 1, Beginner",
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }
        help_texts = {
            'is_public': 'Make this set visible to all teachers',
        }


class SightReadingAssignmentForm(forms.ModelForm):
    student_selection = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full',
            'id': 'id_student_selection',
        }),
        help_text='Select the student to assign this set to',
    )

    class Meta:
        model = SightReadingAssignment
        fields = ['sight_reading_set', 'lesson', 'notes']
        widgets = {
            'sight_reading_set': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'lesson': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Optional private notes for this assignment…',
            }),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.private_teaching.models import TeacherStudentApplication
        from lessons.models import Lesson
        from datetime import date

        self.fields['student_selection'].choices = [('', '-- Select Student --')]
        self.fields['lesson'].required = False
        self.fields['lesson'].empty_label = '-- No Specific Lesson --'

        if teacher:
            self.fields['sight_reading_set'].queryset = SightReadingSet.objects.filter(
                created_by=teacher
            ).order_by('name')

            accepted_apps = TeacherStudentApplication.objects.filter(
                teacher=teacher,
                status='accepted',
            ).select_related('applicant__profile')

            student_choices = [('', '-- Select Student --')]

            for app in accepted_apps:
                user = app.applicant
                try:
                    if hasattr(user, 'profile') and user.profile.is_student:
                        full_name = user.profile.full_name or user.username
                        student_choices.append((f'user_{user.id}', full_name))
                    elif hasattr(user, 'profile') and user.profile.is_guardian:
                        for child in user.children.all():
                            student_choices.append((f'child_{child.id}', child.full_name))
                except Exception:
                    continue

            self.fields['student_selection'].choices = student_choices

            self.fields['lesson'].queryset = Lesson.objects.filter(
                teacher=teacher,
                approved_status='Accepted',
            ).order_by('-lesson_date', '-lesson_time')

        if self.instance and self.instance.pk:
            if self.instance.child_profile_id:
                self.fields['student_selection'].initial = f'child_{self.instance.child_profile_id}'
            elif self.instance.student_id:
                self.fields['student_selection'].initial = f'user_{self.instance.student_id}'

    def clean(self):
        from apps.accounts.models import ChildProfile
        cleaned_data = super().clean()
        student_selection = cleaned_data.get('student_selection')

        if not student_selection:
            raise forms.ValidationError('Please select a student.')

        if student_selection.startswith('user_'):
            user_id = int(student_selection.replace('user_', ''))
            student = User.objects.get(id=user_id)
            child_profile = None
        elif student_selection.startswith('child_'):
            child_id = student_selection.replace('child_', '')
            child_profile = ChildProfile.objects.get(id=child_id)
            student = child_profile.guardian
        else:
            raise forms.ValidationError('Invalid student selection.')

        cleaned_data['_parsed_student'] = student
        cleaned_data['_parsed_child_profile'] = child_profile
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'cleaned_data'):
            instance.student = self.cleaned_data.get('_parsed_student')
            instance.child_profile = self.cleaned_data.get('_parsed_child_profile')
        if commit:
            instance.save()
        return instance


class SessionGradeForm(forms.Form):
    RESULT_CHOICES = [
        ('', '-- Not graded --'),
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
    ]
    result = forms.ChoiceField(choices=RESULT_CHOICES, required=False)
    teacher_note = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 2,
            'placeholder': 'Private note about this exercise…',
        }),
        required=False,
    )
    next_position = forms.IntegerField(widget=forms.HiddenInput)
