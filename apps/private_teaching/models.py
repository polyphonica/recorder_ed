from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings as django_settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

from apps.core.models import PayableModel, BaseCancellationRequest
from lessons.models import Lesson

User = get_user_model()


class Subject(models.Model):
    """Model for teacher-specific lesson subjects with pricing"""
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subjects',
        help_text="Teacher who offers this subject"
    )
    subject = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    base_price_60min = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=50.00,
        help_text="Base price for 60-minute lesson"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this subject is currently offered"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order in which subjects are displayed (lower numbers appear first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'subject']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        unique_together = ['teacher', 'subject']

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        return f"{self.subject} - {teacher_name} (£{self.base_price_60min}/60min)"


class LessonRequest(PayableModel):
    """
    Container for lesson requests with message thread.

    Supports both adult students and children (under 18).
    - For adults: student field is populated, child_profile is None
    - For children: student field = guardian, child_profile = child

    Inherits payment and child profile fields from PayableModel.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_requests',
        help_text="For adults: the student. For children: the guardian/parent."
    )

    # Child profile field inherited from PayableModel:
    # - child_profile (ForeignKey to ChildProfile)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lesson Request'
        verbose_name_plural = 'Lesson Requests'
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['child_profile', 'created_at']),
        ]

    def __str__(self):
        # PERFORMANCE FIX: Removed lessons.count() call that triggered a query on every __str__
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        guardian_info = f" (Guardian: {self.student.get_full_name()})" if self.child_profile else ""
        return f"{student_name}{guardian_info} - {self.created_at.strftime('%Y-%m-%d')}"

    def get_absolute_url(self):
        return reverse('private_teaching:my_requests')

    @property
    def teacher(self):
        """Get teacher from first lesson's subject"""
        first_lesson = self.lessons.first()
        return first_lesson.teacher if first_lesson else None

    # Child profile properties inherited from PayableModel:
    # - student_name
    # - guardian
    # - is_for_child (replaces is_child_request)

    @property
    def is_child_request(self):
        """Alias for is_for_child for backward compatibility"""
        return self.is_for_child

    @property
    def student_display_name(self):
        """
        Alias for student_name property from PayableModel.
        Returns the display name for the student (child or adult).

        - For child lessons: returns child_profile.full_name
        - For adult lessons: returns student.get_full_name()
        """
        return self.student_name

    @property
    def is_child_lesson(self):
        """
        Alias for is_for_child property from PayableModel.
        Check if this lesson request is for a child (under 18).
        """
        return self.is_for_child

    @property
    def guardian_name(self):
        """
        Returns guardian's name if this is a child lesson, None otherwise.
        """
        if self.guardian:
            return self.guardian.get_full_name() or self.guardian.username
        return None

    @property
    def subject_display(self):
        """Get subject(s) for display - returns comma-separated list of unique subjects"""
        subjects = self.lessons.select_related('subject').values_list('subject__subject', flat=True).distinct()
        return ', '.join(subjects) if subjects else 'No subjects'

    @property
    def status(self):
        """Get overall status based on lesson statuses"""
        lessons = self.lessons.all()
        if not lessons:
            return 'draft'

        statuses = lessons.values_list('approved_status', flat=True)
        if all(s == Lesson.ApprovalStatus.ACCEPTED for s in statuses):
            return 'accepted'
        elif all(s == Lesson.ApprovalStatus.REJECTED for s in statuses):
            return 'rejected'
        elif any(s == Lesson.ApprovalStatus.PENDING for s in statuses):
            return 'pending'
        return 'mixed'


