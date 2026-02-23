"""
Forms for the unified Quiz system (private lesson quizzes).
"""
from django import forms
from django.contrib.auth import get_user_model
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Quiz, QuizQuestion, QuizAnswer, QuizAssignment
from apps.lesson_templates.models import Tag
from apps.accounts.models import ChildProfile

User = get_user_model()


class QuizForm(forms.ModelForm):
    """Form for creating/editing private lesson quizzes."""

    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Add new tags (comma-separated)',
            'class': 'input input-bordered w-full'
        }),
        help_text='Enter new tags separated by commas'
    )

    class Meta:
        model = Quiz
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
            'pagination_mode',
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
            'pagination_mode': forms.RadioSelect(attrs={
                'class': 'radio radio-primary'
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
            'pagination_mode': 'Choose how questions are displayed to students',
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        if teacher:
            self.fields['subject'].queryset = teacher.subjects.filter(is_active=True)

        self.fields['subject'].required = False
        self.fields['subject'].empty_label = "-- Select Subject (Optional) --"
        self.fields['syllabus'].required = False

    def _save_new_tags(self):
        new_tags_input = self.cleaned_data.get('new_tags', '')
        if not new_tags_input:
            return []
        tag_names = [name.strip() for name in new_tags_input.split(',') if name.strip()]
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags

    def clean_pass_percentage(self):
        pass_percentage = self.cleaned_data.get('pass_percentage')
        if pass_percentage is not None:
            if pass_percentage < 0 or pass_percentage > 100:
                raise forms.ValidationError('Pass percentage must be between 0 and 100.')
        return pass_percentage

    def clean_max_attempts(self):
        max_attempts = self.cleaned_data.get('max_attempts')
        if max_attempts is not None and max_attempts < 1:
            raise forms.ValidationError('Maximum attempts must be at least 1.')
        return max_attempts

    def clean(self):
        cleaned_data = super().clean()
        allow_retakes = cleaned_data.get('allow_retakes')
        max_attempts = cleaned_data.get('max_attempts')
        if not allow_retakes and max_attempts and max_attempts > 1:
            cleaned_data['max_attempts'] = 1
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            new_tags = self._save_new_tags()
            if new_tags:
                instance.tags.add(*new_tags)
        return instance


# Keep old name as alias for backwards compat within this package
PrivateLessonQuizForm = QuizForm


class QuizQuestionForm(forms.ModelForm):
    """Form for quiz questions with CKEditor5 support."""

    class Meta:
        model = QuizQuestion
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

    def clean_points(self):
        points = self.cleaned_data.get('points')
        if points is not None and points < 1:
            raise forms.ValidationError('Points must be at least 1.')
        return points


PrivateLessonQuizQuestionForm = QuizQuestionForm


class QuizAnswerForm(forms.ModelForm):
    """Form for quiz answers with CKEditor5 support."""

    class Meta:
        model = QuizAnswer
        fields = ['text', 'is_correct', 'order']
        widgets = {
            'text': CKEditor5Widget(config_name='default'),
            'is_correct': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-20',
                'min': 0
            }),
        }


PrivateLessonQuizAnswerForm = QuizAnswerForm


# Formset for answers (inline with question)
QuizAnswerFormSet = forms.inlineformset_factory(
    QuizQuestion,
    QuizAnswer,
    form=QuizAnswerForm,
    extra=3,
    max_num=10,
    can_delete=True
)

PrivateLessonQuizAnswerFormSet = QuizAnswerFormSet


class QuizAssignmentForm(forms.ModelForm):
    """Form for assigning quiz to a private lesson student."""

    student_selection = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full',
            'id': 'id_student_selection'
        }),
        help_text='Select the student to assign this quiz to'
    )

    class Meta:
        model = QuizAssignment
        fields = ['quiz', 'lesson', 'due_date', 'notes']
        widgets = {
            'quiz': forms.Select(attrs={
                'class': 'select select-bordered w-full'
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

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        from datetime import date

        self.fields['student_selection'].choices = [('', '-- Select Student --')]
        self.fields['quiz'].required = False

        if teacher:
            from apps.private_teaching.models import TeacherStudentApplication
            from lessons.models import Lesson

            self.fields['quiz'].queryset = Quiz.objects.filter(
                created_by=teacher
            ).order_by('-created_at')

            accepted_apps = TeacherStudentApplication.objects.filter(
                teacher=teacher,
                status='accepted'
            ).select_related('applicant__profile')

            student_choices = [('', '-- Select Student --')]
            students_without_lessons = []

            for app in accepted_apps:
                user = app.applicant
                try:
                    if hasattr(user, 'profile') and user.profile.is_student:
                        has_completed_lesson = Lesson.objects.filter(
                            teacher=teacher,
                            student=user,
                            approved_status='Accepted',
                            lesson_date__lt=date.today()
                        ).exists()
                        full_name = user.profile.full_name or user.username
                        student_key = f'user_{user.id}'
                        if not has_completed_lesson:
                            full_name += ' ⚠️ No lessons yet'
                            students_without_lessons.append(student_key)
                        student_choices.append((student_key, full_name))
                    elif hasattr(user, 'profile') and user.profile.is_guardian:
                        children = user.children.all()
                        for child in children:
                            has_completed_lesson = Lesson.objects.filter(
                                teacher=teacher,
                                student=user,
                                approved_status='Accepted',
                                lesson_date__lt=date.today()
                            ).exists()
                            child_name = child.full_name
                            student_key = f'child_{child.id}'
                            if not has_completed_lesson:
                                child_name += ' ⚠️ No lessons yet'
                                students_without_lessons.append(student_key)
                            student_choices.append((student_key, child_name))
                except Exception:
                    continue

            self.fields['student_selection'].choices = student_choices
            self.students_without_lessons = students_without_lessons

            self.fields['lesson'].queryset = Lesson.objects.filter(
                teacher=teacher,
                approved_status='Accepted'
            ).order_by('-lesson_date', '-lesson_time')

        self.fields['lesson'].required = False
        self.fields['lesson'].empty_label = "-- No Specific Lesson --"
        self.fields['due_date'].required = False

        if self.instance and self.instance.pk:
            if self.instance.child_profile_id:
                self.fields['student_selection'].initial = f'child_{self.instance.child_profile_id}'
            elif self.instance.student_id:
                self.fields['student_selection'].initial = f'user_{self.instance.student_id}'

    def clean(self):
        cleaned_data = super().clean()
        student_selection = cleaned_data.get('student_selection')
        quiz = cleaned_data.get('quiz')

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
            raise forms.ValidationError('Invalid student selection')

        cleaned_data['_parsed_student'] = student
        cleaned_data['_parsed_child_profile'] = child_profile

        if quiz and student:
            existing = QuizAssignment.objects.filter(
                quiz=quiz,
                student=student,
                child_profile=child_profile
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                student_name = child_profile.full_name if child_profile else student.get_full_name()
                raise forms.ValidationError(
                    f'This quiz is already assigned to {student_name}.'
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'cleaned_data'):
            parsed_student = self.cleaned_data.get('_parsed_student')
            parsed_child = self.cleaned_data.get('_parsed_child_profile')
            if parsed_student:
                instance.student = parsed_student
                instance.child_profile = parsed_child
        if commit:
            instance.save()
        return instance


PrivateLessonQuizAssignmentForm = QuizAssignmentForm
