from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import LessonRequest, Subject, LessonRequestMessage, ExamRegistration, ExamPiece, ExamBoard, PracticeEntry
from lessons.models import Lesson


class StudentSignupForm(UserCreationForm):
    """Registration form with conditional guardian fields for under-18 students"""
    
    # Personal information
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'})
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'input input-bordered w-full'})
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'})
    )
    
    # Age verification
    under_eighteen = forms.BooleanField(
        required=False,
        label="I am under 18 years old",
        widget=forms.CheckboxInput(attrs={'class': 'checkbox', 'id': 'under_eighteen'})
    )
    
    # Guardian information (conditionally required)
    guardian_first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full guardian-field',
            'style': 'display: none;'
        })
    )
    guardian_last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full guardian-field',
            'style': 'display: none;'
        })
    )
    guardian_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full guardian-field',
            'style': 'display: none;'
        })
    )
    guardian_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full guardian-field',
            'style': 'display: none;'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'input input-bordered w-full'})
        self.fields['password2'].widget.attrs.update({'class': 'input input-bordered w-full'})

    def clean(self):
        cleaned_data = super().clean()
        under_eighteen = cleaned_data.get('under_eighteen')
        
        if under_eighteen:
            # Validate guardian fields are provided when under 18
            guardian_fields = ['guardian_first_name', 'guardian_last_name', 'guardian_email', 'guardian_phone']
            for field in guardian_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for students under 18.')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Update profile with additional information
            profile = user.profile
            profile.first_name = self.cleaned_data['first_name']
            profile.last_name = self.cleaned_data['last_name']
            profile.phone = self.cleaned_data['phone']
            profile.under_eighteen = self.cleaned_data['under_eighteen']
            profile.is_student = True  # Mark as student
            
            if self.cleaned_data['under_eighteen']:
                profile.guardian_first_name = self.cleaned_data['guardian_first_name']
                profile.guardian_last_name = self.cleaned_data['guardian_last_name']
                profile.guardian_email = self.cleaned_data['guardian_email']
                profile.guardian_phone = self.cleaned_data['guardian_phone']
            
            profile.save()
        
        return user


class LessonRequestForm(forms.ModelForm):
    """Form for the main lesson request (container only - messages handled separately)"""

    # Child selection for guardians
    child_profile = forms.ChoiceField(
        required=False,
        label="Request lessons for:",
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary'
        }),
        help_text="Select which child these lessons are for"
    )

    class Meta:
        model = LessonRequest
        fields = []  # No fields - this is just a container for the formset

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Setup child selection field for guardians
        if self.user and self.user.is_authenticated and self.user.profile.is_guardian:
            from apps.accounts.models import ChildProfile
            children = self.user.children.all()

            if children:
                choices = [(str(child.id), f"{child.full_name} (Age: {child.age})") for child in children]
                self.fields['child_profile'].choices = choices
                self.fields['child_profile'].required = True
            else:
                # Remove field if no children
                del self.fields['child_profile']
        else:
            # Remove field for non-guardians
            del self.fields['child_profile']


