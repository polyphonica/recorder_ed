from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import LessonRequest, Subject, LessonRequestMessage
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


class RescheduleForm(forms.Form):
    """Form for teachers to reschedule a lesson inline from cancellation request detail"""

    lesson_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'input input-bordered w-full',
            'type': 'date'
        }),
        label="New Lesson Date"
    )

    lesson_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'input input-bordered w-full',
            'type': 'time'
        }),
        label="New Lesson Time"
    )

    def __init__(self, *args, **kwargs):
        proposed_date = kwargs.pop('proposed_date', None)
        proposed_time = kwargs.pop('proposed_time', None)
        super().__init__(*args, **kwargs)

        # Pre-fill with student's proposed date/time if available
        if proposed_date and not self.is_bound:
            self.fields['lesson_date'].initial = proposed_date
        if proposed_time and not self.is_bound:
            self.fields['lesson_time'].initial = proposed_time


class TeacherInitiateCancellationForm(forms.Form):
    """Form for teachers to cancel or propose a reschedule on an auto-accepted lesson"""
    action = forms.ChoiceField(
        choices=[('cancel', 'Cancel lesson'), ('reschedule', 'Propose new time')],
        widget=forms.RadioSelect,
        label='What would you like to do?'
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'textarea textarea-bordered w-full'}),
        label='Reason (required — visible to student)'
    )
    proposed_new_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
        label='Proposed new date'
    )
    proposed_new_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'input input-bordered w-full'}),
        label='Proposed new time'
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('action') == 'reschedule':
            if not cleaned.get('proposed_new_date') or not cleaned.get('proposed_new_time'):
                raise forms.ValidationError(
                    'A proposed date and time are required when proposing a reschedule.'
                )
        return cleaned


class VoucherForm(forms.ModelForm):
    """Form for teachers to create and edit vouchers/promo codes"""

    DOMAIN_CHOICES = [
        ('private_teaching', 'Private Lessons'),
        ('workshops', 'Workshops'),
        ('workshop_series', 'Workshop Series'),
    ]

    applicable_domains = forms.MultipleChoiceField(
        choices=DOMAIN_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox checkbox-primary'}),
        required=True,
        label="Valid For",
        help_text="Select which types of purchases this voucher can be used for"
    )

    class Meta:
        from apps.payments.models import Voucher
        model = Voucher
        fields = [
            'code', 'description', 'discount_type', 'discount_value',
            'applicable_domains', 'valid_from', 'valid_until',
            'max_uses_total', 'max_uses_per_student', 'minimum_purchase_amount'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'input input-bordered w-full uppercase',
                'placeholder': 'e.g., SUMMER25, FREECLASS',
                'style': 'text-transform: uppercase;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Internal description (e.g., "Competition winner prize")'
            }),
            'discount_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'valid_from': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'valid_until': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'max_uses_total': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'placeholder': 'Leave blank for unlimited'
            }),
            'max_uses_per_student': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1'
            }),
            'minimum_purchase_amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

        # Set labels
        self.fields['code'].label = "Voucher Code"
        self.fields['description'].label = "Description (internal)"
        self.fields['discount_type'].label = "Discount Type"
        self.fields['discount_value'].label = "Discount Value"
        self.fields['valid_from'].label = "Valid From"
        self.fields['valid_until'].label = "Valid Until (optional)"
        self.fields['max_uses_total'].label = "Max Total Uses (optional)"
        self.fields['max_uses_per_student'].label = "Max Uses Per Student"
        self.fields['minimum_purchase_amount'].label = "Minimum Purchase (£)"

        # Set help texts
        self.fields['discount_value'].help_text = "Enter percentage (0-100) or fixed amount in £ depending on type. Not needed for '100% Free'."
        self.fields['max_uses_total'].help_text = "Leave blank for unlimited uses"
        self.fields['valid_until'].help_text = "Leave blank for no expiration"

        # If editing, convert JSONField list to form values
        if self.instance and self.instance.pk:
            if self.instance.applicable_domains:
                self.initial['applicable_domains'] = self.instance.applicable_domains

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError("Voucher code is required.")

        # Check uniqueness (excluding current instance if editing)
        from apps.payments.models import Voucher
        existing = Voucher.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("This voucher code already exists.")

        return code

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')

        # Validate discount value based on type
        if discount_type == 'free':
            cleaned_data['discount_value'] = 0
        elif discount_type == 'percentage':
            if discount_value is None or discount_value <= 0 or discount_value > 100:
                self.add_error('discount_value', 'Percentage must be between 1 and 100.')
        elif discount_type == 'fixed':
            if discount_value is None or discount_value <= 0:
                self.add_error('discount_value', 'Fixed amount must be greater than 0.')

        return cleaned_data

    def save(self, commit=True):
        voucher = super().save(commit=False)
        if self.teacher:
            voucher.created_by = self.teacher

        # Convert form list to JSON list for applicable_domains
        voucher.applicable_domains = self.cleaned_data.get('applicable_domains', [])

        if commit:
            voucher.save()
        return voucher
