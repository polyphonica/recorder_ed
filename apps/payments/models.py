import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class ShoppingCart(models.Model):
    """Shopping cart for storing workshop sessions before purchase"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shopping_cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'

    def __str__(self):
        return f"Cart for {self.user.email} ({self.items.count()} items)"

    @property
    def total_amount(self):
        """Calculate total amount of all items in cart"""
        return sum(item.price for item in self.items.all())

    @property
    def item_count(self):
        """Get count of items in cart"""
        return self.items.count()

    def add_session(self, session):
        """Add a workshop session to cart (if not already present)"""
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            session=session,
            defaults={'price': session.workshop.price}
        )
        return cart_item, created

    def remove_session(self, session):
        """Remove a workshop session from cart"""
        return CartItem.objects.filter(cart=self, session=session).delete()

    def clear(self):
        """Remove all items from cart"""
        return self.items.all().delete()


class CartItem(models.Model):
    """Individual workshop session in a shopping cart"""
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='items')
    session = models.ForeignKey('workshops.WorkshopSession', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of adding to cart")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'session']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        ordering = ['added_at']

    def __str__(self):
        return f"{self.session.workshop.title} - {self.session.start_date}"


class Order(models.Model):
    """Completed order after successful payment"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Internal notes about the order")

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.user.email} - ${self.total_amount}"

    @property
    def session_count(self):
        """Get count of sessions in this order"""
        return self.items.count()


class OrderItem(models.Model):
    """Individual workshop session in a completed order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    session = models.ForeignKey('workshops.WorkshopSession', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price paid for this session")

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.order.id} - {self.session.workshop.title}"


class Transaction(models.Model):
    """Payment transaction record"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, help_text="External payment provider transaction ID")
    payment_method = models.CharField(max_length=50, default='mock', help_text="Payment method used")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Future payment provider fields
    provider_response = models.JSONField(blank=True, null=True, help_text="Raw response from payment provider")
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction {self.id} - ${self.amount} - {self.status}"