class StudentLessonForm(forms.ModelForm):
    """Form for students to create lesson requests"""

    class Meta:
        model = Lesson
        fields = ['subject', 'location', 'lesson_date', 'lesson_time', 'duration_in_minutes']
        widgets = {
            'subject': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'location': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'lesson_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'lesson_time': forms.TimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'time'
            }),
            'duration_in_minutes': forms.Select(attrs={'class': 'select select-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        # Extract teacher parameter if provided (for filtering subjects)
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

        # Filter subjects by teacher if provided
        if teacher:
            from .models import Subject
            self.fields['subject'].queryset = Subject.objects.filter(
                teacher=teacher,
                is_active=True
            )

        self.fields['subject'].required = True
        self.fields['subject'].empty_label = "Select subject"
        self.fields['location'].required = True
        self.fields['lesson_date'].required = True
        self.fields['lesson_time'].required = True
        self.fields['duration_in_minutes'].required = True


# Create the formset for students to create multiple lessons
StudentLessonFormSet = inlineformset_factory(
    LessonRequest,
    Lesson,
    form=StudentLessonForm,
    extra=1,  # Show 1 empty form by default
    min_num=1,  # Require at least 1 lesson
    validate_min=True,
    can_delete=True
)


class TeacherLessonForm(forms.ModelForm):
    """Form for teachers to edit lessons with approval and pricing"""

    # Display-only field for base price
    base_price = forms.DecimalField(
        required=False,
        disabled=True,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full bg-base-200',
            'readonly': True
        }),
        label="Base Price (60min)"
    )

    class Meta:
        model = Lesson
        fields = [
            'subject', 'duration_in_minutes', 'location',
            'lesson_date', 'lesson_time', 'approved_status', 'payment_status'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'select select-bordered w-full bg-base-200'}),
            'duration_in_minutes': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'location': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'lesson_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'lesson_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
            'approved_status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'payment_status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make subject field read-only (disabled in form, but value preserved)
        self.fields['subject'].disabled = True
        self.fields['subject'].required = False

        # Customize subject field to show only subject name, not with price
        self.fields['subject'].label_from_instance = lambda obj: obj.subject

        # Populate base_price field from subject
        if self.instance and self.instance.subject:
            self.fields['base_price'].initial = self.instance.subject.base_price_60min


# Create the teacher formset for editing lesson requests
TeacherLessonFormSet = inlineformset_factory(
    LessonRequest,
    Lesson,
    form=TeacherLessonForm,
    extra=0,  # Don't show empty forms for teachers
    can_delete=True
)


class ProfileCompleteForm(forms.ModelForm):
    """Form for completing user profile information"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'last_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
        }

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'})
    )

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)
        
        if self.user_profile:
            self.fields['phone'].initial = self.user_profile.phone

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            if self.user_profile:
                self.user_profile.first_name = user.first_name
                self.user_profile.last_name = user.last_name
                self.user_profile.phone = self.cleaned_data['phone']
                self.user_profile.profile_completed = True
                self.user_profile.save()
        
        return user


class TeacherProfileCompleteForm(forms.ModelForm):
    """Form for completing teacher profile information"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'last_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
        }

    # Teacher-specific fields
    bio = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 4,
            'placeholder': 'Write a brief biography about your musical background and teaching approach...'
        }),
        help_text="This biography will be visible to students"
    )
    
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'https://your-website.com'
        }),
        help_text="Optional: Your professional website or portfolio"
    )
    
    teaching_experience = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Describe your teaching experience, qualifications, and credentials...'
        })
    )
    
    specializations = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'List your musical specializations (e.g., jazz piano, classical violin, music theory...)' 
        })
    )

    # Optional contact fields (private, not shown to students)
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Your contact number (private)'
        }),
        help_text="Private - not visible to students"
    )

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)
        
        if self.user_profile:
            self.fields['phone'].initial = self.user_profile.phone
            self.fields['bio'].initial = self.user_profile.bio
            self.fields['website'].initial = self.user_profile.website
            self.fields['teaching_experience'].initial = self.user_profile.teaching_experience
            self.fields['specializations'].initial = self.user_profile.specializations

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            if self.user_profile:
                self.user_profile.first_name = user.first_name
                self.user_profile.last_name = user.last_name
                self.user_profile.phone = self.cleaned_data.get('phone', '')
                self.user_profile.bio = self.cleaned_data['bio']
                self.user_profile.website = self.cleaned_data.get('website', '')
                self.user_profile.teaching_experience = self.cleaned_data.get('teaching_experience', '')
                self.user_profile.specializations = self.cleaned_data.get('specializations', '')
                self.user_profile.profile_completed = True
                self.user_profile.save()
        
        return user


class TeacherResponseForm(forms.Form):
    """Form for teacher to respond to lesson requests"""
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 4,
            'placeholder': 'Add a message for the student about scheduling, pricing, or any changes...'
        }),
        label="Message to Student"
    )


