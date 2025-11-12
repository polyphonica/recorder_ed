from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
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
        return f"{self.subject} (${self.base_price_60min}/60min)"


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