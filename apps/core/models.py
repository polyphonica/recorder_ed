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
