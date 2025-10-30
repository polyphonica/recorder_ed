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
    workshop_id = models.IntegerField(null=True, blank=True)
    course_id = models.IntegerField(null=True, blank=True)
    order_id = models.IntegerField(null=True, blank=True)  # For private lessons
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
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
