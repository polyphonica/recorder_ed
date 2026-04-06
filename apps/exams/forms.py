from django import forms
from django.forms import inlineformset_factory

from .models import ExamBoard, ExamRegistration, ExamPiece


class ExamRegistrationForm(forms.ModelForm):
    """Form for teachers to register students for exams"""

    student = forms.ChoiceField(
        label="Student/Guardian:",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
        help_text="Select the student or guardian"
    )
    child_profile = forms.ChoiceField(
        required=False,
        label="Student (if child):",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
        help_text="Select which child this exam is for (if applicable)"
    )

    class Meta:
        model = ExamRegistration
        fields = [
            'subject', 'exam_board',
            'grade_type', 'grade_level', 'exam_date', 'submission_deadline',
            'registration_number', 'venue', 'scales', 'arpeggios',
            'sight_reading', 'aural_tests', 'payment_amount', 'teacher_notes'
        ]
        labels = {
            'payment_amount': 'Registration fee',
        }
        widgets = {
            'subject': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'exam_board': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'grade_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'grade_level': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'max': '8'
            }),
            'exam_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'submission_deadline': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Optional - from exam board'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Video submission, London Centre'
            }),
            'scales': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'e.g., C major, A minor melodic, chromatic'
            }),
            'arpeggios': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'e.g., C major, A minor'
            }),
            'sight_reading': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Sight reading requirements'
            }),
            'aural_tests': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Aural test requirements'
            }),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'teacher_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Private notes about this exam registration'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        self.selected_student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        self.fields['payment_amount'].required = False

        if self.teacher:
            from apps.private_teaching.models import TeacherStudentApplication, Subject
            accepted_applications = TeacherStudentApplication.objects.filter(
                teacher=self.teacher,
                status='accepted'
            ).select_related('applicant', 'child_profile')

            student_choices = []
            child_choices = []

            for app in accepted_applications:
                if app.child_profile:
                    if (str(app.applicant.id), f"{app.applicant.get_full_name()} (Guardian)") not in student_choices:
                        student_choices.append((str(app.applicant.id), f"{app.applicant.get_full_name()} (Guardian)"))
                    child_choices.append((str(app.child_profile.id), app.child_profile.full_name))
                else:
                    student_choices.append((str(app.applicant.id), app.applicant.get_full_name()))

            self.fields['student'].choices = [('', 'Select student')] + student_choices
            self.fields['child_profile'].choices = [('', 'N/A - Adult student')] + child_choices

            if self.selected_student:
                self.fields['student'].initial = str(self.selected_student)

            self.fields['subject'].queryset = Subject.objects.filter(
                teacher=self.teacher,
                is_active=True
            )
            self.fields['exam_board'].queryset = ExamBoard.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        grade_type = cleaned_data.get('grade_type')
        grade_level = cleaned_data.get('grade_level')

        if grade_type and grade_level:
            if grade_type == ExamRegistration.THEORY:
                if grade_level < 1 or grade_level > 6:
                    self.add_error('grade_level', 'Theory grades must be between 1 and 6')
            else:
                if grade_level < 1 or grade_level > 8:
                    self.add_error('grade_level', 'Practical and Performance grades must be between 1 and 8')

        return cleaned_data

    def save(self, commit=True):
        exam = super().save(commit=False)
        if self.teacher:
            exam.teacher = self.teacher

        student_id = self.cleaned_data.get('student')
        if student_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            exam.student = User.objects.get(id=student_id)

        child_profile_id = self.cleaned_data.get('child_profile')
        if child_profile_id:
            from apps.accounts.models import ChildProfile
            exam.child_profile = ChildProfile.objects.get(id=child_profile_id)
        else:
            exam.child_profile = None

        if not exam.payment_amount:
            exam.payment_amount = 0
        if exam.payment_amount > 0:
            exam.payment_status = 'pending'
        else:
            exam.payment_status = 'not_required'

        if commit:
            exam.save()
        return exam


class ExamPieceForm(forms.ModelForm):
    """Form for individual exam pieces"""

    class Meta:
        model = ExamPiece
        fields = ['piece_number', 'title', 'composer', 'syllabus_list', 'teacher_notes']
        widgets = {
            'piece_number': forms.NumberInput(attrs={
                'class': 'input input-bordered w-20',
                'min': '1',
                'placeholder': '#'
            }),
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Piece title'
            }),
            'composer': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Composer name'
            }),
            'syllabus_list': forms.TextInput(attrs={
                'class': 'input input-bordered w-32',
                'placeholder': 'A, B, C...'
            }),
            'teacher_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Notes about practice progress'
            }),
        }


ExamPieceFormSet = inlineformset_factory(
    ExamRegistration,
    ExamPiece,
    form=ExamPieceForm,
    extra=3,
    min_num=0,
    can_delete=True
)


class ExamResultsForm(forms.ModelForm):
    """Form for teachers to enter exam results"""

    class Meta:
        model = ExamRegistration
        fields = [
            'status', 'mark_achieved', 'grade_achieved',
            'examiner_comments', 'certificate_received_date'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'mark_achieved': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'max': '100',
                'placeholder': 'e.g., 85'
            }),
            'grade_achieved': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'examiner_comments': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Enter examiner feedback and comments'
            }),
            'certificate_received_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].initial = ExamRegistration.RESULTS_RECEIVED
