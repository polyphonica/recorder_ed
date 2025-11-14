from django import forms
from .models import Ticket, TicketMessage, TicketAttachment


class PublicTicketForm(forms.ModelForm):
    """Form for anonymous/public users to create support tickets"""

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
