from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


# Extend User model with display methods
def user_display_name(self):
    """Return full name if available, otherwise username"""
    if self.first_name and self.last_name:
        return f"{self.first_name} {self.last_name}"
    elif self.first_name or self.last_name:
        return f"{self.first_name}{self.last_name}".strip()
    else:
        return self.username

def user_full_name_or_username(self):
    """Return full name with fallback to username"""
    full_name = f"{self.first_name} {self.last_name}".strip()
    return full_name if full_name else self.username

def user_is_instructor(self):
    """
    Check if user has teacher/instructor status.
    Now uses the unified profile.is_teacher from accounts app.
    """
    # Use unified profile from accounts app
    try:
        if hasattr(self, 'profile'):
            return self.profile.is_teacher
    except:
        pass

    # Fallback to False if no profile exists
    return False

# Add methods to User model
User.add_to_class('display_name', user_display_name)
User.add_to_class('full_name_or_username', user_full_name_or_username)
User.add_to_class('is_instructor', user_is_instructor)


class UserProfile(models.Model):
    """Extended user profile for instructor status and other user attributes"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    is_instructor = models.BooleanField(
        default=False, 
        help_text="Designates whether this user can create and manage workshops. Does not grant admin backend access."
    )
    bio = models.TextField(blank=True, help_text="Instructor biography")
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.display_name()} ({'Instructor' if self.is_instructor else 'Student'})"


class WorkshopCategory(models.Model):
    """Categories for organizing workshops"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='book-open')
    color = models.CharField(max_length=20, default='primary')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Workshop Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Workshop(models.Model):
    """Main workshop model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('mixed', 'Mixed Ability'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, help_text="Brief summary for listings")
    
    # Content
    learning_objectives = models.TextField(help_text="What students will learn")
    prerequisites = models.TextField(blank=True, help_text="Required knowledge or skills")
    materials_needed = models.TextField(blank=True, help_text="Materials students should have")
    
    # Organization
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshops')
    category = models.ForeignKey(WorkshopCategory, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    # Difficulty and Duration
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    
    DURATION_UNIT_CHOICES = [
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
    ]
    
    duration_value = models.PositiveIntegerField(default=60, help_text="Duration amount")
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, default='minutes')
    
    # Media
    featured_image = models.ImageField(upload_to='workshops/images/', blank=True, null=True)
    promo_video_url = models.URLField(blank=True, help_text="YouTube or Vimeo URL")
    
    # Pricing
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Delivery Method and Venue
    DELIVERY_CHOICES = [
        ('online', 'Online'),
        ('in_person', 'In-Person'),
        ('hybrid', 'Hybrid (Online + In-Person)'),
    ]
    
    delivery_method = models.CharField(
        max_length=20, 
        choices=DELIVERY_CHOICES, 
        default='online',
        help_text="How will this workshop be delivered?"
    )
    venue_name = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Name of the venue (required for in-person workshops)"
    )
    venue_address = models.TextField(
        blank=True, 
        help_text="Street address of the venue"
    )
    venue_city = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="City where the venue is located"
    )
    venue_postcode = models.CharField(
        max_length=20, 
        blank=True, 
        help_text="Postal/ZIP code for the venue"
    )
    venue_map_link = models.URLField(
        blank=True, 
        help_text="Link to Google Maps, Apple Maps, etc."
    )
    venue_notes = models.TextField(
        blank=True, 
        help_text="Additional venue info: parking, entrance, accessibility notes"
    )
    max_venue_capacity = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Maximum in-person participants (if different from online capacity)"
    )
    
    # Status and Publishing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Stats (denormalized for performance)
    total_sessions = models.PositiveIntegerField(default=0)
    total_registrations = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['instructor', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('workshops:detail', kwargs={'slug': self.slug})
    
    @property
    def duration_display(self):
        """Display duration in user-friendly format"""
        if self.duration_value == 1:
            # Singular form
            unit_singular = {
                'minutes': 'minute',
                'hours': 'hour', 
                'days': 'day',
                'weeks': 'week'
            }
            return f"{self.duration_value} {unit_singular.get(self.duration_unit, self.duration_unit)}"
        else:
            # Plural form
            return f"{self.duration_value} {self.duration_unit}"
    
    @property
    def estimated_duration(self):
        """Backward compatibility - return duration in minutes"""
        multipliers = {
            'minutes': 1,
            'hours': 60,
            'days': 1440,  # 24 * 60
            'weeks': 10080  # 7 * 24 * 60
        }
        return self.duration_value * multipliers.get(self.duration_unit, 1)
    
    @property
    def duration_in_hours(self):
        """Get duration in hours for easier comparison"""
        return self.estimated_duration / 60
    
    @property
    def is_published(self):
        return self.status == 'published'
    
    @property
    def next_session(self):
        """Get the next upcoming session"""
        return self.sessions.filter(
            start_datetime__gte=timezone.now(),
            is_active=True
        ).order_by('start_datetime').first()
    
    @property
    def upcoming_sessions(self):
        """Get all upcoming sessions"""
        return self.sessions.filter(
            start_datetime__gte=timezone.now(),
            is_active=True
        ).order_by('start_datetime')
    
    @property
    def has_upcoming_sessions(self):
        """Check if workshop has any upcoming sessions (regardless of availability)"""
        return self.upcoming_sessions.exists()
    
    @property
    def has_available_sessions(self):
        """Check if workshop has any upcoming sessions with spots available"""
        return self.upcoming_sessions.filter(
            current_registrations__lt=models.F('max_participants')
        ).exists()
    
    def get_tags_list(self):
        """Return tags as a list"""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    @property
    def is_online_only(self):
        """Check if workshop is online only"""
        return self.delivery_method == 'online'
    
    @property
    def is_in_person_only(self):
        """Check if workshop is in-person only"""
        return self.delivery_method == 'in_person'
    
    @property
    def is_hybrid(self):
        """Check if workshop offers both online and in-person options"""
        return self.delivery_method == 'hybrid'
    
    @property
    def requires_venue(self):
        """Check if workshop requires venue information"""
        return self.delivery_method in ['in_person', 'hybrid']
    
    @property
    def full_venue_address(self):
        """Return formatted full address"""
        if not self.venue_address:
            return ''

        address_parts = [self.venue_address]
        if self.venue_city:
            address_parts.append(self.venue_city)
        if self.venue_postcode:
            address_parts.append(self.venue_postcode)

        return ', '.join(address_parts)

    @property
    def actual_registrations_count(self):
        """Get actual count of active registrations across all sessions"""
        return WorkshopRegistration.objects.filter(
            session__workshop=self,
            status__in=['registered', 'attended', 'waitlisted']
        ).count()


class WorkshopSession(models.Model):
    """Scheduled instances of workshops"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='sessions')
    
    # Schedule
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    timezone_name = models.CharField(max_length=50, default='UTC')
    
    # Capacity
    max_participants = models.PositiveIntegerField(default=20)
    current_registrations = models.PositiveIntegerField(default=0)
    waitlist_enabled = models.BooleanField(default=True)
    
    # Session Details
    session_notes = models.TextField(blank=True, help_text="Special notes for this session")
    meeting_url = models.URLField(blank=True, help_text="Zoom, Meet, or other video platform URL")
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)
    
    # Session-specific delivery method (optional override)
    session_delivery_override = models.CharField(
        max_length=20,
        choices=Workshop.DELIVERY_CHOICES,
        blank=True,
        help_text="Override workshop delivery method for this specific session"
    )
    session_venue_notes = models.TextField(
        blank=True,
        help_text="Session-specific venue information or changes"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    
    # Recording
    recording_url = models.URLField(blank=True)
    recording_available_until = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['workshop', 'start_datetime']),
            models.Index(fields=['start_datetime', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.workshop.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_full(self):
        return self.current_registrations >= self.max_participants
    
    @property
    def spots_remaining(self):
        return max(0, self.max_participants - self.current_registrations)
    
    @property
    def is_past(self):
        return self.end_datetime < timezone.now()
    
    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime
    
    @property
    def is_upcoming(self):
        return self.start_datetime > timezone.now()
    
    def update_registration_count(self):
        """Update the current registration count based on active registrations"""
        self.current_registrations = self.registrations.filter(
            status__in=['registered', 'promoted', 'attended']
        ).count()
        self.save(update_fields=['current_registrations'])
    
    @property
    def effective_delivery_method(self):
        """Get the delivery method for this session (override or inherit from workshop)"""
        return self.session_delivery_override or self.workshop.delivery_method
    
    @property
    def is_session_online(self):
        """Check if this session is delivered online"""
        return self.effective_delivery_method in ['online', 'hybrid']
    
    @property
    def is_session_in_person(self):
        """Check if this session is delivered in-person"""
        return self.effective_delivery_method in ['in_person', 'hybrid']
    
    def update_waitlist_positions(self):
        """Update waitlist positions for this session"""
        waitlisted_registrations = self.registrations.filter(
            status='waitlisted'
        ).order_by('registration_date')
        
        for index, registration in enumerate(waitlisted_registrations, start=1):
            if registration.waitlist_position != index:
                registration.waitlist_position = index
                registration.save(update_fields=['waitlist_position'])
    
    def get_next_waitlist_position(self):
        """Get the next available waitlist position"""
        last_position = self.registrations.filter(
            status='waitlisted'
        ).aggregate(
            max_position=models.Max('waitlist_position')
        )['max_position']
        
        return (last_position or 0) + 1
    
    def process_waitlist_promotions(self, promoted_by=None, reason='capacity_increase'):
        """Process waitlist promotions when capacity increases"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calculate available spots
        active_registrations = self.registrations.filter(
            status__in=['registered', 'promoted', 'attended']
        ).count()
        available_spots = self.max_participants - active_registrations
        
        if available_spots <= 0:
            return []
        
        # Get waitlisted students in order
        waitlisted = self.registrations.filter(
            status='waitlisted'
        ).order_by('waitlist_position', 'registration_date')[:available_spots]
        
        promoted_registrations = []
        promotion_deadline = timezone.now() + timedelta(hours=48)  # 48-hour confirmation window
        
        for registration in waitlisted:
            # Update registration status to promoted (awaiting payment/confirmation)
            registration.status = 'promoted'
            registration.promoted_at = timezone.now()
            registration.promotion_expires_at = promotion_deadline
            registration.promotion_notification_sent = False
            registration.save()
            
            # Create promotion audit record
            from django.apps import apps
            WaitlistPromotion = apps.get_model('workshops', 'WaitlistPromotion')
            WaitlistPromotion.objects.create(
                registration=registration,
                promoted_by=promoted_by,
                reason=reason,
                expires_at=promotion_deadline
            )
            
            promoted_registrations.append(registration)
        
        # Update session registration count (include promoted students as they hold spots)
        self.current_registrations = self.registrations.filter(
            status__in=['registered', 'promoted', 'attended']
        ).count()
        self.save(update_fields=['current_registrations'])
        
        # Update remaining waitlist positions
        self.update_waitlist_positions()
        
        return promoted_registrations
    
    def get_waitlist_info(self):
        """Get waitlist statistics for this session"""
        waitlisted = self.registrations.filter(status='waitlisted')
        return {
            'total_waitlisted': waitlisted.count(),
            'next_position': self.get_next_waitlist_position(),
            'waitlisted_students': waitlisted.order_by('waitlist_position', 'registration_date')
        }


class WorkshopRegistration(models.Model):
    """
    Student registrations for workshop sessions.

    Supports both adult students and children (under 18).
    - For adults: student field is populated, child_profile is None
    - For children: student field = guardian, child_profile = child
    """
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('registered', 'Registered'),
        ('waitlisted', 'Waitlisted'),
        ('promoted', 'Promoted (Awaiting Payment)'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkshopSession, on_delete=models.CASCADE, related_name='registrations')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workshop_registrations',
        help_text="For adults: the student. For children: the guardian/parent."
    )

    # Child profile (for students under 18)
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.CASCADE,
        related_name='workshop_registrations',
        null=True,
        blank=True,
        help_text="If registering a child, link to their child profile"
    )

    # Registration Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    registration_date = models.DateTimeField(auto_now_add=True)

    # Contact Information
    email = models.EmailField()  # Guardian's email for child registrations
    phone = models.CharField(max_length=20, blank=True)  # Guardian's phone for child registrations
    
    # Experience and Expectations
    experience_level = models.CharField(max_length=20, choices=Workshop.DIFFICULTY_CHOICES, blank=True)
    expectations = models.TextField(blank=True, help_text="What do you hope to learn?")
    special_requirements = models.TextField(blank=True, help_text="Accessibility or other needs")
    
    # Post-Session
    attended = models.BooleanField(default=False)
    rating = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback = models.TextField(blank=True)
    
    # Waitlist Management
    waitlist_position = models.PositiveIntegerField(null=True, blank=True, help_text="Position in waitlist queue")
    promoted_at = models.DateTimeField(null=True, blank=True, help_text="When moved from waitlist to registered")
    promotion_expires_at = models.DateTimeField(null=True, blank=True, help_text="Deadline to confirm promotion")
    promotion_notification_sent = models.BooleanField(default=False, help_text="Whether promotion notification was sent")

    # Payment Information
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', 'Not Required'),
            ('pending', 'Pending Payment'),
            ('completed', 'Payment Completed'),
            ('failed', 'Payment Failed'),
        ],
        default='not_required',
        help_text="Payment status for paid workshops"
    )
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Amount paid for this registration"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe PaymentIntent ID"
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Checkout Session ID"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was completed"
    )

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['registration_date']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['child_profile', 'status']),
            models.Index(fields=['session', 'waitlist_position']),
            models.Index(fields=['promotion_expires_at']),
        ]

    def __str__(self):
        if self.child_profile:
            return f"{self.child_profile.full_name} (Guardian: {self.student.get_full_name() or self.student.username}) - {self.session}"
        else:
            return f"{self.student.get_full_name() or self.student.username} - {self.session}"

    @property
    def student_name(self):
        """Return the name of the actual student (child or adult)"""
        if self.child_profile:
            return self.child_profile.full_name
        return self.student.get_full_name() or self.student.username

    @property
    def guardian(self):
        """Return guardian user if this is a child registration, None otherwise"""
        return self.student if self.child_profile else None

    @property
    def is_child_registration(self):
        """Check if this is a registration for a child (under 18)"""
        return self.child_profile is not None
    
    def save(self, *args, **kwargs):
        """Override save to handle waitlist position assignment"""
        if self.status == 'waitlisted' and not self.waitlist_position:
            self.waitlist_position = self.session.get_next_waitlist_position()
        elif self.status != 'waitlisted':
            self.waitlist_position = None
        
        super().save(*args, **kwargs)
        
        # Update session registration count whenever status changes
        self.session.update_registration_count()
        
        # Update waitlist positions if this registration changed status
        if self.status == 'waitlisted' or 'status' in kwargs.get('update_fields', []):
            self.session.update_waitlist_positions()
    
    @property
    def is_promotion_expired(self):
        """Check if promotion confirmation has expired"""
        if not self.promotion_expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.promotion_expires_at and self.status == 'registered'
    
    def confirm_promotion(self):
        """Confirm a waitlist promotion"""
        if self.promoted_at and self.promotion_expires_at:
            promotion = self.promotions.filter(
                expired=False,
                confirmed_at__isnull=True
            ).first()
            
            if promotion:
                from django.utils import timezone
                promotion.confirmed_at = timezone.now()
                promotion.save()
                
                # Update registration status to confirmed
                self.status = 'registered'
                self.promotion_expires_at = None
                self.save(update_fields=['status', 'promotion_expires_at'])


class WaitlistPromotion(models.Model):
    """Audit trail for waitlist promotions"""
    REASON_CHOICES = [
        ('capacity_increase', 'Session capacity increased'),
        ('manual_promotion', 'Manual promotion by instructor'),
        ('cancellation', 'Student cancellation opened spot'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(WorkshopRegistration, on_delete=models.CASCADE, related_name='promotions')
    promoted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who triggered promotion")
    promoted_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    expires_at = models.DateTimeField(help_text="Deadline for student to confirm registration")
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When student confirmed the promotion")
    expired = models.BooleanField(default=False, help_text="Whether promotion expired unconfirmed")
    
    class Meta:
        ordering = ['-promoted_at']
        indexes = [
            models.Index(fields=['registration', 'promoted_at']),
            models.Index(fields=['expires_at', 'expired']),
        ]
    
    def __str__(self):
        return f"Promotion: {self.registration.student.username} - {self.registration.session.workshop.title}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at and not self.confirmed_at


class WorkshopMaterial(models.Model):
    """Resources and materials for workshops"""
    TYPE_CHOICES = [
        ('slides', 'Presentation Slides'),
        ('handout', 'Handout/Worksheet'),
        ('resource', 'Additional Resource'),
        ('recording', 'Session Recording'),
        ('transcript', 'Transcript'),
        ('code', 'Code Examples'),
        ('link', 'External Link'),
    ]
    
    ACCESS_CHOICES = [
        ('pre', 'Before Session'),
        ('during', 'During Session'),
        ('post', 'After Session'),
        ('always', 'Always Available'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='materials')
    session = models.ForeignKey(WorkshopSession, on_delete=models.CASCADE, null=True, blank=True, related_name='materials')
    
    # Content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # File or Link
    file = models.FileField(upload_to='workshops/materials/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    
    # Access Control
    access_timing = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='always')
    is_downloadable = models.BooleanField(default=True)
    requires_registration = models.BooleanField(default=True)
    
    # Organization
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
        indexes = [
            models.Index(fields=['workshop', 'access_timing']),
            models.Index(fields=['session', 'access_timing']),
        ]
    
    def __str__(self):
        session_info = f" ({self.session.start_datetime.strftime('%Y-%m-%d')})" if self.session else ""
        return f"{self.workshop.title} - {self.title}{session_info}"
    
    @property
    def file_extension(self):
        """Get file extension"""
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return ''
    
    @property
    def file_size_display(self):
        """Display file size in human-readable format"""
        if self.file:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            else:
                return f"{size / (1024 * 1024 * 1024):.1f} GB"
        return 'Unknown size'
    
    def can_be_accessed_by_registration(self, registration):
        """Check if a registration can access this material"""
        if not self.requires_registration:
            return True
            
        if not registration or registration.status not in ['registered', 'attended']:
            return False
        
        # If material is session-specific, check session timing
        if self.session:
            now = timezone.now()
            session_start = self.session.start_datetime
            session_end = self.session.end_datetime
            
            access_rules = {
                'always': True,
                'pre': now < session_start,
                'during': session_start <= now <= session_end,
                'post': now > session_end,
            }
            
            return access_rules.get(self.access_timing, False)
        
        # Workshop-level materials are generally always accessible to registered users
        return True
    
    @property
    def is_session_specific(self):
        """Check if this material is attached to a specific session"""
        return self.session is not None


class WorkshopInterest(models.Model):
    """Track user interest in workshops that don't have available sessions"""
    TIMING_PREFERENCES = [
        ('weekday_morning', 'Weekday Mornings'),
        ('weekday_afternoon', 'Weekday Afternoons'),
        ('weekday_evening', 'Weekday Evenings'),
        ('weekend_morning', 'Weekend Mornings'),
        ('weekend_afternoon', 'Weekend Afternoons'),
        ('weekend_evening', 'Weekend Evenings'),
        ('flexible', 'Flexible'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='interest_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshop_interests')
    
    # Contact Information
    email = models.EmailField(help_text="We'll notify you when sessions become available")
    
    # Preferences
    preferred_timing = models.CharField(
        max_length=20, 
        choices=TIMING_PREFERENCES, 
        default='flexible',
        help_text="When would you prefer to attend?"
    )
    
    # Additional Details
    experience_level = models.CharField(
        max_length=20, 
        choices=Workshop.DIFFICULTY_CHOICES, 
        blank=True,
        help_text="Your current experience level with this topic"
    )
    
    special_requests = models.TextField(
        blank=True,
        help_text="Any specific topics you'd like covered or accessibility needs"
    )
    
    # Notification Preferences
    notify_immediately = models.BooleanField(
        default=True,
        help_text="Notify me as soon as sessions are scheduled"
    )
    
    notify_summary = models.BooleanField(
        default=False,
        help_text="Send me monthly summaries of new workshop opportunities"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    has_been_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['workshop', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workshop', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['has_been_notified', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name_or_username()} interested in {self.workshop.title}"
    
    @property
    def formatted_timing(self):
        """Return human-readable timing preference"""
        return dict(self.TIMING_PREFERENCES).get(self.preferred_timing, 'Flexible')


class WorkshopCartItem(models.Model):
    """
    Workshop session in shopping cart.
    Uses the unified Cart model from private_teaching app.
    """
    cart = models.ForeignKey(
        'private_teaching.Cart',
        on_delete=models.CASCADE,
        related_name='workshop_items',
        help_text="Cart this workshop session belongs to"
    )
    session = models.ForeignKey(
        WorkshopSession,
        on_delete=models.CASCADE,
        related_name='cart_items',
        help_text="Workshop session to purchase"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price at time of adding to cart"
    )

    # Optional fields for checkout (ultra-minimal - most come from user account)
    notes = models.TextField(
        blank=True,
        help_text="Optional notes for instructor"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.CASCADE,
        related_name='workshop_cart_items',
        null=True,
        blank=True,
        help_text="If registering a child, link to their child profile"
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at']
        verbose_name = 'Workshop Cart Item'
        verbose_name_plural = 'Workshop Cart Items'
        unique_together = ['cart', 'session']  # Prevent duplicates
        indexes = [
            models.Index(fields=['cart', 'added_at']),
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"{self.session.workshop.title} - {self.session.start_datetime.strftime('%Y-%m-%d %H:%M')}"

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.price

    @property
    def is_child_registration(self):
        """Check if this is a registration for a child"""
        return self.child_profile is not None
