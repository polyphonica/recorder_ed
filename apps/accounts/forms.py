from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth.models import User
from .models import UserProfile, ChildProfile
from datetime import date
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

class CustomUserCreationForm(UserCreationForm):
    # Account type selection
    ACCOUNT_TYPE_CHOICES = [
        ('adult_student', 'I am an adult student (18+)'),
        ('parent_guardian', 'I am a parent/guardian signing up for a student under 18'),
    ]

    account_type = forms.ChoiceField(
        required=True,
        choices=ACCOUNT_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary',
        }),
        label="Account Type",
        initial='adult_student'
    )

    # Personal information (required for both account types)
    first_name = forms.CharField(
        required=True,
        max_length=100,
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Your first name'
        })
    )

    last_name = forms.CharField(
        required=True,
        max_length=100,
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Your last name'
        })
    )

    phone = forms.CharField(
        required=True,
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Your phone number'
        })
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Your email address'
        })
    )

    # Address fields (required only for parents/guardians)
    address_line_1 = forms.CharField(
        required=False,
        max_length=255,
        label="Address Line 1",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Street address'
        })
    )

    address_line_2 = forms.CharField(
        required=False,
        max_length=255,
        label="Address Line 2",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Apartment, suite, etc. (optional)'
        })
    )

    city = forms.CharField(
        required=False,
        max_length=100,
        label="City",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'City'
        })
    )

    state_province = forms.CharField(
        required=False,
        max_length=100,
        label="State/Province",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'State or Province'
        })
    )

    postal_code = forms.CharField(
        required=False,
        max_length=20,
        label="Postal Code",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Postal/ZIP code'
        })
    )

    country = forms.CharField(
        required=False,
        max_length=100,
        label="Country",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'Country'
        })
    )

    # Child fields (required only for parents/guardians)
    child_first_name = forms.CharField(
        required=False,
        max_length=100,
        label="Child's First Name",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': "Child's first name"
        })
    )

    child_last_name = forms.CharField(
        required=False,
        max_length=100,
        label="Child's Last Name",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered',
            'placeholder': "Child's last name (for exam registration)"
        })
    )

    child_date_of_birth = forms.DateField(
        required=False,
        label="Child's Date of Birth",
        widget=forms.DateInput(attrs={
            'class': 'input input-bordered',
            'placeholder': 'YYYY-MM-DD',
            'type': 'date'
        }),
        help_text="Used to calculate the child's age"
    )

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'input input-bordered',
            'placeholder': 'Enter your password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'input input-bordered',
            'placeholder': 'Confirm your password'
        })

    def clean_email(self):
        """
        Validate that the email is unique (case-insensitive).
        Prevents duplicate email accounts.
        """
        email = self.cleaned_data.get('email', '').lower().strip()

        # Check if email already exists (case-insensitive)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists. '
                'Please use a different email or try logging in.'
            )

        return email

    def clean(self):
        """Validate fields based on account type"""
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')

        if account_type == 'parent_guardian':
            # For parents/guardians, address and child fields are required

            # Validate address fields
            address_line_1 = cleaned_data.get('address_line_1')
            city = cleaned_data.get('city')
            state_province = cleaned_data.get('state_province')
            postal_code = cleaned_data.get('postal_code')
            country = cleaned_data.get('country')

            if not address_line_1:
                self.add_error('address_line_1', "Address is required for parent/guardian accounts.")
            if not city:
                self.add_error('city', "City is required for parent/guardian accounts.")
            if not state_province:
                self.add_error('state_province', "State/Province is required for parent/guardian accounts.")
            if not postal_code:
                self.add_error('postal_code', "Postal code is required for parent/guardian accounts.")
            if not country:
                self.add_error('country', "Country is required for parent/guardian accounts.")

            # Validate child fields
            child_first_name = cleaned_data.get('child_first_name')
            child_last_name = cleaned_data.get('child_last_name')
            child_date_of_birth = cleaned_data.get('child_date_of_birth')

            if not child_first_name:
                self.add_error('child_first_name', "Child's first name is required.")

            if not child_last_name:
                self.add_error('child_last_name', "Child's last name is required.")

            if not child_date_of_birth:
                self.add_error('child_date_of_birth', "Child's date of birth is required.")
            else:
                # Validate that child is actually under 18
                today = date.today()
                age = today.year - child_date_of_birth.year - ((today.month, today.day) < (child_date_of_birth.month, child_date_of_birth.day))

                if age >= 18:
                    self.add_error('child_date_of_birth', "Child must be under 18 years old. For students 18 and over, please select 'Adult student' account type.")

                # Also check the DOB is not in the future
                if child_date_of_birth > today:
                    self.add_error('child_date_of_birth', "Date of birth cannot be in the future.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class ChildProfileForm(forms.ModelForm):
    """Form for guardians to add/edit child profiles"""
    class Meta:
        model = ChildProfile
        fields = ['first_name', 'last_name', 'date_of_birth']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered',
                'placeholder': "Child's first name"
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered',
                'placeholder': "Child's last name"
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'input input-bordered',
                'type': 'date'
            }),
        }
        labels = {
            'first_name': "Child's First Name",
            'last_name': "Child's Last Name",
            'date_of_birth': "Child's Date of Birth",
        }
        help_texts = {
            'last_name': 'Required for external exam registration',
            'date_of_birth': 'Used to calculate age',
        }

    def clean_date_of_birth(self):
        """Validate that child is under 18"""
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            if age >= 18:
                raise forms.ValidationError(
                    "Child must be under 18 years old. For students 18 and over, "
                    "they should create their own account."
                )

            if dob > today:
                raise forms.ValidationError("Date of birth cannot be in the future.")

        return dob


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            # Personal Information
            'first_name', 'last_name', 'phone', 'profile_image',
            # Address Information
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            # Public Teaching Profile
            'bio', 'teaching_philosophy', 'website',
            # Professional Background
            'qualifications', 'professional_memberships', 'dbs_check_status',
            # Teaching Specializations
            'instruments_taught', 'exam_boards_offered', 'age_groups_taught',
            # Teaching Settings
            'default_zoom_link',
            # Notification Preferences
            'email_on_new_message',
            'workshop_email_notifications'
        ]
        widgets = {
            # Personal Information
            'first_name': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Last Name'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Phone Number'}),
            'profile_image': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),

            # Address Information
            'address_line_1': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Address Line 1'}),
            'address_line_2': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Address Line 2 (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'City'}),
            'state_province': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Country'}),

            # Public Teaching Profile
            'bio': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered',
                'placeholder': 'Introduce yourself and share what makes you unique as a music teacher...',
                'rows': 4
            }),
            'teaching_philosophy': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered',
                'placeholder': 'Describe your approach to teaching music (e.g., student-centered, emphasis on technique and musicality, preparing for performances)...',
                'rows': 4
            }),
            'website': forms.URLInput(attrs={
                'class': 'input input-bordered',
                'placeholder': 'https://yourwebsite.com'
            }),

            # Professional Background
            'qualifications': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered',
                'placeholder': 'List your qualifications, one per line:\n• BA (Hons) Music - Royal College of Music\n• DipABRSM Performance Diploma\n• PGCE Music Education',
                'rows': 5
            }),
            'professional_memberships': forms.TextInput(attrs={
                'class': 'input input-bordered',
                'placeholder': 'e.g., Musicians\' Union, ISM, Trinity College London'
            }),
            'dbs_check_status': forms.Select(attrs={
                'class': 'select select-bordered'
            }),

            # Teaching Specializations
            'instruments_taught': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered',
                'placeholder': 'List instruments and levels, one per line:\n• Recorder: Beginner to Grade 8\n• Flute: Beginner to Grade 5\n• Music Theory: Grades 1-5',
                'rows': 4
            }),
            'exam_boards_offered': forms.TextInput(attrs={
                'class': 'input input-bordered',
                'placeholder': 'e.g., Trinity College London, ABRSM, Rock School'
            }),
            'age_groups_taught': forms.TextInput(attrs={
                'class': 'input input-bordered',
                'placeholder': 'e.g., Children (5-12), Teens (13-18), Adults (18+)'
            }),

            # Teaching Settings
            'default_zoom_link': forms.URLInput(attrs={
                'class': 'input input-bordered',
                'placeholder': 'https://zoom.us/j/your-meeting-id or Google Meet link'
            }),

            # Notification Preferences
            'email_on_new_message': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'workshop_email_notifications': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }


