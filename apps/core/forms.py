from django import forms
from django.contrib.auth.models import User


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Your full name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'your.email@recorder-ed.com'
        })
    )
    subject = forms.ChoiceField(
        choices=[
            ('general', 'General Inquiry'),
            ('teaching', 'Teaching Question'),
            ('workshop', 'Workshop Request'),
            ('course', 'Course Information'),
        ],
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 5,
            'placeholder': 'Your message here...'
        })
    )
    newsletter = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        label='Subscribe to newsletter'
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Email address'
            }),
        }


class FilterForm(forms.Form):
    CATEGORY_CHOICES = [
        ('', 'All Categories'),
        ('web', 'Web Development'),
        ('mobile', 'Mobile Development'),
        ('data', 'Data Science'),
        ('ai', 'Artificial Intelligence'),
        ('design', 'UI/UX Design'),
    ]
    
    LEVEL_CHOICES = [
        ('', 'All Levels'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Search courses...'
        })
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )
    level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )
    price_range = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'range range-primary',
            'type': 'range',
            'min': '0',
            'max': '500',
            'value': '100'
        })
    )