class LessonRequestMessage(models.Model):
    """Message thread for lesson request negotiations"""
    lesson_request = models.ForeignKey(
        LessonRequest,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="The lesson request this message belongs to"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="User who wrote this message (student or teacher)"
    )
    message = models.TextField(help_text="Message content")
    created_at = models.DateTimeField(auto_now_add=True)

    # Read tracking (to match BaseMessage structure for future migration)
    is_read = models.BooleanField(default=False, help_text="Whether this message has been read")
    read_at = models.DateTimeField(null=True, blank=True, help_text="When this message was read")

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Lesson Request Message'
        verbose_name_plural = 'Lesson Request Messages'
        # PERFORMANCE FIX: Add index for message thread queries
        indexes = [
            models.Index(fields=['lesson_request', 'created_at']),
        ]

    def __str__(self):
        return f"{self.author.get_full_name()}: {self.message[:50]}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class CartItem(models.Model):
    """Individual lesson in shopping cart"""
    cart = models.ForeignKey(
        'core.Cart',
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Cart this item belongs to"
    )
    lesson = models.ForeignKey(
        'lessons.Lesson',  # String reference to avoid circular import
        on_delete=models.CASCADE,
        related_name='cart_items',
        help_text="Lesson to purchase"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Price at time of adding to cart"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'lesson']  # Prevent duplicates
        # PERFORMANCE FIX: Add index for cart item queries
        indexes = [
            models.Index(fields=['cart', 'added_at']),
        ]

    def __str__(self):
        return f"{self.lesson.subject} - {self.lesson.lesson_date}"

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.price


class Order(models.Model):
    """Completed lesson purchase order"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Payment Pending'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_orders',
        help_text="Student who made the purchase"
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique order identifier"
    )
    total_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Total order amount"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Payment processing status"
    )
    payment_method = models.CharField(
        max_length=50,
        default='stripe',
        help_text="Payment method used"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe PaymentIntent ID"
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Checkout Session ID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was completed"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        # PERFORMANCE FIX: Add index for order history queries
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['payment_status', '-created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.student.get_full_name()}"
    
    def generate_order_number(self):
        """Generate unique order number"""
        # SECURITY FIX: Use secrets module instead of random for cryptographically secure tokens
        import secrets
        from django.utils import timezone

        date_str = timezone.now().strftime('%Y%m%d')
        # Use secrets.token_hex for cryptographically secure random string
        random_str = secrets.token_hex(3).upper()  # 6 characters hex
        return f"PT{date_str}{random_str}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Individual lesson in a completed order"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Order this item belongs to"
    )
    lesson = models.OneToOneField(
        'lessons.Lesson',  # String reference to avoid circular import
        on_delete=models.CASCADE,
        related_name='order_item',
        help_text="Lesson purchased"
    )
    price_paid = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Price paid for this lesson"
    )

    class Meta:
        ordering = ['order__created_at']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        # PERFORMANCE FIX: Add index for order item queries
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f"{self.lesson.subject} - {self.order.order_number}"


class TeacherStudentApplication(models.Model):
    """
    Application for students to study with a specific teacher.
    Students must be accepted before they can request lessons.
    """
    APPLICATION_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('waitlist', 'On Waiting List'),
        ('declined', 'Declined'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who is applying
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='private_teaching_applications',
        help_text="Guardian/parent or adult student applying"
    )

    # If applying for a child
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        related_name='private_teaching_applications',
        null=True,
        blank=True,
        help_text="If applying for a child, link to their child profile"
    )

    # Which teacher
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_applications',
        help_text="Teacher being applied to"
    )

    # Status and notes
    status = models.CharField(
        max_length=20,
        choices=APPLICATION_STATUS_CHOICES,
        default='pending',
        help_text="Current status of the application"
    )

    teacher_notes = models.TextField(
        blank=True,
        help_text="Private notes from teacher (reason for decline, waiting list notes, etc.)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Teacher-Student Application'
        verbose_name_plural = 'Teacher-Student Applications'
        unique_together = [['applicant', 'child_profile', 'teacher']]
        indexes = [
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['applicant', 'status']),
        ]

    def __str__(self):
        student_name = self.student_name
        return f"{student_name} → {self.teacher.get_full_name()} ({self.get_status_display()})"

    @property
    def student_name(self):
        """Return the name of the actual student (child or adult)"""
        if self.child_profile:
            return self.child_profile.full_name
        return self.applicant.get_full_name() or self.applicant.username

    @property
    def is_child_application(self):
        """Check if this is an application for a child"""
        return self.child_profile is not None

    def get_absolute_url(self):
        return reverse('private_teaching:application_detail', kwargs={'application_id': self.id})


class ApplicationMessage(models.Model):
    """Messages between teacher and student/guardian regarding application"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    application = models.ForeignKey(
        TeacherStudentApplication,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="The application this message belongs to"
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="User who wrote this message (applicant or teacher)"
    )

    message = models.TextField(help_text="Message content")

    created_at = models.DateTimeField(auto_now_add=True)

    # Track if message has been read
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Application Message'
        verbose_name_plural = 'Application Messages'
        # PERFORMANCE FIX: Add index for application message queries
        indexes = [
            models.Index(fields=['application', 'created_at']),
        ]

    def __str__(self):
        return f"{self.author.get_full_name()}: {self.message[:50]}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class PrivateLessonTermsAndConditions(models.Model):
    """Platform-wide Terms and Conditions for private lesson bookings"""
    version = models.IntegerField(unique=True, help_text="Version number (e.g., 1, 2, 3)")
    content = models.TextField(help_text="Full Terms and Conditions text (supports Markdown)")
    effective_date = models.DateTimeField(help_text="When these terms become effective")
    is_current = models.BooleanField(default=False, help_text="Is this the current active version?")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_private_lesson_terms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Private Lesson Terms and Conditions'
        verbose_name_plural = 'Private Lesson Terms and Conditions'
        ordering = ['-version']

    def save(self, *args, **kwargs):
        """Ensure only one version is marked as current"""
        if self.is_current:
            PrivateLessonTermsAndConditions.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        status = "CURRENT" if self.is_current else "archived"
        return f"Private Lesson Terms v{self.version} ({status})"


