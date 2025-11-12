from django.db import models


class PayableModel(models.Model):
    """
    Abstract base model for entities that require payment processing

    Provides common payment-related fields for workshops, courses, and other paid services.
    Includes Stripe integration fields and payment status tracking.
    """

    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Pending Payment'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
    ]

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
