"""
Shopping cart utilities for private teaching lessons
"""
from decimal import Decimal
from django.shortcuts import get_object_or_404
from apps.core.cart import BaseCartManager
from .models import Cart, CartItem
from lessons.models import Lesson


class CartManager(BaseCartManager):
    """Manage shopping cart operations"""

    def get_cart_model(self):
        """Return the Cart model class to use"""
        return Cart
    
    def add_lesson(self, lesson_id, price=None):
        """Add a lesson to cart"""
        is_auth, error = self._require_authentication("add lessons to cart")
        if not is_auth:
            return False, error

        try:
            lesson = get_object_or_404(Lesson, id=lesson_id)
        except:
            return False, "Lesson not found"

        # Verify lesson is approved and unpaid
        if lesson.approved_status != 'Accepted':
            return False, f"Only accepted lessons can be added to cart (status: {lesson.approved_status})"

        if lesson.payment_status == 'Paid':
            return False, "This lesson has already been paid for"

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        # Use lesson's fee if no price provided
        if price is None:
            price = lesson.fee or 50.00

        # Check if lesson already in cart
        existing_item = CartItem.objects.filter(
            cart=cart,
            lesson=lesson
        ).first()

        if existing_item:
            return False, "This lesson is already in your cart"

        # Create new cart item
        try:
            cart_item = CartItem.objects.create(
                cart=cart,
                lesson=lesson,
                price=price
            )
            # Mark lesson as in cart
            lesson.in_cart = True
            lesson.save()
            return True, f"Added {lesson.subject.subject} lesson to cart"
        except Exception as e:
            return False, f"Error adding lesson to cart: {str(e)}"
    
    def add_all_lessons_from_request(self, lesson_request):
        """Add all accepted, unpaid lessons from a lesson request to cart"""
        is_auth, error = self._require_authentication("add lessons to cart")
        if not is_auth:
            return False, error

        # Get all accepted, unpaid lessons from the request
        eligible_lessons = lesson_request.lessons.filter(
            approved_status='Accepted',
            payment_status='Not Paid'
        )

        if not eligible_lessons.exists():
            return False, "No accepted, unpaid lessons found in this request"

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        added_count = 0
        skipped_count = 0

        for lesson in eligible_lessons:
            # Check if lesson already in cart
            existing_item = CartItem.objects.filter(
                cart=cart,
                lesson=lesson
            ).first()

            if existing_item:
                skipped_count += 1
                continue

            # Create new cart item
            CartItem.objects.create(
                cart=cart,
                lesson=lesson,
                price=lesson.fee
            )
            lesson.in_cart = True
            lesson.save()
            added_count += 1

        if added_count == 0:
            return False, f"All {skipped_count} lessons are already in your cart"
        elif skipped_count > 0:
            return True, f"Added {added_count} lessons to cart ({skipped_count} already in cart)"
        else:
            return True, f"Added {added_count} lessons to cart"
    
    def remove_lesson(self, lesson_id):
        """Remove a lesson from cart"""
        is_auth, error = self._require_authentication()
        if not is_auth:
            return False, error

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        try:
            cart_item = CartItem.objects.get(
                cart=cart,
                lesson_id=lesson_id
            )
            lesson_name = str(cart_item.lesson)
            lesson = cart_item.lesson
            cart_item.delete()
            # Update lesson in_cart status
            lesson.in_cart = False
            lesson.save()
            return True, f"Removed {lesson_name} from cart"
        except CartItem.DoesNotExist:
            return False, "Lesson not found in cart"
    
    def clear_cart(self):
        """Clear all items from cart"""
        is_auth, error = self._require_authentication()
        if not is_auth:
            return False, error

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple
            
        item_count = cart.items.count()
        cart.items.all().delete()
        return True, f"Removed {item_count} items from cart"
    
    def get_cart_context(self):
        """Get cart context for templates"""
        cart = self.get_cart()

        cart_items = cart.items.select_related(
            'lesson__lesson_request',
            'lesson__subject',
            'lesson__student'
        ).all() if cart else []

        return self.get_base_cart_context(
            cart=cart,
            items_queryset=cart_items,
            item_key='cart_items',
            total_key='cart_total',
            count_key='cart_count'
        )