class PrivateLessonTermsAcceptance(models.Model):
    """Tracks when students accept Private Lesson Terms and Conditions"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='private_lesson_terms_acceptances')
    # Link to the actual lesson booking (will be populated when lesson is booked)
    # Note: Using string reference to avoid circular import issues
    lesson = models.OneToOneField('lessons.Lesson', on_delete=models.CASCADE,
                                   related_name='terms_acceptance', null=True, blank=True,
                                   help_text="The lesson this acceptance is associated with")
    terms_version = models.ForeignKey(PrivateLessonTermsAndConditions, on_delete=models.PROTECT,
                                     related_name='acceptances')
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, help_text="Browser user agent string")

    class Meta:
        verbose_name = 'Private Lesson Terms Acceptance'
        verbose_name_plural = 'Private Lesson Terms Acceptances'
        ordering = ['-accepted_at']

    def __str__(self):
        lesson_info = f" for lesson {self.lesson.id}" if self.lesson else ""
        return f"{self.student.username} accepted v{self.terms_version.version}{lesson_info}"


class LessonCancellationRequest(BaseCancellationRequest):
    """Track student cancellation requests for private lessons"""

    # Request Type Choices
    CANCEL_WITH_REFUND = 'cancel_refund'
    RESCHEDULE = 'reschedule'

    REQUEST_TYPE_CHOICES = [
        (CANCEL_WITH_REFUND, 'Cancel with Refund'),
        (RESCHEDULE, 'Reschedule Lesson'),
    ]

    # Cancellation Reason Choices
    SCHEDULE_CONFLICT = 'schedule_conflict'
    ILLNESS = 'illness'
    EMERGENCY = 'emergency'
    NO_LONGER_NEEDED = 'no_longer_needed'
    DISCONTINUING = 'discontinuing'
    OTHER = 'other'

    REASON_CHOICES = [
        (SCHEDULE_CONFLICT, 'Schedule Conflict'),
        (ILLNESS, 'Illness'),
        (EMERGENCY, 'Family Emergency'),
        (NO_LONGER_NEEDED, 'No Longer Need Lessons'),
        (DISCONTINUING, 'Discontinuing All Lessons'),
        (OTHER, 'Other'),
    ]

    # Who initiated this request
    INITIATED_BY_STUDENT = 'student'
    INITIATED_BY_TEACHER = 'teacher'
    INITIATED_BY_CHOICES = [
        (INITIATED_BY_STUDENT, 'Student'),
        (INITIATED_BY_TEACHER, 'Teacher'),
    ]

    # Core Fields (domain-specific)
    lesson = models.ForeignKey('lessons.Lesson', on_delete=models.CASCADE, related_name='cancellation_requests')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_cancellation_requests')
    initiated_by = models.CharField(
        max_length=10, choices=INITIATED_BY_CHOICES, default=INITIATED_BY_STUDENT,
        help_text="Who initiated this request"
    )

    # Request Details (domain-specific)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default=CANCEL_WITH_REFUND)
    cancellation_reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Optional: Student can provide a reason, but it's not required"
    )
    # Note: 'reason' field inherited from BaseCancellationRequest serves as student_message

    # Timing Information (domain-specific)
    hours_before_lesson = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Hours between request and lesson start time"
    )
    is_within_policy = models.BooleanField(
        default=True,
        help_text="True if requested 48+ hours before lesson (eligible for refund)"
    )

    # Status and Resolution (domain-specific fields for teacher workflow)
    teacher_response = models.TextField(blank=True, help_text="Teacher's response to the request")
    teacher_responded_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Refund Details (domain-specific - includes platform fee)
    platform_fee_retained = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Platform fee that is non-refundable"
    )

    # Reschedule Details (domain-specific)
    proposed_new_date = models.DateField(null=True, blank=True)
    proposed_new_time = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Lesson Cancellation Request'
        verbose_name_plural = 'Lesson Cancellation Requests'
        ordering = ['-created_at']
        # PERFORMANCE FIX: Add indexes for cancellation request queries
        indexes = [
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['lesson']),
        ]

    def __str__(self):
        return f"{self.get_request_type_display()} - {self.lesson} by {self.student.username}"

    @property
    def requested_at(self):
        """Alias for created_at for backward compatibility"""
        return self.created_at

    @property
    def student_message(self):
        """Alias for reason field for backward compatibility"""
        return self.reason

    @student_message.setter
    def student_message(self, value):
        """Allow setting student_message which sets reason"""
        self.reason = value

    def save(self, *args, **kwargs):
        """Calculate hours before lesson and policy compliance on first save"""
        if not self.pk:  # Only on creation
            from django.utils import timezone
            from datetime import datetime, timedelta

            # Combine lesson date and time
            lesson_datetime = datetime.combine(
                self.lesson.lesson_date,
                self.lesson.lesson_time
            )
            lesson_datetime = timezone.make_aware(lesson_datetime)

            # Calculate hours until lesson
            time_until_lesson = lesson_datetime - timezone.now()
            self.hours_before_lesson = time_until_lesson.total_seconds() / 3600

            # Check if within cancellation policy
            self.is_within_policy = self.hours_before_lesson >= django_settings.PRIVATE_LESSON_CANCELLATION_HOURS

        super().save(*args, **kwargs)

    def calculate_refund_eligibility(self):
        """
        Calculate if student is eligible for refund based on cancellation notice policy.
        Updates is_eligible_for_refund and refund_amount fields.

        Refund policy for private lessons:
        - Must provide advance notice (hours configured in settings.PRIVATE_LESSON_CANCELLATION_HOURS)
        - Lesson must have been paid
        - Must be requesting cancellation (not reschedule)
        - Request must be within refund window (days configured in settings.PRIVATE_LESSON_REFUND_REQUEST_DAYS)
        - Refund amount = lesson price minus platform fee (configured in settings.PLATFORM_COMMISSION_PERCENTAGE)
        """
        from django.utils import timezone
        from datetime import datetime, timedelta
        from decimal import Decimal

        # Check all eligibility criteria
        eligible = True

        # Must be within 48-hour policy
        if not self.is_within_policy:
            eligible = False

        # Lesson must have been paid
        if self.lesson.payment_status != 'completed':
            eligible = False

        # Must be requesting a cancellation (not just reschedule)
        if self.request_type != self.CANCEL_WITH_REFUND:
            eligible = False

        # Request must be within refund request window
        lesson_datetime = datetime.combine(
            self.lesson.lesson_date,
            self.lesson.lesson_time
        )
        lesson_datetime = timezone.make_aware(lesson_datetime)
        days_since_lesson = (timezone.now() - lesson_datetime).days
        if days_since_lesson > django_settings.PRIVATE_LESSON_REFUND_REQUEST_DAYS:
            eligible = False

        # Set eligibility
        self.is_eligible_for_refund = eligible

        if eligible:
            # Calculate refund: lesson price minus 10% platform fee
            lesson_price = self.lesson.price or Decimal('0.00')
            platform_fee_rate = Decimal('0.10')
            self.platform_fee_retained = lesson_price * platform_fee_rate
            self.refund_amount = lesson_price - self.platform_fee_retained
        else:
            self.refund_amount = None
            self.platform_fee_retained = None

        return self.is_eligible_for_refund

    @property
    def can_receive_refund(self):
        """
        Determine if this cancellation is eligible for a refund.
        Uses calculate_refund_eligibility() to avoid code duplication.
        """
        # Use the existing calculation method to determine eligibility
        return self.calculate_refund_eligibility()




# Quiz models moved to apps.quizzes

class StudentPieceAssignment(models.Model):
    """
    Assigns a playalong piece directly to a student (independent of any lesson).
    Teachers manage these from the student progress page.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    piece = models.ForeignKey(
        'audioplayer.Piece',
        on_delete=models.CASCADE,
        related_name='student_assignments'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_pieces'
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_pieces',
        help_text="Optional: Specific child this piece is for"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='piece_assignments_given'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    instructions = models.TextField(blank=True, help_text="Practice instructions for this piece")
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_at']
        unique_together = ['student', 'piece', 'teacher']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['teacher', '-assigned_at']),
        ]

    def __str__(self):
        student_name = self.student.get_full_name() or self.student.username
        return f"{self.piece.title} → {student_name}"


class StudentCollectionAssignment(models.Model):
    """
    Assigns a playalong collection directly to a student (independent of any lesson).
    Teachers manage these from the student progress page.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(
        'audioplayer.PieceCollection',
        on_delete=models.CASCADE,
        related_name='student_assignments'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_collections'
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_collections',
        help_text="Optional: Specific child this collection is for"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='collection_assignments_given'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    instructions = models.TextField(blank=True, help_text="Practice instructions for this collection")
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_at']
        unique_together = ['student', 'collection', 'teacher']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['teacher', '-assigned_at']),
        ]

    def __str__(self):
        student_name = self.student.get_full_name() or self.student.username
        return f"{self.collection.title} → {student_name}"
