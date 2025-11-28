"""
Shopping cart utilities for workshop sessions
"""
from decimal import Decimal
from django.shortcuts import get_object_or_404
from apps.private_teaching.models import Cart
from apps.core.cart import BaseCartManager
from .models import WorkshopCartItem, WorkshopSession


class WorkshopCartManager(BaseCartManager):
    """Manage workshop cart operations"""

    def get_cart_model(self):
        """Return the Cart model class to use"""
        return Cart

    def add_session(self, session_id, child_profile_id=None, notes='', registration_data=None, is_series_purchase=False, series_price=None):
        """
        Add a workshop session to cart with optional registration data

        Args:
            session_id: UUID of the workshop session
            child_profile_id: Optional child profile ID for guardian purchases
            notes: Optional notes for the instructor
            registration_data: Dict with registration form data (for in-person workshops)
            is_series_purchase: Boolean indicating if this is part of a series purchase
            series_price: Decimal series price to use for series purchases
        """
        # Check authentication
        is_auth, error = self._require_authentication("add workshops to cart")
        if not is_auth:
            return False, error

        try:
            session = get_object_or_404(WorkshopSession, id=session_id)
        except:
            return False, "Workshop session not found"

        # Verify session is active and upcoming
        if not session.is_active:
            return False, "This workshop session is not available"

        if session.is_cancelled:
            return False, "This workshop session has been cancelled"

        if session.is_past:
            return False, "This workshop session has already occurred"

        # Check if session is full
        if session.is_full and not session.waitlist_enabled:
            return False, "This workshop session is full"

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        # Determine price
        if is_series_purchase and series_price and session.workshop.is_series:
            # For series purchases, divide the series price equally among all sessions
            session_count = session.workshop.series_session_count
            price = series_price / session_count if session_count > 0 else session.workshop.price
        else:
            # Use workshop's regular price
            price = session.workshop.price

        # Check if session already in cart
        existing_item = WorkshopCartItem.objects.filter(
            cart=cart,
            session=session
        ).first()

        if existing_item:
            return False, "This workshop session is already in your cart"

        # Create new cart item
        try:
            from apps.accounts.models import ChildProfile
            child_profile = None
            if child_profile_id:
                child_profile = ChildProfile.objects.get(id=child_profile_id, guardian=self.user)

            # Prepare cart item data
            cart_item_data = {
                'cart': cart,
                'session': session,
                'price': price,
                'notes': notes,
                'child_profile': child_profile,
            }

            # Add registration data if provided (for in-person workshops)
            if registration_data:
                cart_item_data.update({
                    'email': registration_data.get('email', ''),
                    'phone': registration_data.get('phone', ''),
                    'emergency_contact': registration_data.get('emergency_contact', ''),
                    'experience_level': registration_data.get('experience_level', ''),
                    'expectations': registration_data.get('expectations', ''),
                    'special_requirements': registration_data.get('special_requirements', ''),
                    'registration_completed': True,  # Mark as having completed registration form
                })

            cart_item = WorkshopCartItem.objects.create(**cart_item_data)
            return True, f"Added {session.workshop.title} to cart"
        except Exception as e:
            return False, f"Error adding workshop to cart: {str(e)}"

    def remove_session(self, session_id):
        """Remove a workshop session from cart.

        For mandatory series, removes ALL sessions from that series.
        """
        is_auth, error = self._require_authentication()
        if not is_auth:
            return False, error

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        try:
            cart_item = WorkshopCartItem.objects.get(
                cart=cart,
                session_id=session_id
            )
            workshop = cart_item.session.workshop

            # Check if this is part of a mandatory series
            if workshop.is_series and workshop.require_full_series_registration:
                # Count how many sessions from this series are in cart
                series_items = WorkshopCartItem.objects.filter(
                    cart=cart,
                    session__workshop=workshop
                )
                session_count = series_items.count()

                # Remove ALL sessions from this mandatory series
                series_items.delete()

                return True, f"Removed entire {workshop.title} series ({session_count} sessions) from cart"

            # Individual session removal (not part of mandatory series)
            workshop_name = workshop.title
            cart_item.delete()
            return True, f"Removed {workshop_name} from cart"
        except WorkshopCartItem.DoesNotExist:
            return False, "Workshop session not found in cart"

    def clear_workshop_cart(self):
        """Clear all workshop items from cart"""
        is_auth, error = self._require_authentication()
        if not is_auth:
            return False, error

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        item_count = cart.workshop_items.count()
        cart.workshop_items.all().delete()
        return True, f"Removed {item_count} workshop(s) from cart"

    def get_cart_context(self):
        """Get cart context for templates"""
        cart = self.get_cart()

        workshop_items = cart.workshop_items.select_related(
            'session__workshop__instructor',
            'session__workshop__category',
            'child_profile'
        ).all() if cart else []

        return self.get_base_cart_context(
            cart=cart,
            items_queryset=workshop_items,
            item_key='workshop_cart_items',
            total_key='workshop_cart_total',
            count_key='workshop_cart_count'
        )

    def get_combined_cart_total(self):
        """Get total for both workshops and lessons in cart"""
        cart = self.get_cart()
        if not cart:
            return Decimal('0.00')

        workshop_total = sum(item.total_price for item in cart.workshop_items.all())
        lesson_total = sum(item.total_price for item in cart.items.all())

        return workshop_total + lesson_total