class AccountTransferForm(forms.Form):
    """Form for transferring a child account to an adult account when they turn 18"""
    email = forms.EmailField(
        label="Your Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter your email address'
        }),
        help_text="This will be your new login email"
    )

    password1 = forms.CharField(
        label="Create Password",
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter a secure password'
        })
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Confirm your password'
        })
    )

    phone = forms.CharField(
        required=False,
        label="Phone Number (Optional)",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': '+1 (555) 123-4567'
        })
    )

    confirm_transfer = forms.BooleanField(
        required=True,
        label="I confirm that I am 18 years or older and wish to transfer this account to my own name",
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary'
        })
    )

    def clean_email(self):
        """Validate that the email is unique"""
        email = self.cleaned_data.get('email', '').lower().strip()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists. '
                'Please use a different email.'
            )

        return email

    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")

        return cleaned_data


class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form that sends HTML emails with RECORDER-ED branding.
    Overrides the default Django password reset to send multipart emails.
    """

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a password reset email with both plain text and HTML versions.
        """
        # Render subject from template
        subject = render_to_string(subject_template_name, context)
        # Remove newlines from subject
        subject = ''.join(subject.splitlines())

        # Render plain text message
        text_message = render_to_string(email_template_name, context)

        # Render HTML message
        html_message = None
        if html_email_template_name:
            html_message = render_to_string(html_email_template_name, context)

        # Send multipart email (plain text + HTML)
        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )