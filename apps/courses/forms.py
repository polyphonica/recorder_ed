"""
Forms for courses app.
"""

from django import forms
from django.db import models
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import Course, Topic, Lesson, Quiz, QuizQuestion, QuizAnswer, CourseMessage


class CourseAdminForm(forms.ModelForm):
    """
    Custom form for Course admin that filters instructor dropdown
    to only show users with is_teacher flag.
    """

    class Meta:
        model = Course
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter instructor field to only show teachers
        # Check both is_teacher (accounts.UserProfile) and is_instructor (workshops.UserProfile)
        teacher_users = User.objects.filter(
            models.Q(profile__is_teacher=True) |
            models.Q(instructor_profile__is_instructor=True)
        ).distinct()

        self.fields['instructor'].queryset = teacher_users
        self.fields['instructor'].help_text = 'Only users with teacher/instructor status are shown'


class QuizQuestionForm(forms.ModelForm):
    """
    Form for creating/editing quiz questions with CKEditor.
    """
    class Meta:
        model = QuizQuestion
        fields = ['text', 'points', 'order']
        widgets = {
            'points': forms.NumberInput(attrs={'class': 'input input-bordered w-32', 'min': 1}),
            'order': forms.NumberInput(attrs={'class': 'input input-bordered w-32', 'min': 1}),
        }


class QuizAnswerForm(forms.ModelForm):
    """
    Form for quiz answers (used in formset).
    """
    class Meta:
        model = QuizAnswer
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'input input-bordered flex-1', 'placeholder': 'Answer text'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'radio radio-primary'}),
        }


# Formset for managing multiple answers for a question
QuizAnswerFormSet = inlineformset_factory(
    QuizQuestion,
    QuizAnswer,
    form=QuizAnswerForm,
    extra=4,  # Start with 4 answer fields
    min_num=2,  # Minimum 2 answers required
    validate_min=True,
    can_delete=True
)


class CourseMessageForm(forms.ModelForm):
    """
    Form for composing a new message to the instructor.
    Used by students from lesson view.
    """
    class Meta:
        model = CourseMessage
        fields = ['category', 'body']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full',
            }),
            'body': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 6,
                'placeholder': 'Describe your question or issue in detail...'
            }),
        }
        labels = {
            'category': 'What is this about?',
            'body': 'Your Message',
        }


class MessageReplyForm(forms.Form):
    """
    Simple form for replying to messages.
    """
    body = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 4,
            'placeholder': 'Type your reply...'
        }),
        label='Your Reply'
    )
