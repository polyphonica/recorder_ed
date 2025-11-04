"""
Shopping cart utilities for workshop sessions
"""
from decimal import Decimal
from django.shortcuts import get_object_or_404
from apps.private_teaching.models import Cart
from .models import WorkshopCartItem, WorkshopSession


class WorkshopCartManager:
    """Manage workshop cart operations"""

    def __init__(self, request):
        self.request = request
        self.user = request.user if request.user.is_authenticated else None
        self.session = request.session

    def get_or_create_cart(self):
        """Get or create cart for current user/session"""
        if self.user and self.user.is_authenticated:
            # Authenticated user - use database cart (unified with lessons)
            cart, created = Cart.objects.get_or_create(
                user=self.user,
                defaults={'session_key': getattr(self.session, 'session_key', None)}
            )
            return cart
        else:
            # Anonymous user - require authentication for workshops
            return None

    def add_session(self, session_id, child_profile_id=None, notes=''):
        """Add a workshop session to cart"""
        if not self.user or not self.user.is_authenticated:
            return False, "Please log in to add workshops to cart"

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

        cart = self.get_or_create_cart()
        if not cart:
            return False, "Unable to create cart"

        # Use workshop's price
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

            cart_item = WorkshopCartItem.objects.create(
                cart=cart,
                session=session,
                price=price,
                notes=notes,
                child_profile=child_profile
            )
            return True, f"Added {session.workshop.title} to cart"
        except Exception as e:
            return False, f"Error adding workshop to cart: {str(e)}"

    def remove_session(self, session_id):
        """Remove a workshop session from cart"""
        if not self.user:
            return False, "Please log in to manage cart"

        cart = self.get_or_create_cart()
        if not cart:
            return False, "Cart not found"

        try:
            cart_item = WorkshopCartItem.objects.get(
                cart=cart,
                session_id=session_id
            )
            workshop_name = cart_item.session.workshop.title
            cart_item.delete()
            return True, f"Removed {workshop_name} from cart"
        except WorkshopCartItem.DoesNotExist:
            return False, "Workshop session not found in cart"

    def clear_workshop_cart(self):
        """Clear all workshop items from cart"""
        if not self.user:
            return False, "Please log in to manage cart"

        cart = self.get_or_create_cart()
        if not cart:
            return False, "Cart not found"

        item_count = cart.workshop_items.count()
        cart.workshop_items.all().delete()
        return True, f"Removed {item_count} workshop(s) from cart"

    def get_cart(self):
        """Get current cart with workshop items"""
        if not self.user:
            return None

        try:
            cart = Cart.objects.get(user=self.user)
            return cart
        except Cart.DoesNotExist:
            return None

    def get_cart_context(self):
        """Get cart context for templates"""
        cart = self.get_cart()

        if not cart:
            return {
                'cart': None,
                'workshop_cart_items': [],
                'workshop_cart_total': Decimal('0.00'),
                'workshop_cart_count': 0,
            }

        workshop_items = cart.workshop_items.select_related(
            'session__workshop__instructor',
            'session__workshop__category',
            'child_profile'
        ).all()

        return {
            'cart': cart,
            'workshop_cart_items': workshop_items,
            'workshop_cart_total': sum(item.total_price for item in workshop_items),
            'workshop_cart_count': workshop_items.count(),
        }

    def get_combined_cart_total(self):
        """Get total for both workshops and lessons in cart"""
        cart = self.get_cart()
        if not cart:
            return Decimal('0.00')

        workshop_total = sum(item.total_price for item in cart.workshop_items.all())
        lesson_total = sum(item.total_price for item in cart.items.all())

        return workshop_total + lesson_total
