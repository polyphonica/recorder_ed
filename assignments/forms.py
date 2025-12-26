from django import forms
from .models import Assignment, AssignmentSubmission
from apps.private_teaching.models import PrivateLessonAssignment
from django.contrib.auth.models import User


class AssignmentForm(forms.ModelForm):
    """Form for creating/editing assignments"""

    class Meta:
        model = Assignment
        fields = [
            'title',
            'instructions',
            'has_notation_component',
            'has_written_component',
            'written_questions',
            'reference_notation',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Write a C Major Scale'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 5,
                'placeholder': 'Detailed instructions for the student...'
            }),
            'has_notation_component': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'has_written_component': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'written_questions': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Enter questions as JSON: [{"question": "What is a perfect 5th?", "type": "short"}]'
            }),
            'reference_notation': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full font-mono text-sm',
                'rows': 4,
                'placeholder': 'VexFlow notation data (optional - can be added later)'
            }),
        }
        labels = {
            'title': 'Assignment Title',
            'instructions': 'Instructions for Student',
            'has_notation_component': 'Include Music Notation Component',
            'has_written_component': 'Include Written Questions',
            'written_questions': 'Written Questions (JSON format)',
            'reference_notation': 'Reference Notation Data (optional)',
        }
        help_texts = {
            'has_notation_component': 'Student will use notation editor to complete',
            'has_written_component': 'Student will answer written questions',
            'written_questions': 'Leave blank if no written component',
            'reference_notation': 'JSON data from notation editor - leave blank to add later',
        }


class AssignToStudentForm(forms.ModelForm):
    """Form for assigning an assignment to a student"""

    class Meta:
        model = PrivateLessonAssignment
        fields = ['student', 'lesson', 'due_date']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'lesson': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
        }
        labels = {
            'student': 'Select Student',
            'lesson': 'Link to Lesson (optional)',
            'due_date': 'Due Date (optional)',
        }
        help_texts = {
            'student': 'Choose which student to assign this to',
            'lesson': 'Optionally link to a specific lesson',
            'due_date': 'When should this be completed?',
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        if teacher:
            # Filter students to only those who are the teacher's students
            from lessons.models import Lesson
            student_ids = Lesson.objects.filter(
                teacher=teacher,
                approved_status='Accepted',
                is_deleted=False
            ).values_list('student_id', flat=True).distinct()

            self.fields['student'].queryset = User.objects.filter(
                id__in=student_ids
            ).order_by('first_name', 'last_name', 'username')

            # Filter lessons to only this teacher's accepted lessons
            self.fields['lesson'].queryset = Lesson.objects.filter(
                teacher=teacher,
                approved_status='Accepted',
                is_deleted=False
            ).order_by('-lesson_date')

            # Make student required, lesson optional
            self.fields['lesson'].required = False


class GradeSubmissionForm(forms.ModelForm):
    """Form for grading a student's submission"""

    class Meta:
        model = AssignmentSubmission
        fields = ['grade', 'feedback']
        widgets = {
            'grade': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 0,
                'max': 100,
                'step': 0.5,
                'placeholder': 'Enter grade (0-100)'
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 6,
                'placeholder': 'Provide feedback to the student...'
            }),
        }
        labels = {
            'grade': 'Grade (out of 100)',
            'feedback': 'Feedback for Student',
        }
        help_texts = {
            'grade': 'Enter a grade between 0 and 100',
            'feedback': 'Constructive feedback on their work',
        }


class SubmissionForm(forms.ModelForm):
    """Form for students to submit their work"""

    written_answer_0 = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3
        })
    )
    written_answer_1 = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3
        })
    )
    written_answer_2 = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3
        })
    )
    written_answer_3 = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3
        })
    )
    written_answer_4 = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3
        })
    )

    class Meta:
        model = AssignmentSubmission
        fields = ['notation_data']
        widgets = {
            'notation_data': forms.HiddenInput(),
        }

    def __init__(self, *args, num_questions=0, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show the number of answer fields needed
        for i in range(5):
            if i >= num_questions:
                del self.fields[f'written_answer_{i}']
