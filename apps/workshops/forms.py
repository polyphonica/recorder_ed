from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Workshop, WorkshopSession, WorkshopRegistration, WorkshopCategory, WorkshopInterest, WorkshopMaterial, WorkshopTestimonial, WorkshopCompetition, WorkshopCompetitionAnswer


TIMEZONE_CHOICES = [
    ('UTC', 'UTC'),
    ('US/Eastern', 'Eastern Time'),
    ('US/Central', 'Central Time'),
    ('US/Mountain', 'Mountain Time'),
    ('US/Pacific', 'Pacific Time'),
    ('Europe/London', 'London Time'),
    ('Europe/Paris', 'Central European Time'),
    ('Asia/Tokyo', 'Tokyo Time'),
    ('Australia/Sydney', 'Sydney Time'),
]


class WorkshopRegistrationForm(forms.ModelForm):
    """Form for workshop registration"""

    # Add child selection field for guardians
    child_profile = forms.ChoiceField(
        required=False,
        label="Register for:",
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary'
        }),
        help_text="Select which child to register for this workshop"
    )

    class Meta:
        model = WorkshopRegistration
        fields = [
            'email', 'phone', 'emergency_contact', 'experience_level',
            'expectations', 'special_requirements'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'your.email@recorder-ed.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '+1 (555) 123-4567'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Name and phone number (e.g., Jane Doe +1 555-123-4567)'
            }),
            'experience_level': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'expectations': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'e.g., Soprano recorder, Alto recorder, Tenor recorder...'
            }),
            'special_requirements': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Any accessibility needs or special requirements?'
            }),
        }
        help_texts = {
            'emergency_contact': 'Required for on-site workshops. In case of emergency, who should we contact? Include their name and phone number.',
            'experience_level': 'How would you rate your current experience level?',
            'expectations': 'This helps the instructor prepare appropriate music and materials for your instruments.',
            'special_requirements': 'We want to ensure everyone can participate fully.',
        }
        labels = {
            'expectations': 'Instruments',
        }

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill email if user is authenticated
        if self.user and self.user.is_authenticated and self.user.email:
            self.fields['email'].initial = self.user.email

        # Make phone optional but recommended
        self.fields['phone'].required = False
        self.fields['expectations'].required = False
        self.fields['special_requirements'].required = False

        # Emergency contact is required for on-site workshops
        if self.session and self.session.workshop.delivery_method == 'in_person':
            self.fields['emergency_contact'].required = True
            self.fields['emergency_contact'].label = 'Emergency Contact (Required for on-site workshops)'
        else:
            self.fields['emergency_contact'].required = False
            self.fields['emergency_contact'].label = 'Emergency Contact (Optional for online workshops)'

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

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email and self.user and self.user.is_authenticated:
            email = self.user.email
        return email


