from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'input input-bordered',
        'placeholder': 'Enter your email address'
    }))
    
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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'phone', 'address_line_1', 'address_line_2', 
                 'city', 'state_province', 'postal_code', 'country', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Last Name'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Phone Number'}),
            'address_line_1': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Address Line 1'}),
            'address_line_2': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Address Line 2 (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'City'}),
            'state_province': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'input input-bordered', 'placeholder': 'Country'}),
            'profile_image': forms.FileInput(attrs={'class': 'file-input file-input-bordered'}),
        }