class SubjectForm(forms.ModelForm):
    """Form for teachers to create and edit subjects with pricing"""
    
    class Meta:
        model = Subject
        fields = ['subject', 'description', 'base_price_60min', 'is_active']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Piano, Guitar, Music Theory'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Brief description of what you teach in this subject...'
            }),
            'base_price_60min': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full text-right',
                'step': '0.01',
                'min': '0',
                'placeholder': '50.00'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        self.fields['base_price_60min'].label = "Base Price (60 minutes)"
        self.fields['is_active'].label = "Currently offering this subject"

    def save(self, commit=True):
        subject = super().save(commit=False)
        if self.teacher:
            subject.teacher = self.teacher
        if commit:
            subject.save()
        return subject


class ExamRegistrationForm(forms.ModelForm):
    """Form for teachers to register students for exams"""

    # Override student and child_profile as ChoiceFields
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
            'sight_reading', 'aural_tests', 'fee_amount', 'teacher_notes'
        ]
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
            'fee_amount': forms.NumberInput(attrs={
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

        # Filter students to only accepted students of this teacher
        if self.teacher:
            from .models import TeacherStudentApplication
            accepted_applications = TeacherStudentApplication.objects.filter(
                teacher=self.teacher,
                status='accepted'
            ).select_related('applicant', 'child_profile')

            # Build choices for student field
            student_choices = []
            child_choices = []

            for app in accepted_applications:
                if app.child_profile:
                    # Add guardian to students if not already there
                    if (str(app.applicant.id), f"{app.applicant.get_full_name()} (Guardian)") not in student_choices:
                        student_choices.append((str(app.applicant.id), f"{app.applicant.get_full_name()} (Guardian)"))
                    # Add child to child choices
                    child_choices.append((str(app.child_profile.id), app.child_profile.full_name))
                else:
                    # Adult student
                    student_choices.append((str(app.applicant.id), app.applicant.get_full_name()))

            self.fields['student'].choices = [('', 'Select student')] + student_choices
            self.fields['child_profile'].choices = [('', 'N/A - Adult student')] + child_choices

            # Pre-select student if provided
            if self.selected_student:
                self.fields['student'].initial = str(self.selected_student)

            # Filter subjects to only this teacher's subjects
            self.fields['subject'].queryset = Subject.objects.filter(
                teacher=self.teacher,
                is_active=True
            )

            # Filter exam boards to only active ones
            self.fields['exam_board'].queryset = ExamBoard.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        grade_type = cleaned_data.get('grade_type')
        grade_level = cleaned_data.get('grade_level')

        if grade_type and grade_level:
            if grade_type == ExamRegistration.THEORY:
                if grade_level < 1 or grade_level > 6:
                    self.add_error('grade_level', 'Theory grades must be between 1 and 6')
            else:  # Practical or Performance
                if grade_level < 1 or grade_level > 8:
                    self.add_error('grade_level', 'Practical and Performance grades must be between 1 and 8')

        return cleaned_data

    def save(self, commit=True):
        exam = super().save(commit=False)
        if self.teacher:
            exam.teacher = self.teacher

        # Handle student conversion from string ID to User instance
        student_id = self.cleaned_data.get('student')
        if student_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            exam.student = User.objects.get(id=student_id)

        # Handle child_profile conversion from string ID to instance
        child_profile_id = self.cleaned_data.get('child_profile')
        if child_profile_id:
            from apps.users.models import ChildProfile
            exam.child_profile = ChildProfile.objects.get(id=child_profile_id)
        else:
            exam.child_profile = None

        # Set payment status to pending if fee is greater than 0
        if exam.fee_amount > 0:
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


# Create formset for exam pieces
ExamPieceFormSet = inlineformset_factory(
    ExamRegistration,
    ExamPiece,
    form=ExamPieceForm,
    extra=3,  # Show 3 empty forms by default (typical for most exams)
    min_num=0,  # Pieces are optional (can be added later)
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
        # Make status required and set to results_received by default
        self.fields['status'].initial = ExamRegistration.RESULTS_RECEIVED

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
