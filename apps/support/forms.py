from django import forms
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3
from .models import Ticket, TicketMessage, TicketAttachment


class PublicTicketForm(forms.ModelForm):
    """Form for anonymous/public users to create support tickets"""

    captcha = ReCaptchaField(
        widget=ReCaptchaV3(
            attrs={
                'required_score': 0.5,
            }
        ),
        label=''  # No label for invisible reCAPTCHA v3
    )

    class Meta:
        model = Ticket
        fields = ['name', 'email', 'category', 'subject', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'your.email@example.com'
            }),
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Brief description of your issue'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'placeholder': 'Please provide as much detail as possible...',
                'rows': 6
            }),
        }
        help_texts = {
            'category': 'Select the category that best matches your issue',
            'description': 'The more details you provide, the faster we can help you',
        }


class AuthenticatedTicketForm(forms.ModelForm):
    """Form for logged-in users to create support tickets"""

    class Meta:
        model = Ticket
        fields = ['category', 'subject', 'description']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Brief description of your issue'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'placeholder': 'Please provide as much detail as possible...',
                'rows': 6
            }),
        }


class TicketReplyForm(forms.ModelForm):
    """Form for users to reply to their tickets"""

    class Meta:
        model = TicketMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'placeholder': 'Type your reply...',
                'rows': 4
            }),
        }
        labels = {
            'message': 'Your Reply'
        }


class StaffReplyForm(forms.ModelForm):
    """Form for staff to reply to tickets or add internal notes"""

    is_internal_note = forms.BooleanField(
        required=False,
        initial=False,
        label='Internal Note (not visible to user)',
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary'
        })
    )

    class Meta:
        model = TicketMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'placeholder': 'Type your reply or internal note...',
                'rows': 4
            }),
        }
        labels = {
            'message': 'Reply / Internal Note'
        }


class TicketUpdateForm(forms.ModelForm):
    """Form for staff to update ticket status, priority, and assignment"""

    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'assigned_to']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'select select-bordered select-sm'
            }),
            'priority': forms.Select(attrs={
                'class': 'select select-bordered select-sm'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'select select-bordered select-sm'
            }),
        }


class TicketAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to tickets"""

    class Meta:
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*,.pdf,.doc,.docx,.txt'
            }),
        }
        labels = {
            'file': 'Attach File'
        }
        help_texts = {
            'file': 'Accepted formats: Images, PDF, Word documents, Text files (Max 10MB)'
        }


class TeacherApplicationForm(forms.ModelForm):
    """Form for prospective teachers to apply to teach on the platform"""

    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Your phone number (optional)'
        }),
        label='Phone Number',
        help_text='Optional - helps us contact you faster'
    )

    teaching_biography = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'Tell us about your teaching experience, musical background, and approach to teaching...',
            'rows': 6
        }),
        label='Teaching Biography & Experience',
        help_text='Share your teaching journey, experience level, and what makes your teaching unique'
    )

    qualifications = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'List any relevant qualifications, certifications, or professional memberships...',
            'rows': 4
        }),
        label='Qualifications',
        help_text='Formal qualifications are not required, but please share any you have'
    )

    subjects = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Recorder, Flute, Music Theory'
        }),
        label='Subjects You Teach',
        help_text='List the instruments or subjects you teach'
    )

    dbs_check = forms.ChoiceField(
        choices=[
            ('yes', 'Yes - I have a current DBS check'),
            ('in_progress', 'In progress - I am obtaining one'),
            ('no', 'No - I do not have one'),
            ('equivalent', 'I have an equivalent background check')
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary'
        }),
        label='DBS Check / Background Check Status',
        help_text='Required for teaching children in the UK'
    )

    teaching_format = forms.MultipleChoiceField(
        choices=[
            ('online', 'Online (via Zoom)'),
            ('in_person', 'In-person (at my studio)'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        label='Preferred Teaching Format',
        help_text='Select all that apply'
    )

    availability = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'e.g., Weekday afternoons, Saturday mornings...',
            'rows': 3
        }),
        label='General Availability',
        help_text='When are you generally available to teach?'
    )

    terms_agreement = forms.BooleanField(
        required=True,
        label='I understand and agree',
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        help_text=(
            'I understand that: (1) The platform administrator or representative may request to '
            'observe my online lessons, (2) I will be subject to a platform commission on lesson '
            'fees, (3) I must comply with safeguarding requirements when teaching children, '
            '(4) Formal qualifications are not required but teaching competence will be assessed'
        )
    )

    class Meta:
        model = Ticket
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'your.email@example.com'
            }),
        }

    def save(self, commit=True):
        # Create the ticket with all the custom fields in the description
        ticket = super().save(commit=False)

        # Set fixed fields for teacher applications
        ticket.category = 'teacher_application'
        ticket.priority = 'high'
        ticket.subject = f"Teacher Application - {self.cleaned_data['name']}"

        # Build description from all fields
        description_parts = [
            f"**Phone:** {self.cleaned_data.get('phone', 'Not provided')}",
            "",
            "**Teaching Biography & Experience:**",
            self.cleaned_data['teaching_biography'],
            "",
            "**Qualifications:**",
            self.cleaned_data['qualifications'],
            "",
            f"**Subjects:** {self.cleaned_data['subjects']}",
            "",
            f"**DBS/Background Check:** {dict(self.fields['dbs_check'].choices)[self.cleaned_data['dbs_check']]}",
            "",
            f"**Preferred Format:** {', '.join([dict(self.fields['teaching_format'].choices)[fmt] for fmt in self.cleaned_data['teaching_format']])}",
            "",
            "**Availability:**",
            self.cleaned_data['availability'],
            "",
            "**Terms Agreement:** Accepted"
        ]

        ticket.description = "\n".join(description_parts)

        if commit:
            ticket.save()

        return ticket
