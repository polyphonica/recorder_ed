"""
Forms for Private Lesson Quiz System
"""
from django import forms
from django.contrib.auth import get_user_model
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    PrivateLessonQuiz,
    PrivateLessonQuizQuestion,
    PrivateLessonQuizAnswer,
    PrivateLessonQuizAssignment,
)
from apps.lesson_templates.models import Tag

User = get_user_model()


class PrivateLessonQuizForm(forms.ModelForm):
    """
    Form for creating/editing quizzes.
    Includes inline tag creation support (like LessonContentTemplateForm).
    """

    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Add new tags (comma-separated)',
            'class': 'input input-bordered w-full'
        }),
        help_text='Enter new tags separated by commas'
    )

    class Meta:
        model = PrivateLessonQuiz
        fields = [
            'title',
            'description',
            'instructions',
            'pass_percentage',
            'time_limit_minutes',
            'randomize_questions',
            'show_correct_answers',
            'allow_retakes',
            'max_attempts',
            'subject',
            'syllabus',
            'grade_level',
            'tags',
            'is_public',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Grade 1 Theory Mock Exam'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Brief description of what this quiz covers...'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Instructions for students taking the quiz...'
            }),
            'pass_percentage': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 0,
                'max': 100,
                'value': 70
            }),
            'time_limit_minutes': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 1,
                'placeholder': 'Leave blank for no time limit'
            }),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 1,
                'placeholder': 'Leave blank for unlimited attempts'
            }),
            'subject': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'syllabus': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'grade_level': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., 1, Beginner, Intermediate'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'select select-bordered w-full',
                'size': 5
            }),
            'randomize_questions': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'show_correct_answers': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'allow_retakes': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        help_texts = {
            'pass_percentage': 'Minimum percentage required to pass (0-100)',
            'time_limit_minutes': 'Optional time limit in minutes',
            'randomize_questions': 'Randomize question order for each attempt',
            'show_correct_answers': 'Show correct answers after submission',
            'allow_retakes': 'Allow students to retake the quiz',
            'max_attempts': 'Maximum number of attempts (leave blank for unlimited)',
            'is_public': 'Make this quiz available to other teachers',
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter subjects to teacher's subjects only
        if teacher:
            self.fields['subject'].queryset = teacher.subjects.filter(is_active=True)

        # Make subject optional
        self.fields['subject'].required = False
        self.fields['subject'].empty_label = "-- Select Subject (Optional) --"

        # Make syllabus optional
        self.fields['syllabus'].required = False

    def _save_new_tags(self):
        """Create new tags from comma-separated input"""
        new_tags_input = self.cleaned_data.get('new_tags', '')
        if not new_tags_input:
            return []

        tag_names = [name.strip() for name in new_tags_input.split(',') if name.strip()]
        tags = []
        for name in tag_names:
            tag, created = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags

    def clean_pass_percentage(self):
        """Validate pass percentage is between 0 and 100"""
        pass_percentage = self.cleaned_data.get('pass_percentage')
        if pass_percentage is not None:
            if pass_percentage < 0 or pass_percentage > 100:
                raise forms.ValidationError('Pass percentage must be between 0 and 100.')
        return pass_percentage

    def clean_max_attempts(self):
        """Validate max_attempts is positive if provided"""
        max_attempts = self.cleaned_data.get('max_attempts')
        if max_attempts is not None and max_attempts < 1:
            raise forms.ValidationError('Maximum attempts must be at least 1.')
        return max_attempts

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        # If retakes not allowed, max_attempts should be 1 or None
        allow_retakes = cleaned_data.get('allow_retakes')
        max_attempts = cleaned_data.get('max_attempts')

        if not allow_retakes and max_attempts and max_attempts > 1:
            cleaned_data['max_attempts'] = 1

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # Save M2M relationships
            self.save_m2m()
            # Add new tags
            new_tags = self._save_new_tags()
            if new_tags:
                instance.tags.add(*new_tags)

        return instance


class PrivateLessonQuizQuestionForm(forms.ModelForm):
    """
    Form for quiz questions with CKEditor5 support.
    """

    class Meta:
        model = PrivateLessonQuizQuestion
        fields = ['text', 'order', 'points', 'explanation']
        widgets = {
            'text': CKEditor5Widget(config_name='default'),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 0,
                'placeholder': 'Question order (0 = first)'
            }),
            'points': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 1,
                'value': 1
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Optional explanation shown after answering...'
            }),
        }
        help_texts = {
            'text': 'Question text (supports images, formatting, music notation)',
            'order': 'Display order (lower numbers appear first)',
            'points': 'Points awarded for correct answer',
            'explanation': 'Optional explanation shown after student answers',
        }

    def clean_points(self):
        """Validate points is positive"""
        points = self.cleaned_data.get('points')
        if points is not None and points < 1:
            raise forms.ValidationError('Points must be at least 1.')
        return points


class PrivateLessonQuizAnswerForm(forms.ModelForm):
    """
    Form for quiz answers.
    Used in formset for managing multiple answers per question.
    """

    class Meta:
        model = PrivateLessonQuizAnswer
        fields = ['text', 'is_correct', 'order']
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Answer text...'
            }),
            'is_correct': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-20',
                'min': 0
            }),
        }
        help_texts = {
            'text': 'Answer text',
            'is_correct': 'Mark as correct answer',
            'order': 'Display order',
        }


# Formset for answers (inline with question)
PrivateLessonQuizAnswerFormSet = forms.inlineformset_factory(
    PrivateLessonQuizQuestion,
    PrivateLessonQuizAnswer,
    form=PrivateLessonQuizAnswerForm,
    extra=4,  # Show 4 empty forms
    min_num=2,  # At least 2 answers required
    max_num=10,  # Maximum 10 answers
    validate_min=True,
    can_delete=True
)


class PrivateLessonQuizAssignmentForm(forms.ModelForm):
    """
    Form for assigning quiz to student(s).
    Teacher selects quiz, student, optional child profile, and due date.
    """

    class Meta:
        model = PrivateLessonQuizAssignment
        fields = ['quiz', 'student', 'child_profile', 'lesson', 'due_date', 'notes']
        widgets = {
            'quiz': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'student': forms.Select(attrs={
                'class': 'select select-bordered w-full',
                'id': 'id_student'
            }),
            'child_profile': forms.Select(attrs={
                'class': 'select select-bordered w-full',
                'id': 'id_child_profile'
            }),
            'lesson': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Optional notes for the student about this quiz...'
            }),
        }
        help_texts = {
            'quiz': 'Select which quiz to assign',
            'student': 'Select the student (or guardian if child)',
            'child_profile': 'If student is a guardian, select which child',
            'lesson': 'Optionally link to a specific lesson',
            'due_date': 'Optional deadline for completion',
            'notes': 'Additional information or context for the student',
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        if teacher:
            # Filter quizzes to teacher's own quizzes
            self.fields['quiz'].queryset = PrivateLessonQuiz.objects.filter(
                created_by=teacher
            ).order_by('-created_at')

            # Filter students to teacher's accepted students
            from .models import TeacherStudentApplication
            accepted_apps = TeacherStudentApplication.objects.filter(
                teacher=teacher,
                status='accepted'
            ).values_list('applicant_id', flat=True)

            self.fields['student'].queryset = User.objects.filter(
                id__in=accepted_apps
            ).order_by('first_name', 'last_name', 'username')

            # Filter lessons to teacher's lessons
            from lessons.models import Lesson
            self.fields['lesson'].queryset = Lesson.objects.filter(
                teacher=teacher,
                approved_status='accepted'
            ).order_by('-lesson_date', '-lesson_time')

        # Make child_profile and lesson optional
        self.fields['child_profile'].required = False
        self.fields['child_profile'].empty_label = "-- Adult Student (No Child) --"

        self.fields['lesson'].required = False
        self.fields['lesson'].empty_label = "-- No Specific Lesson --"

        self.fields['due_date'].required = False

        # Initially, child_profile should show all children (filtered by JS)
        self.fields['child_profile'].queryset = self.fields['child_profile'].queryset.none()

    def clean(self):
        """Validate assignment doesn't already exist"""
        cleaned_data = super().clean()

        quiz = cleaned_data.get('quiz')
        student = cleaned_data.get('student')
        child_profile = cleaned_data.get('child_profile')

        if quiz and student:
            # Check for duplicate assignment
            existing = PrivateLessonQuizAssignment.objects.filter(
                quiz=quiz,
                student=student,
                child_profile=child_profile
            )

            # Exclude current instance if editing
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                student_name = child_profile.full_name if child_profile else student.get_full_name()
                raise forms.ValidationError(
                    f'This quiz is already assigned to {student_name}.'
                )

        return cleaned_data
