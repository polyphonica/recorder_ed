from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class StripePayment(models.Model):
    """Track all Stripe payments across the platform"""
    
    DOMAIN_CHOICES = [
        ('workshops', 'Workshops'),
        ('courses', 'Courses'),
        ('private_teaching', 'Private Teaching'),
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
