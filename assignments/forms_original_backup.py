from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Assignment, AssignmentSubmission, Tag
from apps.private_teaching.models import PrivateLessonAssignment
from django.contrib.auth.models import User


class AssignmentForm(forms.ModelForm):
    """Form for creating/editing assignments"""

    # Additional field for creating new tags inline
    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Scales, Rhythm, Theory'
        }),
        label='New Tags',
        help_text='Enter tag names separated by commas to create and add them to this assignment'
    )

    class Meta:
        model = Assignment
        fields = [
            'title',
            'instructions',
            'grading_scale',
            'difficulty',
            'tags',
            'is_public',
            'has_notation_component',
            'has_written_component',
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
                'placeholder': 'Provide assignment instructions and question(s) here...'
            }),
            'grading_scale': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'select select-bordered w-full',
                'size': '5'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'has_notation_component': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'has_written_component': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'reference_notation': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full font-mono text-sm',
                'rows': 4,
                'placeholder': 'VexFlow notation data (optional - can be added later)'
            }),
        }
        labels = {
            'title': 'Assignment Title',
            'instructions': 'Instructions and Question(s)',
            'grading_scale': 'Grading Scale',
            'difficulty': 'Difficulty Level',
            'tags': 'Existing Tags',
            'is_public': 'Make Public',
            'has_notation_component': 'Include Music Notation Component',
            'has_written_component': 'Include Written Response Component',
            'reference_notation': 'Reference Notation Data (optional)',
        }
        help_texts = {
            'grading_scale': 'Choose how this assignment will be graded',
            'instructions': 'Provide instructions and any questions for the student',
            'difficulty': 'Select the difficulty level for this assignment',
            'tags': 'Select existing tags (Ctrl+Click to select multiple)',
            'is_public': 'Allow other teachers to browse and use this assignment',
            'has_notation_component': 'Student will use the notation editor to complete this assignment',
            'has_written_component': 'Student will provide a written response with text formatting',
            'reference_notation': 'JSON data from notation editor - leave blank to add later',
        }

    def save(self, commit=True):
        instance = super().save(commit=commit)

        # Handle new tags if provided
        new_tags_str = self.cleaned_data.get('new_tags', '')
        if new_tags_str:
            # Parse comma-separated tags
            tag_names = [name.strip() for name in new_tags_str.split(',') if name.strip()]

            for tag_name in tag_names:
                # Get or create tag (case-insensitive check)
                tag, created = Tag.objects.get_or_create(
                    name__iexact=tag_name,
                    defaults={'name': tag_name}
                )
                # If tag exists but with different case, use the existing one
                if not created:
                    tag = Tag.objects.filter(name__iexact=tag_name).first()

                # Add tag to assignment
                instance.tags.add(tag)

        return instance


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

    class Meta:
        model = AssignmentSubmission
        fields = ['notation_data', 'written_response']
        widgets = {
            'notation_data': forms.HiddenInput(),
            'written_response': CKEditor5Widget(config_name='default'),
        }
