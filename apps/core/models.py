import uuid

from django.db import models
from django.conf import settings


class PayableModel(models.Model):
    """
    Abstract base model for entities that require payment processing

    Provides common payment-related fields for workshops, courses, and other paid services.
    Includes Stripe integration fields, payment status tracking, and child profile support.

    Child Profile Support:
    - For adult students: student field is populated, child_profile is None
    - For children (under 18): student field = guardian, child_profile = child
    """

    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Pending Payment'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
    ]

    # Student/Guardian field (defined in subclass)
    # student = ForeignKey to User (must be defined in subclass)

    # Child profile support (for students under 18)
    # Note: Use related_name='%(class)s_set' to avoid clashes between models
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        null=True,
        blank=True,
        help_text="If for a child, link to their child profile"
    )

    # Payment fields
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='not_required',
        help_text="Current payment status"
    )
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Amount paid or to be paid"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe PaymentIntent ID for tracking"
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Checkout Session ID"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when payment was completed"
    )

    class Meta:
        abstract = True

    # Payment-related properties
    @property
    def is_paid(self):
        """Check if payment has been completed"""
        return self.payment_status == 'completed'

    @property
    def is_payment_pending(self):
        """Check if payment is pending"""
        return self.payment_status == 'pending'

    @property
    def requires_payment(self):
        """Check if payment is required"""
        return self.payment_status != 'not_required'

    # Child profile properties
    @property
    def student_name(self):
        """Return the name of the actual student (child or adult)"""
        if self.child_profile:
            return self.child_profile.full_name
        # Access student field from subclass
        student = getattr(self, 'student', None)
        if student:
            return student.get_full_name() or student.username
        return "Unknown"

    @property
    def guardian(self):
        """Return guardian user if this is for a child, None otherwise"""
        if self.child_profile:
            return getattr(self, 'student', None)
        return None

    @property
    def is_for_child(self):
        """Check if this is for a child (under 18)"""
        return self.child_profile is not None


class BaseAttachment(models.Model):
    """
    Abstract base model for file attachments and materials.

    Provides common fields and methods for file management:
    - UUID primary key
    - Title and file fields
    - Ordering support
    - File size calculation
    - Timestamps

    Subclasses should define:
    - Foreign key to the parent object (e.g., lesson, workshop, session)
    - Any additional fields specific to their use case (e.g., file_type, access_timing)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic fields
    title = models.CharField(max_length=200, help_text="Title/name of the attachment")
    file = models.FileField(
        upload_to='attachments/',  # Subclasses should override upload_to
        blank=True,
        null=True,
        help_text="Uploaded file"
    )

    # Organization
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['order', 'title']

    def __str__(self):
        return self.title

    @property
    def file_extension(self):
        """Get file extension from filename"""
        if self.file and self.file.name:
            return self.file.name.split('.')[-1].lower()
        return ''

    @property
    def file_size(self):
        """Get human-readable file size"""
        if self.file:
            try:
                size = self.file.size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} TB"
            except (OSError, ValueError):
                return "Unknown size"
        return "0 B"


class BaseMessage(models.Model):
    """
    Abstract base model for messaging functionality across apps.

    Provides common fields and methods for threaded message systems:
    - Author/sender tracking
    - Message content
    - Timestamp tracking
    - Read/unread status
    - Optional threading support

    Subclasses should define:
    - Foreign key to the parent object (e.g., course, lesson_request, application)
    - Any additional fields specific to their use case
    """

    # Author field (creator of the message)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_authored',
        help_text="User who wrote this message"
    )

    # Message content
    message = models.TextField(help_text="Message content")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    # Read tracking
    is_read = models.BooleanField(
        default=False,
        help_text="Whether this message has been read"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this message was read"
    )

    class Meta:
        abstract = True
        ordering = ['created_at']

    def __str__(self):
        author_name = self.author.get_full_name() or self.author.username
        return f"{author_name}: {self.message[:50]}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class BaseCancellationRequest(models.Model):
    """
    Abstract base model for cancellation requests across different domains.

    Provides common fields and methods for tracking cancellation workflows:
    - Student and status tracking
    - Refund eligibility and amount calculation
    - Admin review workflow
    - Timestamps

    Subclasses should define:
    - Foreign key to the parent object (e.g., enrollment, lesson)
    - Any domain-specific fields (e.g., hours_before_lesson, reschedule options)
    - Override calculate_refund_eligibility() with domain-specific logic
    """

    # Common status choices
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'

    STATUS_CHOICES = [
        (PENDING, 'Pending Review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (COMPLETED, 'Completed (Refund Processed)'),
    ]

    # Core fields
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_requests',
        help_text="Student requesting cancellation"
    )

    # Cancellation details
    reason = models.TextField(
        blank=True,
        default='',
        help_text="Optional: Student's explanation for cancellation/reschedule"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    # Refund eligibility
    is_eligible_for_refund = models.BooleanField(
        default=False,
        help_text="Is this cancellation eligible for refund?"
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount to be refunded"
    )

    # Admin review
    admin_notes = models.TextField(blank=True, help_text="Admin notes/response")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_reviewed',
        help_text="Admin who reviewed this request"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Refund processing
    refund_processed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def calculate_refund_eligibility(self):
        """
        Calculate if student is eligible for refund.

        This method should be overridden in subclasses to implement
        domain-specific refund policies (e.g., 7-day trial, 48-hour notice).

        Should update:
        - self.is_eligible_for_refund
        - self.refund_amount

        Returns:
            bool: True if eligible for refund
        """
        raise NotImplementedError("Subclasses must implement calculate_refund_eligibility()")

    def approve(self, admin_user, notes=''):
        """Approve the cancellation request"""
        from django.utils import timezone
        self.status = self.APPROVED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save()

    def reject(self, admin_user, notes=''):
        """Reject the cancellation request"""
        from django.utils import timezone
        self.status = self.REJECTED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save()

    def mark_refund_processed(self):
        """Mark the refund as processed"""
        from django.utils import timezone
        self.status = self.COMPLETED
        self.refund_processed_at = timezone.now()
        self.save()
