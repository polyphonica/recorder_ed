import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class StripePayment(models.Model):
    """Track all Stripe payments across the platform"""
    
    DOMAIN_CHOICES = [
        ('workshops', 'Workshops'),
        ('courses', 'Courses'),
        ('private_teaching', 'Private Teaching'),
        ('digital_products', 'Digital Products'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Stripe identifiers
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Platform details
    domain = models.CharField(max_length=50, choices=DOMAIN_CHOICES)
    student = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payments_made')
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payments_received')
    
    # Financial details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount paid by student")
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, help_text="Platform commission")
    teacher_share = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount for teacher")
    currency = models.CharField(max_length=3, default='gbp')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # References to original objects
    workshop_id = models.UUIDField(null=True, blank=True)
    course_id = models.UUIDField(null=True, blank=True)
    order_id = models.IntegerField(null=True, blank=True)  # For private lessons
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Refund tracking
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount refunded (if partial)")
    refunded_at = models.DateTimeField(null=True, blank=True, help_text="When refund was processed")
    stripe_refund_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe refund ID")

    # Stripe fee tracking (for platform accounting)
    stripe_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Stripe's processing fee for this transaction"
    )
    stripe_balance_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Balance Transaction ID for fee tracking"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stripe Payment'
        verbose_name_plural = 'Stripe Payments'
    
    def __str__(self):
        return f"{self.domain} - {self.student} - £{self.total_amount} ({self.status})"
    
    def mark_completed(self):
        """Mark payment as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self):
        """Mark payment as failed"""
        self.status = 'failed'
        self.save()

    def mark_refunded(self, refund_amount=None, stripe_refund_id=None):
        """Mark payment as refunded"""
        self.status = 'refunded'
        self.refunded_at = timezone.now()
        self.refund_amount = refund_amount or self.total_amount  # Default to full refund
        if stripe_refund_id:
            self.stripe_refund_id = stripe_refund_id
        self.save()

    def is_full_refund(self):
        """Check if this is a full refund"""
        if self.status != 'refunded' or not self.refund_amount:
            return False
        return self.refund_amount >= self.total_amount

    def is_partial_refund(self):
        """Check if this is a partial refund"""
        if self.status != 'refunded' or not self.refund_amount:
            return False
        return self.refund_amount < self.total_amount


class Voucher(models.Model):
    """
    Voucher/promo code for discounts across multiple domains.
    Created by teachers for promotional purposes (e.g., competition winners, promotional offers).
    """

    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage Off'),
        ('fixed', 'Fixed Amount Off'),
        ('free', '100% Free'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('exhausted', 'Usage Limit Reached'),
    ]

    DOMAIN_CHOICES = [
        ('private_teaching', 'Private Lessons'),
        ('workshops', 'Workshops'),
        ('workshop_series', 'Workshop Series'),
        ('digital_products', 'Digital Products'),
        ('courses', 'Courses'),
    ]

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Voucher Code
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique voucher code (e.g., SUMMER25, FREECLASS)"
    )

    # Teacher who created it
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_vouchers',
        help_text="Teacher who created this voucher"
    )

    # Description (internal)
    description = models.TextField(
        blank=True,
        help_text="Internal description/purpose (e.g., 'Competition winner prize')"
    )

    # Discount Configuration
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        help_text="Type of discount to apply"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Percentage (0-100) or fixed amount in GBP depending on type. Set to 0 for 'free' type."
    )

    # Applicable Domains (stored as JSON list for flexibility)
    applicable_domains = models.JSONField(
        default=list,
        help_text="List of domains: ['private_teaching', 'workshops', 'workshop_series', 'digital_products']"
    )

    # Restrictions - specific students
    restricted_to_students = models.ManyToManyField(
        User,
        related_name='restricted_vouchers',
        blank=True,
        help_text="If set, only these students can use the voucher"
    )

    # Restrictions - specific workshops
    restricted_to_workshops = models.ManyToManyField(
        'workshops.Workshop',
        related_name='restricted_vouchers',
        blank=True,
        help_text="If set, only valid for these specific workshops"
    )

    # Validity Period
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text="When the voucher becomes valid"
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the voucher expires (null = no expiration)"
    )

    # Usage Limits
    max_uses_total = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total redemptions (null = unlimited)"
    )
    max_uses_per_student = models.PositiveIntegerField(
        default=1,
        help_text="Maximum uses per student"
    )

    # Minimum Purchase Requirement
    minimum_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum cart total required to apply voucher"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Current status of the voucher"
    )

    # Stripe Coupon ID (for partial discounts that need Stripe integration)
    stripe_coupon_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Coupon ID for partial discount vouchers"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Voucher'
        verbose_name_plural = 'Vouchers'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    @property
    def times_used(self):
        """Return the total number of times this voucher has been redeemed"""
        return self.redemptions.count()

    @property
    def is_expired(self):
        """Check if voucher has passed its expiration date"""
        if self.valid_until is None:
            return False
        return timezone.now() > self.valid_until

    @property
    def is_exhausted(self):
        """Check if voucher has reached its usage limit"""
        if self.max_uses_total is None:
            return False
        return self.times_used >= self.max_uses_total

    @property
    def is_valid_period(self):
        """Check if current time is within valid period"""
        now = timezone.now()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def is_usable(self):
        """Check if voucher can currently be used (basic checks only)"""
        return (
            self.status == 'active' and
            self.is_valid_period and
            not self.is_exhausted
        )

    def uses_remaining(self):
        """Return number of uses remaining, or None if unlimited"""
        if self.max_uses_total is None:
            return None
        return max(0, self.max_uses_total - self.times_used)

    def update_status_if_needed(self):
        """Update status based on current state (call after redemptions)"""
        if self.status == 'active':
            if self.is_expired:
                self.status = 'expired'
                self.save(update_fields=['status', 'updated_at'])
            elif self.is_exhausted:
                self.status = 'exhausted'
                self.save(update_fields=['status', 'updated_at'])


class VoucherRedemption(models.Model):
    """
    Audit trail for voucher redemptions.
    Records each use of a voucher with full financial details.
    """

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Voucher and Student
    voucher = models.ForeignKey(
        Voucher,
        on_delete=models.PROTECT,
        related_name='redemptions',
        help_text="The voucher that was redeemed"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='voucher_redemptions',
        help_text="The student who redeemed the voucher"
    )

    # What domain was the purchase in
    domain = models.CharField(
        max_length=50,
        help_text="Domain where voucher was used: private_teaching, workshops, workshop_series"
    )

    # Domain-specific references (only one will be populated based on domain)
    private_lesson_order = models.ForeignKey(
        'private_teaching.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_redemptions',
        help_text="Order if used for private lessons"
    )
    workshop_registration = models.ForeignKey(
        'workshops.WorkshopRegistration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_redemptions',
        help_text="Registration if used for workshop"
    )
    course_enrollment = models.ForeignKey(
        'courses.CourseEnrollment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_redemptions',
        help_text="Enrollment if used for a course"
    )

    # Financial Details
    original_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original price before discount"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount discounted"
    )
    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Final price paid after discount"
    )

    # Payment Method
    payment_bypassed = models.BooleanField(
        default=False,
        help_text="True if 100% free - Stripe was bypassed"
    )
    stripe_payment = models.ForeignKey(
        StripePayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_redemption',
        help_text="Associated Stripe payment if payment was made"
    )

    # Timestamp
    redeemed_at = models.DateTimeField(auto_now_add=True)

    # Audit fields
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address at time of redemption"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent at time of redemption"
    )

    class Meta:
        ordering = ['-redeemed_at']
        verbose_name = 'Voucher Redemption'
        verbose_name_plural = 'Voucher Redemptions'
        indexes = [
            models.Index(fields=['voucher', 'student']),
            models.Index(fields=['domain', 'redeemed_at']),
        ]

    def __str__(self):
        return f"{self.voucher.code} - {self.student} - £{self.discount_amount} off"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update voucher status after redemption
        self.voucher.update_status_if_needed()