class WorkshopForm(forms.ModelForm):
    """Form for creating and editing workshops"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make price field not required since it's handled in clean() method
        self.fields['price'].required = False
        # Sort categories alphabetically
        self.fields['category'].queryset = WorkshopCategory.objects.filter(is_active=True).order_by('name')

    class Meta:
        model = Workshop
        fields = [
            'title', 'slug', 'short_description', 'description', 'category',
            'difficulty_level', 'duration_value', 'duration_unit', 'tags',
            'learning_objectives', 'prerequisites', 'materials_needed',
            'featured_image', 'promo_video_url',
            'delivery_method', 'venue_name', 'venue_address', 'venue_city',
            'venue_postcode', 'venue_map_link', 'venue_notes', 'max_venue_capacity',
            'is_free', 'price',
            'is_series', 'series_price', 'require_full_series_registration', 'series_description',
            'status', 'is_featured'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter workshop title...',
                'x-on:input': "if (!isEditMode || !$root.querySelector('[name=slug]').value) { $root.querySelector('[name=slug]').value = generateSlug($event.target.value) }",
            }),
            'slug': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'url-friendly-slug'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Brief description for workshop cards...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 6,
                'placeholder': 'Detailed workshop description...'
            }),
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'duration_value': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 1,
                'placeholder': '2'
            }),
            'duration_unit': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'tag1, tag2, tag3...'
            }),
            'learning_objectives': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'What will participants learn?'
            }),
            'prerequisites': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Any required knowledge or skills?'
            }),
            'materials_needed': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'What should participants bring?'
            }),
            'featured_image': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*'
            }),
            'promo_video_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'delivery_method': forms.Select(attrs={
                'class': 'select select-bordered w-full',
                'x-on:change': 'deliveryMethod = $event.target.value',
            }),
            'venue_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Community Center, Office Building, etc.'
            }),
            'venue_address': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': '123 Main Street, Suite 200'
            }),
            'venue_city': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'City name'
            }),
            'venue_postcode': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '12345'
            }),
            'venue_map_link': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://maps.google.com/...'
            }),
            'venue_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Parking info, entrance details, accessibility notes...'
            }),
            'max_venue_capacity': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 1,
                'placeholder': '20'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 0,
                'step': 0.01,
                'placeholder': '0.00',
                'required': False  # We'll handle this in clean() method
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary',
                'x-on:change': 'isFree = $event.target.checked',
            }),
            # Series Configuration
            'is_series': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary',
                'x-on:change': 'isSeries = $event.target.checked',
            }),
            'series_price': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 0,
                'step': 0.01,
                'placeholder': '200.00'
            }),
            'require_full_series_registration': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'series_description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Session 1 (Jan 15): Introduction to Interpretation\nSession 2 (Jan 22): Phrasing and Dynamics\n...'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_free = cleaned_data.get('is_free')
        price = cleaned_data.get('price')
        is_series = cleaned_data.get('is_series')
        series_price = cleaned_data.get('series_price')
        require_full_series = cleaned_data.get('require_full_series_registration')

        # Validate regular pricing
        if is_free:
            # If workshop is free, set price to 0
            cleaned_data['price'] = 0.00
        else:
            # If workshop is not free, price is required
            if price is None or price == '':
                raise forms.ValidationError({
                    'price': 'Price is required for paid workshops.'
                })
            if price < 0:
                raise forms.ValidationError({
                    'price': 'Price cannot be negative.'
                })

        # Validate series pricing
        if is_series:
            if not series_price:
                raise forms.ValidationError({
                    'series_price': 'Series price is required when creating a series workshop.'
                })
            if series_price < 0:
                raise forms.ValidationError({
                    'series_price': 'Series price cannot be negative.'
                })
            # Warn if series price is higher than individual session price
            # (though this might be intentional in some cases)
            if price and series_price < price:
                # This is unusual but allowed - might be a deep discount for series
                pass
        else:
            # If not a series, clear series-related fields
            cleaned_data['series_price'] = None
            cleaned_data['require_full_series_registration'] = False
            cleaned_data['series_description'] = ''

        return cleaned_data


class WorkshopSessionForm(forms.ModelForm):
    """Form for creating workshop sessions"""

    class Meta:
        model = WorkshopSession
        fields = [
            'session_title',
            'start_datetime', 'end_datetime', 'timezone_name',
            'max_participants', 'waitlist_enabled',
            'meeting_url', 'meeting_id', 'meeting_password',
            'session_notes'
        ]
        widgets = {
            'session_title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Session 1: Basic Technique, Articulation Part 1'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'timezone_name': forms.Select(choices=TIMEZONE_CHOICES, attrs={
                'class': 'select select-bordered w-full'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '20',
                'min': '1'
            }),
            'meeting_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://zoom.us/j/...'
            }),
            'meeting_id': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Meeting ID'
            }),
            'meeting_password': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Meeting Password'
            }),
            'session_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Special notes for this session (optional)'
            }),
            'waitlist_enabled': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }
        help_texts = {
            'session_title': 'Optional descriptive title for this session (especially useful for series)',
            'start_datetime': 'When the session begins',
            'end_datetime': 'When the session ends',
            'max_participants': 'Maximum number of registered participants',
            'waitlist_enabled': 'Allow students to join waitlist when session is full',
            'meeting_url': 'Video conference link for the session (Zoom, Teams, Meet, etc.)',
            'meeting_id': 'Meeting ID for manual entry if needed',
            'meeting_password': 'Password to join the meeting (if required)',
            'session_notes': 'Any special instructions or information for this session',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        
        if start_datetime and end_datetime:
            if start_datetime >= end_datetime:
                raise forms.ValidationError(
                    'End time must be after start time.'
                )
            
            if start_datetime <= timezone.now():
                raise forms.ValidationError(
                    'Session cannot be scheduled in the past.'
                )
            
            # Check for reasonable duration (15 minutes to 8 hours)
            duration = end_datetime - start_datetime
            if duration.total_seconds() < 900:  # 15 minutes
                raise forms.ValidationError(
                    'Session must be at least 15 minutes long.'
                )
            if duration.total_seconds() > 28800:  # 8 hours
                raise forms.ValidationError(
                    'Session cannot be longer than 8 hours.'
                )
        
        return cleaned_data


class BatchSessionForm(forms.Form):
    """Form for creating multiple recurring sessions at once"""

    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 2 Weeks'),
        ('monthly', 'Monthly'),
    ]

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'input input-bordered w-full',
            'type': 'date',
        }),
        help_text='Date of the first session',
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'input input-bordered w-full',
            'type': 'time',
        }),
        help_text='Start time (same for all sessions)',
    )
    duration_minutes = forms.IntegerField(
        min_value=15,
        max_value=480,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full',
            'min': '15',
            'max': '480',
        }),
        help_text='Duration in minutes per session',
    )
    timezone_name = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full',
        }),
    )
    frequency = forms.ChoiceField(
        choices=FREQUENCY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full',
        }),
    )
    number_of_sessions = forms.IntegerField(
        min_value=2,
        max_value=52,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full',
            'min': '2',
            'max': '52',
            'placeholder': 'e.g. 6',
        }),
        help_text='Number of sessions to create (2–52)',
    )
    max_participants = forms.IntegerField(
        min_value=1,
        initial=20,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full',
            'min': '1',
            'placeholder': '20',
        }),
    )
    waitlist_enabled = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
    )
    meeting_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'https://zoom.us/j/...',
        }),
    )
    title_pattern = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Session {n}: Topic',
        }),
        help_text='Use {n} for session number. e.g. "Week {n}" → "Week 1", "Week 2"...',
    )
    session_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 2,
            'placeholder': 'Notes shared across all sessions (optional)',
        }),
    )

    def __init__(self, *args, workshop=None, **kwargs):
        super().__init__(*args, **kwargs)
        if workshop:
            self.fields['duration_minutes'].initial = workshop.estimated_duration

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        start_time = cleaned_data.get('start_time')
        number_of_sessions = cleaned_data.get('number_of_sessions')
        frequency = cleaned_data.get('frequency')

        if start_date and start_time:
            from datetime import datetime
            first_start = datetime.combine(start_date, start_time)
            if timezone.make_aware(first_start, timezone.get_current_timezone()) <= timezone.now():
                raise forms.ValidationError('The first session must be in the future.')

            # Check that the series doesn't span more than 1 year
            if number_of_sessions and frequency:
                last_date = self._calculate_date(start_date, frequency, number_of_sessions - 1)
                if (last_date - start_date).days > 365:
                    raise forms.ValidationError(
                        'The series spans more than 1 year. Reduce the number of sessions or frequency.'
                    )

        return cleaned_data

    def _calculate_date(self, start_date, frequency, offset):
        """Calculate the date for session at the given offset from start."""
        if frequency == 'weekly':
            return start_date + timedelta(weeks=offset)
        elif frequency == 'biweekly':
            return start_date + timedelta(weeks=offset * 2)
        elif frequency == 'monthly':
            return start_date + relativedelta(months=offset)
        return start_date

    def generate_sessions(self):
        """Generate a list of session dicts from the cleaned form data."""
        data = self.cleaned_data
        start_date = data['start_date']
        start_time = data['start_time']
        duration = timedelta(minutes=data['duration_minutes'])
        sessions = []

        for i in range(data['number_of_sessions']):
            session_date = self._calculate_date(start_date, data['frequency'], i)
            from datetime import datetime
            start_dt = datetime.combine(session_date, start_time)
            end_dt = start_dt + duration

            title = ''
            if data.get('title_pattern'):
                title = data['title_pattern'].replace('{n}', str(i + 1))

            sessions.append({
                'session_title': title,
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'timezone_name': data['timezone_name'],
                'max_participants': data['max_participants'],
                'waitlist_enabled': data['waitlist_enabled'],
                'meeting_url': data.get('meeting_url') or '',
                'session_notes': data.get('session_notes') or '',
            })

        return sessions


class WorkshopMaterialForm(forms.ModelForm):
    """Form for instructors to upload session materials"""
    
    class Meta:
        model = WorkshopMaterial
        fields = [
            'title', 'description', 'material_type', 'file', 'external_url',
            'access_timing', 'requires_registration', 'is_downloadable', 'order'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter material title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Brief description of this material...'
            }),
            'material_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'file': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.zip,.py,.js,.html,.css'
            }),
            'external_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://recorder-ed.com/resource'
            }),
            'access_timing': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': 0,
                'placeholder': '0'
            }),
            'requires_registration': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'is_downloadable': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        help_texts = {
            'title': 'Display name for the material',
            'description': 'Brief description of what this material contains',
            'material_type': 'Type of material for organization',
            'file': 'Upload a file (PDF, Word, PowerPoint, etc.)',
            'external_url': 'Or provide a link to external resource',
            'access_timing': 'When participants can access this material',
            'requires_registration': 'Only registered participants can access',
            'is_downloadable': 'Allow participants to download the file',
            'order': 'Display order (0 = first)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        external_url = cleaned_data.get('external_url')
        
        if not file and not external_url:
            raise forms.ValidationError(
                'Either upload a file or provide an external URL.'
            )
        
        if file and external_url:
            raise forms.ValidationError(
                'Please provide either a file or an external URL, not both.'
            )
        
        return cleaned_data


class WorkshopFilterForm(forms.Form):
    """Form for filtering workshops in the list view"""
    
    PRICE_CHOICES = [
        ('', 'All Prices'),
        ('free', 'Free'),
        ('paid', 'Paid'),
    ]
    
    SORT_CHOICES = [
        ('featured', 'Featured First'),
        ('next_session', 'Next Session (Soonest First)'),
        ('newest', 'Newest First'),
        ('title', 'Title A-Z'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
    ]
    
    category = forms.ModelChoiceField(
        queryset=WorkshopCategory.objects.filter(is_active=True).order_by('name'),
        empty_label='All Categories',
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )
    
    delivery_method = forms.ChoiceField(
        choices=[('', 'All Delivery Methods')] + Workshop.DELIVERY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )

    difficulty = forms.ChoiceField(
        choices=[('', 'All Difficulty Levels')] + Workshop.DIFFICULTY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )

    price = forms.ChoiceField(
        choices=PRICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )

    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )


class WorkshopInterestForm(forms.ModelForm):
    """Form for requesting interest in a workshop without available sessions"""
    
    class Meta:
        model = WorkshopInterest
        fields = [
            'email', 'preferred_timing', 'experience_level', 
            'special_requests', 'notify_immediately'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered input-sm w-full',
                'placeholder': 'your.email@recorder-ed.com'
            }),
            'preferred_timing': forms.Select(attrs={
                'class': 'select select-bordered select-sm w-full'
            }),
            'experience_level': forms.Select(attrs={
                'class': 'select select-bordered select-sm w-full'
            }),
            'special_requests': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered textarea-sm w-full',
                'rows': 2,
                'placeholder': 'Any specific topics you\'d like covered or accessibility needs...'
            }),
            'notify_immediately': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-sm checkbox-primary'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.workshop = kwargs.pop('workshop', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill email if user is authenticated
        if self.user and self.user.is_authenticated:
            self.fields['email'].initial = self.user.email
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.workshop:
            instance.workshop = self.workshop
        if self.user and self.user.is_authenticated:
            instance.user = self.user
            
        if commit:
            instance.save()
        return instance


class FeedbackForm(forms.Form):
    """Form for students to submit private feedback after attending a workshop."""
    rating = forms.IntegerField(min_value=1, max_value=5)
    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Share your thoughts on the workshop (optional)...',
        }),
    )


class TestimonialForm(forms.ModelForm):
    """Form for instructors to create or edit a testimonial."""
    class Meta:
        model = WorkshopTestimonial
        fields = ['display_name', 'quote', 'rating']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g. Sarah T.',
            }),
            'quote': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'The testimonial quote...',
            }),
            'rating': forms.NumberInput(attrs={
                'class': 'input input-bordered w-20',
                'min': 1, 'max': 5,
            }),
        }


class WorkshopCompetitionForm(forms.ModelForm):
    """Form for instructors to create a competition question."""
    class Meta:
        model = WorkshopCompetition
        fields = ['question']
        widgets = {
            'question': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'e.g. What is the fingering for a high D on the soprano recorder?',
            }),
        }
        labels = {
            'question': 'Competition Question',
        }


class WorkshopCompetitionAnswerForm(forms.ModelForm):
    """Form for a single answer option."""
    class Meta:
        model = WorkshopCompetitionAnswer
        fields = ['text', 'is_correct', 'order']
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Answer option',
            }),
            'is_correct': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
            'order': forms.HiddenInput(),
        }
        labels = {
            'text': '',
            'is_correct': 'Correct',
        }


CompetitionAnswerFormSet = forms.inlineformset_factory(
    WorkshopCompetition,
    WorkshopCompetitionAnswer,
    form=WorkshopCompetitionAnswerForm,
    fields=['text', 'is_correct', 'order'],
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)