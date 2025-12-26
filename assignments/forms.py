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
            'grading_scale',
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
            'grading_scale': forms.Select(attrs={
                'class': 'select select-bordered w-full'
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
            'grading_scale': 'Grading Scale',
            'has_notation_component': 'Include Music Notation Component',
            'has_written_component': 'Include Written Questions',
            'written_questions': 'Written Questions (JSON format)',
            'reference_notation': 'Reference Notation Data (optional)',
        }
        help_texts = {
            'grading_scale': 'Choose how this assignment will be graded',
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

            # Get all accepted lessons for this teacher with child profile info
            lessons = Lesson.objects.filter(
                teacher=teacher,
                approved_status='Accepted',
                is_deleted=False
            ).select_related('student', 'lesson_request', 'lesson_request__child_profile').distinct()

            # Build a dict of student choices with proper display names
            student_choices = {}
            for lesson in lessons:
                student_id = lesson.student.id
                if student_id not in student_choices:
                    # Check if this is a child student
                    if lesson.lesson_request and lesson.lesson_request.child_profile:
                        child = lesson.lesson_request.child_profile
                        guardian = lesson.student
                        # Show child name with guardian in parentheses
                        display_name = f"{child.full_name} (Guardian: {guardian.get_full_name() or guardian.username})"
                    else:
                        # Show regular student name
                        display_name = lesson.student.get_full_name() or lesson.student.username

                    student_choices[student_id] = display_name

            # Sort by display name
            sorted_choices = sorted(student_choices.items(), key=lambda x: x[1])

            # Set queryset and override label_from_instance
            student_ids = [student_id for student_id, _ in sorted_choices]
            self.fields['student'].queryset = User.objects.filter(id__in=student_ids)

            # Store display names for use in label_from_instance
            self._student_display_names = student_choices

            # Override the label display method
            original_label = self.fields['student'].label_from_instance
            def custom_label(obj):
                return self._student_display_names.get(obj.id, obj.get_full_name() or obj.username)
            self.fields['student'].label_from_instance = custom_label

            # Filter lessons to only this teacher's accepted lessons
            self.fields['lesson'].queryset = Lesson.objects.filter(
                teacher=teacher,
                approved_status='Accepted',
                is_deleted=False
            ).select_related('lesson_request', 'lesson_request__child_profile', 'student').order_by('-lesson_date')

            # Override the lesson label display to show child name if applicable
            def lesson_label(obj):
                # Show child name if this is a child lesson
                if obj.lesson_request and obj.lesson_request.child_profile:
                    student_name = obj.lesson_request.child_profile.full_name
                else:
                    student_name = obj.student.get_full_name() or obj.student.username

                return f"{student_name} - {obj.lesson_date.strftime('%b %d, %Y')} - {obj.subject.subject}"
            self.fields['lesson'].label_from_instance = lesson_label

            # Make student required, lesson optional
            self.fields['lesson'].required = False


class GradeSubmissionForm(forms.ModelForm):
    """Form for grading a student's submission"""

    class Meta:
        model = AssignmentSubmission
        fields = ['grade', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 6,
                'placeholder': 'Provide feedback to the student...'
            }),
        }
        labels = {
            'feedback': 'Feedback for Student',
        }
        help_texts = {
            'feedback': 'Constructive feedback on their work',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the assignment to determine grading scale
        if self.instance and self.instance.assignment:
            assignment = self.instance.assignment
            grading_scale = assignment.grading_scale

            if grading_scale == 'pass_fail':
                # For pass/fail, use a dropdown
                self.fields['grade'] = forms.ChoiceField(
                    choices=[
                        ('', 'Select grade'),
                        (1, 'Pass'),
                        (0, 'Fail'),
                    ],
                    widget=forms.Select(attrs={
                        'class': 'select select-bordered w-full'
                    }),
                    label='Grade',
                    help_text='Select Pass or Fail'
                )
            elif grading_scale == '10':
                # For 0-10 scale
                self.fields['grade'].widget = forms.NumberInput(attrs={
                    'class': 'input input-bordered w-full',
                    'min': 0,
                    'max': 10,
                    'step': 0.5,
                    'placeholder': 'Enter grade (0-10)'
                })
                self.fields['grade'].label = 'Grade (out of 10)'
                self.fields['grade'].help_text = 'Enter a grade between 0 and 10'
            else:  # 100 scale (default)
                self.fields['grade'].widget = forms.NumberInput(attrs={
                    'class': 'input input-bordered w-full',
                    'min': 0,
                    'max': 100,
                    'step': 0.5,
                    'placeholder': 'Enter grade (0-100)'
                })
                self.fields['grade'].label = 'Grade (out of 100)'
                self.fields['grade'].help_text = 'Enter a grade between 0 and 100'


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
