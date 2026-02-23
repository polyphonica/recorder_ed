from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings as django_settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field
from decimal import Decimal
import uuid

from apps.core.models import PayableModel, BaseCancellationRequest

User = get_user_model()

# NOTE: Lesson model is imported at runtime to avoid circular import
# from lessons.models import Lesson


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

        from lessons.models import Lesson  # local import to avoid circular import
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


class Cart(models.Model):
    """Shopping cart for lesson purchases"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_cart',
        help_text="User who owns this cart"
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Session key for anonymous users"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'

    def __str__(self):
        return f"Cart for {self.user.get_full_name() if self.user else 'Anonymous'}"

    @property
    def total_amount(self):
        """Calculate total cart amount"""
        return sum(item.total_price for item in self.items.all())

    @property
    def item_count(self):
        """Get total number of items in cart"""
        return self.items.count()


class CartItem(models.Model):
    """Individual lesson in shopping cart"""
    cart = models.ForeignKey(
        Cart,
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


class ExamBoard(models.Model):
    """Examination boards that provide graded music exams"""

    ABRSM = 'abrsm'
    TRINITY = 'trinity'
    MTB = 'mtb'

    BOARD_CHOICES = [
        (ABRSM, 'ABRSM (Associated Board of the Royal Schools of Music)'),
        (TRINITY, 'Trinity College London'),
        (MTB, 'Music Teachers\' Board'),
    ]

    name = models.CharField(
        max_length=50,
        choices=BOARD_CHOICES,
        unique=True,
        help_text="Examination board name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the examination board"
    )
    website = models.URLField(
        blank=True,
        help_text="Official website URL"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this board is currently available for selection"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Examination Board'
        verbose_name_plural = 'Examination Boards'

    def __str__(self):
        return self.get_name_display()


class ExamRegistration(PayableModel):
    """
    Registration for a music examination.

    Supports both adult students and children (under 18).
    - For adults: student field is populated, child_profile is None
    - For children: student field = guardian, child_profile = child

    Inherits payment and child profile fields from PayableModel.
    """

    PRACTICAL = 'practical'
    PERFORMANCE = 'performance'
    THEORY = 'theory'

    GRADE_TYPE_CHOICES = [
        (PRACTICAL, 'Practical Grade'),
        (PERFORMANCE, 'Performance Grade'),
        (THEORY, 'Music Theory'),
    ]

    REGISTERED = 'registered'
    SUBMITTED = 'submitted'
    RESULTS_RECEIVED = 'results_received'

    STATUS_CHOICES = [
        (REGISTERED, 'Registered'),
        (SUBMITTED, 'Exam Submitted'),
        (RESULTS_RECEIVED, 'Results Received'),
    ]

    PASS = 'pass'
    MERIT = 'merit'
    DISTINCTION = 'distinction'
    FAIL = 'fail'

    GRADE_ACHIEVED_CHOICES = [
        (PASS, 'Pass'),
        (MERIT, 'Merit'),
        (DISTINCTION, 'Distinction'),
        (FAIL, 'Fail'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_registrations',
        help_text="For adults: the student. For children: the guardian/parent."
    )
    # child_profile inherited from PayableModel

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_exam_registrations',
        help_text="Teacher registering the student for the exam"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exam_registrations',
        help_text="Subject/instrument for the exam"
    )

    exam_board = models.ForeignKey(
        ExamBoard,
        on_delete=models.PROTECT,
        related_name='exam_registrations',
        help_text="Examination board"
    )

    # Exam details
    grade_type = models.CharField(
        max_length=20,
        choices=GRADE_TYPE_CHOICES,
        help_text="Type of exam (Practical, Performance, or Theory)"
    )

    grade_level = models.PositiveIntegerField(
        help_text="Grade level (1-8 for Practical/Performance, 1-6 for Theory)"
    )

    exam_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the exam (can be set later for flexible submissions)"
    )

    submission_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for submitting recordings/videos"
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Registration number from the exam board"
    )

    venue = models.CharField(
        max_length=200,
        blank=True,
        help_text="Exam venue or submission method (e.g., 'Video submission', 'London Centre')"
    )

    # Technical requirements
    scales = models.TextField(
        blank=True,
        help_text="Required scales (e.g., 'C major, A minor melodic, chromatic')"
    )

    arpeggios = models.TextField(
        blank=True,
        help_text="Required arpeggios (e.g., 'C major, A minor')"
    )

    sight_reading = models.TextField(
        blank=True,
        help_text="Sight reading requirements or notes"
    )

    aural_tests = models.TextField(
        blank=True,
        help_text="Aural test requirements or notes"
    )

    # Status and results
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=REGISTERED,
        help_text="Current exam status"
    )

    mark_achieved = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Numerical mark achieved (e.g., 85 out of 100)"
    )

    grade_achieved = models.CharField(
        max_length=20,
        choices=GRADE_ACHIEVED_CHOICES,
        blank=True,
        help_text="Grade achieved (Pass, Merit, Distinction, Fail)"
    )

    examiner_comments = models.TextField(
        blank=True,
        help_text="Comments from the examiner"
    )

    certificate_received_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when certificate was received"
    )

    # Payment (fee_amount field)
    fee_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Exam registration fee set by teacher"
    )

    # Notes and timestamps
    teacher_notes = models.TextField(
        blank=True,
        help_text="Private teacher notes about this exam"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-exam_date', '-created_at']
        verbose_name = 'Exam Registration'
        verbose_name_plural = 'Exam Registrations'
        indexes = [
            models.Index(fields=['teacher', 'exam_date']),
            models.Index(fields=['student', 'exam_date']),
            models.Index(fields=['exam_board', 'grade_type', 'grade_level']),
        ]

    def __str__(self):
        student_name = self.student_name  # From PayableModel
        grade_display = f"{self.get_grade_type_display()} Grade {self.grade_level}"
        return f"{student_name} - {self.exam_board} {grade_display}"

    def clean(self):
        """Validate grade level based on grade type"""
        super().clean()

        if self.grade_type == self.THEORY:
            if self.grade_level < 1 or self.grade_level > 6:
                raise ValidationError({
                    'grade_level': 'Theory grades must be between 1 and 6'
                })
        else:  # Practical or Performance
            if self.grade_level < 1 or self.grade_level > 8:
                raise ValidationError({
                    'grade_level': 'Practical and Performance grades must be between 1 and 8'
                })

    def get_absolute_url(self):
        return reverse('private_teaching:exam_detail', kwargs={'pk': self.id})

    @property
    def display_name(self):
        """Full display name for the exam"""
        return f"{self.exam_board} {self.get_grade_type_display()} Grade {self.grade_level}"

    @property
    def has_results(self):
        """Check if results have been entered"""
        return self.status == self.RESULTS_RECEIVED and (
            self.mark_achieved is not None or self.grade_achieved
        )


class ExamPiece(models.Model):
    """
    Individual piece selected for an exam.
    Number of pieces varies by board and grade.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    exam_registration = models.ForeignKey(
        ExamRegistration,
        on_delete=models.CASCADE,
        related_name='pieces',
        help_text="Exam registration this piece belongs to"
    )

    piece_number = models.PositiveIntegerField(
        help_text="Piece number in the exam (1, 2, 3, 4, etc.)"
    )

    title = models.CharField(
        max_length=200,
        help_text="Title of the piece"
    )

    composer = models.CharField(
        max_length=200,
        help_text="Composer name"
    )

    syllabus_list = models.CharField(
        max_length=50,
        blank=True,
        help_text="Syllabus list (e.g., 'A', 'B', 'C', 'Own Choice')"
    )

    playalong_piece = models.ForeignKey(
        'audioplayer.Piece',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_pieces',
        help_text="Link to playalong piece for practice"
    )

    teacher_notes = models.TextField(
        blank=True,
        help_text="Teacher notes about practice progress or readiness"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['piece_number']
        verbose_name = 'Exam Piece'
        verbose_name_plural = 'Exam Pieces'
        unique_together = ['exam_registration', 'piece_number']
        # PERFORMANCE FIX: Add index for exam piece queries
        indexes = [
            models.Index(fields=['exam_registration', 'piece_number']),
        ]

    def __str__(self):
        return f"Piece {self.piece_number}: {self.title} by {self.composer}"


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


class PracticeEntry(models.Model):
    """
    Practice diary entries for private lesson students.
    Helps students track practice and teachers monitor progress.
    Especially valuable for exam preparation and recital preparation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='practice_entries',
        help_text="Student who practiced (adult or guardian for child)"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='practice_entries',
        help_text="If practicing for a child's lessons"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_practice_entries',
        help_text="Teacher who can view this practice entry"
    )
    lesson_request = models.ForeignKey(
        'LessonRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='practice_entries',
        help_text="Associated lesson request/relationship"
    )

    # Practice Details
    practice_date = models.DateField(
        help_text="Date of practice session"
    )
    duration_minutes = models.PositiveIntegerField(
        help_text="How long practiced (in minutes)"
    )

    # What was practiced
    pieces_practiced = models.TextField(
        blank=True,
        help_text="Pieces/songs worked on (e.g., 'Sonata in F, Scales: G Major, A Minor')"
    )
    exercises_practiced = models.TextField(
        blank=True,
        help_text="Technical exercises (e.g., 'Long tones, Tonguing exercises')"
    )

    # Reflections
    focus_areas = models.TextField(
        blank=True,
        help_text="What you focused on (e.g., 'Worked on tricky section bars 12-16')"
    )
    struggles = models.TextField(
        blank=True,
        help_text="Difficulties encountered (optional)"
    )
    achievements = models.TextField(
        blank=True,
        help_text="Breakthroughs or improvements (optional)"
    )

    # Optional ratings
    enjoyment_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, '1 - Not enjoyable'), (2, '2'), (3, '3'), (4, '4'), (5, '5 - Very enjoyable')],
        help_text="How enjoyable was this practice session?"
    )

    # Exam/Performance preparation flag
    preparing_for_exam = models.BooleanField(
        default=False,
        help_text="Check if practicing for an upcoming exam"
    )
    preparing_for_performance = models.BooleanField(
        default=False,
        help_text="Check if practicing for a recital or performance"
    )

    # Teacher interaction
    teacher_comment = models.TextField(
        blank=True,
        help_text="Teacher's comment on this practice session (optional)"
    )
    teacher_viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When teacher viewed this entry"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-practice_date', '-created_at']
        verbose_name = 'Practice Entry'
        verbose_name_plural = 'Practice Entries'
        indexes = [
            models.Index(fields=['student', '-practice_date']),
            models.Index(fields=['teacher', '-practice_date']),
        ]

    def __str__(self):
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        return f"{student_name} - {self.practice_date} ({self.duration_minutes} min)"

    @property
    def practicing_student_name(self):
        """Return the name of who actually practiced"""
        if self.child_profile:
            return self.child_profile.full_name
        return self.student.get_full_name() or self.student.username

    @property
    def has_reflections(self):
        """Check if student added any reflections"""
        return bool(self.focus_areas or self.struggles or self.achievements)

    @property
    def preparation_type(self):
        """Return what this practice is preparing for"""
        types = []
        if self.preparing_for_exam:
            types.append('Exam')
        if self.preparing_for_performance:
            types.append('Performance')
        return ', '.join(types) if types else None


# ============================================================================
# Teacher Availability Calendar System Models
# ============================================================================


class TeacherAvailability(models.Model):
    """
    Represents a teacher's recurring weekly availability pattern.
    Example: "Every Monday from 9:00 AM to 12:00 PM I'm available"
    """
    DAY_OF_WEEK_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='availability_slots',
        help_text="Teacher who owns this availability slot"
    )
    day_of_week = models.IntegerField(
        choices=DAY_OF_WEEK_CHOICES,
        help_text="Day of week (0=Monday, 6=Sunday)"
    )
    start_time = models.TimeField(
        help_text="Start time of availability (e.g., 09:00)"
    )
    end_time = models.TimeField(
        help_text="End time of availability (e.g., 17:00)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to temporarily disable this slot"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_teaching_teacher_availability'
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Teacher Availability Slot'
        verbose_name_plural = 'Teacher Availability Slots'
        indexes = [
            models.Index(fields=['teacher', 'day_of_week']),
        ]

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        return f"{teacher_name} - {self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    def clean(self):
        """Validate that end_time is after start_time"""
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")


class AvailabilityException(models.Model):
    """
    Represents exceptions to the recurring availability pattern.
    Used for: vacations, one-time blocks, special available hours
    Example: "On Dec 25, I'm unavailable all day (Christmas)"
    Example: "On Jan 15, I'm available 6 PM - 9 PM (normally closed)"
    """
    EXCEPTION_TYPE_CHOICES = [
        ('block', 'Block Time (Unavailable)'),
        ('available', 'Add Availability (Override)'),
    ]

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='availability_exceptions',
        help_text="Teacher who owns this exception"
    )
    exception_type = models.CharField(
        max_length=20,
        choices=EXCEPTION_TYPE_CHOICES,
        default='block',
        help_text="Type of exception: block unavailable time or add special availability"
    )
    date = models.DateField(
        help_text="Specific date for this exception"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time (leave blank to block entire day)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="End time (leave blank to block entire day)"
    )
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional reason (e.g., 'Christmas Holiday', 'Conference')"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to cancel this exception"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_teaching_availability_exception'
        ordering = ['date', 'start_time']
        verbose_name = 'Availability Exception'
        verbose_name_plural = 'Availability Exceptions'
        indexes = [
            models.Index(fields=['teacher', 'date']),
        ]

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        if self.start_time and self.end_time:
            return f"{teacher_name} - {self.date} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')} ({self.get_exception_type_display()})"
        return f"{teacher_name} - {self.date} All Day ({self.get_exception_type_display()})"

    def clean(self):
        """Validate exception data"""
        # If one time is specified, both must be specified
        if (self.start_time is None) != (self.end_time is None):
            raise ValidationError(
                "Both start_time and end_time must be specified, or both left blank for all-day exception"
            )

        # If times are specified, end must be after start
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")

        # Check for conflicting exceptions when blocking time
        if self.exception_type == 'block':
            # Build queryset for existing exceptions
            existing_exceptions = AvailabilityException.objects.filter(
                teacher=self.teacher,
                date=self.date,
                exception_type='block',
                is_active=True
            )

            # Exclude self if updating
            if self.pk:
                existing_exceptions = existing_exceptions.exclude(pk=self.pk)

            # Check for overlapping block exceptions
            if self.start_time and self.end_time:
                # Check for specific time blocks that overlap
                overlapping = existing_exceptions.filter(
                    start_time__isnull=False,
                    end_time__isnull=False,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                )
                if overlapping.exists():
                    raise ValidationError(
                        f"This time conflicts with an existing block on {self.date}. "
                        f"You already have blocked time that overlaps with this period."
                    )

            # Check for all-day blocks
            all_day_blocks = existing_exceptions.filter(
                start_time__isnull=True,
                end_time__isnull=True
            )
            if all_day_blocks.exists():
                raise ValidationError(
                    f"This day is already blocked all day on {self.date}. "
                    f"Remove the existing all-day block before adding a specific time block."
                )

            # If creating an all-day block, check for any existing blocks
            if not self.start_time and not self.end_time:
                if existing_exceptions.exists():
                    raise ValidationError(
                        f"Cannot create an all-day block on {self.date} because there are already "
                        f"specific time blocks on this day. Remove them first or use a specific time range."
                    )

            # Check if this time is already unavailable in the regular schedule
            if self.start_time and self.end_time:
                # Get the day of week for this date
                day_of_week = self.date.weekday()

                # Check if there's any regular availability for this day/time
                available_slots = TeacherAvailability.objects.filter(
                    teacher=self.teacher,
                    day_of_week=day_of_week,
                    is_active=True,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                )

                if not available_slots.exists():
                    raise ValidationError(
                        f"This time is already unavailable in your regular weekly schedule. "
                        f"No need to add a block exception - you don't have recurring availability during this time. "
                        f"If you want to add special hours, use 'Special Hours' instead."
                    )


class TeacherAvailabilitySettings(models.Model):
    """
    Global settings for teacher's availability and booking behavior
    """
    teacher = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='availability_settings',
        help_text="Teacher who owns these settings"
    )

    # Buffer time between lessons
    buffer_minutes = models.IntegerField(
        default=0,
        help_text="Minutes of break time required between lessons (0-60)"
    )

    # Advance booking settings
    min_booking_notice_hours = models.IntegerField(
        default=24,
        help_text="Minimum hours in advance students must book (e.g., 24 = must book at least 1 day ahead)"
    )
    max_booking_days_ahead = models.IntegerField(
        default=90,
        help_text="Maximum days in advance students can book (e.g., 90 = can book up to 3 months ahead)"
    )

    # Availability system enable/disable
    use_availability_calendar = models.BooleanField(
        default=False,
        help_text="Enable availability calendar (if False, uses old request system)"
    )

    # Auto-approval
    auto_approve_bookings = models.BooleanField(
        default=True,
        help_text="Automatically approve bookings if slot is available (recommended)"
    )

    # Timezone
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Teacher's timezone (e.g., 'America/New_York', 'Europe/London')"
    )

    # Recurring lessons settings
    max_recurring_lessons = models.IntegerField(
        default=8,
        help_text="Maximum number of lessons students can book in a recurring sequence (e.g., 8 = up to 8 weekly lessons)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_teaching_availability_settings'
        verbose_name = 'Teacher Availability Settings'
        verbose_name_plural = 'Teacher Availability Settings'

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        return f"Availability Settings - {teacher_name}"



# ============================================================================
# QUIZ MODELS FOR PRIVATE LESSONS
# ============================================================================

class PrivateLessonQuiz(models.Model):
    """
    Quiz that can be assigned to private lesson students.
    Similar to Assignment model - reusable across students.
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Fields
    title = models.CharField(
        max_length=200,
        help_text="Quiz title (e.g., 'Grade 1 Theory Mock Exam')"
    )
    description = models.TextField(
        blank=True,
        help_text="Overview of what this quiz covers"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Instructions for students taking the quiz"
    )
    
    # Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_quizzes'
    )
    
    # Quiz Settings
    pass_percentage = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage to pass (0-100)"
    )
    time_limit_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time limit in minutes (null = no limit)"
    )
    randomize_questions = models.BooleanField(
        default=False,
        help_text="Randomize question order for each attempt"
    )
    show_correct_answers = models.BooleanField(
        default=True,
        help_text="Show correct answers after submission"
    )
    allow_retakes = models.BooleanField(
        default=True,
        help_text="Allow students to retake quiz"
    )
    max_attempts = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum attempts allowed (null = unlimited)"
    )
    pagination_mode = models.CharField(
        max_length=20,
        choices=[
            ('continuous', 'Continuous (Single Page)'),
            ('paginated', 'Paginated (One at a Time)'),
        ],
        default='continuous',
        help_text="Display mode for quiz questions"
    )

    # Categorization (align with LessonTemplate system)
    subject = models.ForeignKey(
        'private_teaching.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    syllabus = models.CharField(
        max_length=50,
        choices=[
            ('abrsm', 'ABRSM'),
            ('trinity', 'Trinity College'),
            ('rcm', 'RCM'),
            ('mtb', 'Music Teachers Board'),
            ('custom', 'Custom'),
        ],
        blank=True
    )
    grade_level = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., '1', 'Beginner', 'Intermediate'"
    )
    tags = models.ManyToManyField(
        'lesson_templates.Tag',
        blank=True,
        related_name='quizzes'
    )
    
    # Sharing
    is_public = models.BooleanField(
        default=False,
        help_text="Make quiz available to other teachers"
    )
    
    # Metadata
    use_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Private Lesson Quiz'
        verbose_name_plural = 'Private Lesson Quizzes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'is_public']),
            models.Index(fields=['syllabus', 'grade_level']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def total_points(self):
        """Calculate total possible points"""
        return self.questions.aggregate(
            total=models.Sum('points')
        )['total'] or 0
    
    @property
    def question_count(self):
        """Count of questions in this quiz"""
        return self.questions.count()
    
    def get_questions(self, randomize=False):
        """Get questions, optionally randomized"""
        questions = self.questions.all()
        if randomize and self.randomize_questions:
            return questions.order_by('?')
        return questions.order_by('order')


class PrivateLessonQuizQuestion(models.Model):
    """
    Individual question within a quiz.
    Supports rich text with CKEditor5.
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    quiz = models.ForeignKey(
        PrivateLessonQuiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    
    # Question Content
    text = CKEditor5Field(
        config_name='extends',
        help_text="Question text (supports images, music notation, etc.)"
    )
    
    # Ordering
    order = models.PositiveIntegerField(default=0)
    
    # Scoring
    points = models.PositiveIntegerField(
        default=1,
        help_text="Points awarded for correct answer"
    )
    
    # Optional Explanation
    explanation = models.TextField(
        blank=True,
        help_text="Explanation shown after answer (optional)"
    )
    
    class Meta:
        verbose_name = 'Quiz Question'
        ordering = ['order']
    
    def __str__(self):
        # Strip HTML for readable string representation
        from django.utils.html import strip_tags
        text_preview = strip_tags(self.text)[:50]
        return f"Q{self.order}: {text_preview}..."
    
    def get_answers(self):
        """Get all answers ordered"""
        return self.answers.all().order_by('order')
    
    def get_correct_answer(self):
        """Get the first correct answer (for single-answer questions)"""
        return self.answers.filter(is_correct=True).first()

    def get_correct_answers(self):
        """Get all correct answers for this question"""
        return self.answers.filter(is_correct=True)

    def has_multiple_correct_answers(self):
        """Check if this question has more than one correct answer"""
        return self.answers.filter(is_correct=True).count() > 1


class PrivateLessonQuizAnswer(models.Model):
    """
    Answer option for a quiz question.
    Supports multiple correct answers when teacher marks more than one.
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    question = models.ForeignKey(
        PrivateLessonQuizQuestion,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    
    # Answer Content
    text = CKEditor5Field(
        config_name='default',
        help_text="Answer text (supports images, formatting, music notation)"
    )
    
    # Correctness
    is_correct = models.BooleanField(
        default=False,
        help_text="Mark as the correct answer"
    )
    
    # Ordering
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Quiz Answer'
        ordering = ['order']
    
    def __str__(self):
        correct_marker = "✓" if self.is_correct else "✗"
        return f"{correct_marker} {self.text[:50]}"


class PrivateLessonQuizAssignment(models.Model):
    """
    Assignment of a quiz to a specific student by a teacher.
    Bridge between reusable quiz template and individual student.
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    quiz = models.ForeignKey(
        PrivateLessonQuiz,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_quizzes'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_quizzes'
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_quizzes',
        help_text="If student is a guardian, specify which child"
    )
    
    # Optional Lesson Link
    lesson = models.ForeignKey(
        'lessons.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quiz_assignments',
        help_text="Link to specific lesson (optional)"
    )
    
    # Assignment Details
    assigned_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional deadline"
    )
    notes = models.TextField(
        blank=True,
        help_text="Teacher notes for student about this quiz"
    )
    
    # Status
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='assigned'
    )
    
    class Meta:
        verbose_name = 'Quiz Assignment'
        ordering = ['-assigned_date']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['teacher', 'assigned_date']),
        ]
        # Prevent duplicate assignments
        unique_together = ['quiz', 'student', 'child_profile']
    
    def __str__(self):
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        return f"{self.quiz.title} → {student_name}"
    
    @property
    def is_overdue(self):
        """Check if past due date"""
        if not self.due_date:
            return False
        return timezone.now() > self.due_date and self.status != 'completed'
    
    @property
    def attempt_count(self):
        """Number of attempts made"""
        return self.attempts.count()
    
    @property
    def best_attempt(self):
        """Highest scoring attempt"""
        return self.attempts.filter(
            submitted_at__isnull=False
        ).order_by('-score').first()
    
    @property
    def latest_attempt(self):
        """Most recent attempt"""
        return self.attempts.order_by('-started_at').first()
    
    @property
    def passed(self):
        """Has student passed this quiz?"""
        best = self.best_attempt
        return best.passed if best else False


class PrivateLessonQuizAttempt(models.Model):
    """
    Individual attempt at a quiz by a student.
    Tracks answers, score, and timing.
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    assignment = models.ForeignKey(
        PrivateLessonQuizAssignment,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Answers (stored as JSON: {question_id: answer_id})
    answers_data = models.JSONField(
        default=dict,
        help_text="Student answers as {question_id: answer_id}"
    )
    
    # Results
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage score (0-100)"
    )
    passed = models.BooleanField(default=False)
    
    # Time tracking
    time_taken_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="How long student took (minutes)"
    )

    # Auto-save tracking
    last_autosave_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last auto-save operation"
    )

    class Meta:
        verbose_name = 'Quiz Attempt'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['assignment', 'submitted_at']),
        ]
    
    def __str__(self):
        status = "Graded" if self.submitted_at else "In Progress"
        return f"Attempt {self.started_at.strftime('%Y-%m-%d')} - {status}"
    
    @property
    def quiz(self):
        """Shortcut to quiz"""
        return self.assignment.quiz
    
    @property
    def student(self):
        """Shortcut to student"""
        return self.assignment.student
    
    @property
    def is_submitted(self):
        """Has this attempt been submitted?"""
        return self.submitted_at is not None

    def autosave_answers(self, answers_data):
        """
        Save answers without grading or marking as submitted.
        Used for periodic auto-save functionality.

        Args:
            answers_data: dict mapping question_id to answer_id

        Returns:
            bool: True if save successful
        """
        from django.utils import timezone
        self.answers_data = answers_data
        self.last_autosave_at = timezone.now()
        self.save(update_fields=['answers_data', 'last_autosave_at'])
        return True

    def calculate_score(self):
        """
        Calculate percentage score based on answers_data.
        Supports both single-answer and multi-answer questions.
        Returns: (earned_points, total_points, percentage)
        """
        quiz = self.quiz
        questions = quiz.get_questions()

        earned_points = 0
        total_points = 0

        for question in questions:
            total_points += question.points

            # Get student's answer(s)
            student_answer = self.answers_data.get(str(question.id))
            if not student_answer:
                continue

            # Check if question has multiple correct answers
            if question.has_multiple_correct_answers():
                # Multi-answer question: student must select ALL correct answers
                # and NO incorrect answers to earn points
                correct_answer_ids = set(
                    str(a.id) for a in question.get_correct_answers()
                )
                # student_answer should be a list for multi-answer questions
                if isinstance(student_answer, list):
                    student_answer_ids = set(str(a) for a in student_answer)
                else:
                    # Backwards compatibility: single value stored
                    student_answer_ids = {str(student_answer)}

                # Award points only if exact match
                if student_answer_ids == correct_answer_ids:
                    earned_points += question.points
            else:
                # Single-answer question
                correct_answer = question.get_correct_answer()
                # Handle both string and list formats for backwards compatibility
                if isinstance(student_answer, list):
                    student_answer_id = str(student_answer[0]) if student_answer else None
                else:
                    student_answer_id = str(student_answer)

                if correct_answer and str(correct_answer.id) == student_answer_id:
                    earned_points += question.points

        # Calculate percentage
        percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        
        return earned_points, total_points, Decimal(str(round(percentage, 2)))
    
    def grade(self):
        """
        Grade the attempt and save results.
        Returns dict with grading details.
        """
        earned_points, total_points, percentage = self.calculate_score()
        
        self.score = percentage
        self.passed = percentage >= self.assignment.quiz.pass_percentage
        self.submitted_at = timezone.now()
        
        # Calculate time taken
        if self.started_at:
            time_delta = timezone.now() - self.started_at
            self.time_taken_minutes = int(time_delta.total_seconds() / 60)
        
        self.save()
        
        # Update assignment status
        self.assignment.status = 'completed'
        self.assignment.save()
        
        return {
            'earned_points': earned_points,
            'total_points': total_points,
            'percentage': float(percentage),
            'passed': self.passed,
            'pass_percentage': self.assignment.quiz.pass_percentage,
        }
    
    def get_detailed_results(self):
        """
        Get detailed results for each question.
        Returns list of dicts with question, student answer, correct answer, etc.
        """
        quiz = self.quiz
        questions = quiz.get_questions()
        results = []
        
        for question in questions:
            student_answer_id = self.answers_data.get(str(question.id))
            correct_answer = question.get_correct_answer()
            
            student_answer = None
            if student_answer_id:
                student_answer = question.answers.filter(id=student_answer_id).first()
            
            is_correct = (
                student_answer and 
                correct_answer and 
                str(student_answer.id) == str(correct_answer.id)
            )
            
            results.append({
                'question': question,
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'points_earned': question.points if is_correct else 0,
                'points_possible': question.points,
            })
        
        return results


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
