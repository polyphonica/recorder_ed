from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import FileExtensionValidator


class ExpenseCategory(models.Model):
    """Categories for organizing expenses"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, help_text="Optional description of this category")
    is_active = models.BooleanField(default=True, help_text="Inactive categories won't appear in expense form")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='expense_categories_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Expense Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Business expenses for tax and accounting purposes"""

    # Business area choices
    PRIVATE_TEACHING = 'private_teaching'
    WORKSHOPS = 'workshops'
    COURSES = 'courses'
    DIGITAL_PRODUCTS = 'digital_products'
    GENERAL = 'general'

    BUSINESS_AREA_CHOICES = [
        (PRIVATE_TEACHING, 'Private Teaching'),
        (WORKSHOPS, 'Workshops'),
        (COURSES, 'Courses'),
        (DIGITAL_PRODUCTS, 'Digital Products'),
        (GENERAL, 'General/Shared Expenses'),
    ]

    # Payment method choices
    CASH = 'cash'
    CARD = 'card'
    BANK_TRANSFER = 'bank_transfer'
    PAYPAL = 'paypal'
    OTHER = 'other'

    PAYMENT_METHOD_CHOICES = [
        (CASH, 'Cash'),
        (CARD, 'Card'),
        (BANK_TRANSFER, 'Bank Transfer'),
        (PAYPAL, 'PayPal'),
        (OTHER, 'Other'),
    ]

    # Core fields
    date = models.DateField(help_text="Date the expense was incurred")
    business_area = models.CharField(max_length=20, choices=BUSINESS_AREA_CHOICES)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    description = models.TextField(help_text="What was purchased")
    supplier = models.CharField(max_length=200, help_text="Vendor or supplier name")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in GBP (£)")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=CARD)

    # Optional fields
    # SECURITY FIX: Added validators for file type restrictions
    receipt_file = models.FileField(
        upload_to='expense_receipts/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']),
        ],
        help_text="Upload receipt image or PDF (max 5MB)"
    )
    notes = models.TextField(blank=True, help_text="Additional notes")

    # Workshop linking (optional)
    workshop = models.ForeignKey('workshops.Workshop', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='expenses', help_text="Link to specific workshop (optional)")

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='expenses_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['business_area']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.date} - {self.description} (£{self.amount})"

    def get_absolute_url(self):
        return reverse('expenses:expense_detail', kwargs={'pk': self.pk})
