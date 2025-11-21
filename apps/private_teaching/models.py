from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
import uuid

from apps.core.models import PayableModel

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        unique_together = ['teacher', 'subject']

    def __str__(self):
        return f"{self.subject} (£{self.base_price_60min}/60min)"


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
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        guardian_info = f" (Guardian: {self.student.get_full_name()})" if self.child_profile else ""
        return f"{student_name}{guardian_info} - {self.lessons.count()} lesson(s) - {self.created_at.strftime('%Y-%m-%d')}"

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
        if all(s == 'Accepted' for s in statuses):
            return 'accepted'
        elif all(s == 'Rejected' for s in statuses):
            return 'rejected'
        elif any(s == 'Pending' for s in statuses):
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
    
    def __str__(self):
        return f"Order {self.order_number} - {self.student.get_full_name()}"
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        from django.utils import timezone
        
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
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
        on_delete=models.CASCADE,
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