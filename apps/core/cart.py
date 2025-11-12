"""
Base shopping cart utilities shared across apps
"""
from decimal import Decimal
from abc import ABC, abstractmethod


class BaseCartManager(ABC):
    """Abstract base class for managing shopping cart operations"""

    def __init__(self, request):
        self.request = request
        self.user = request.user if request.user.is_authenticated else None
        self.session = request.session

    @abstractmethod
    def get_cart_model(self):
        """Return the Cart model class to use"""
        pass

    def get_or_create_cart(self):
        """Get or create cart for current user/session"""
        if self.user and self.user.is_authenticated:
            # Authenticated user - use database cart
            cart_model = self.get_cart_model()
            cart, created = cart_model.objects.get_or_create(
                user=self.user,
                defaults={'session_key': getattr(self.session, 'session_key', None)}
            )
            return cart
        else:
            # Anonymous user - require authentication
            return None

    def get_cart(self):
        """Get current cart"""
        if not self.user:
            return None

        try:
            cart_model = self.get_cart_model()
            cart = cart_model.objects.get(user=self.user)
            return cart
        except cart_model.DoesNotExist:
            return None

    def _require_authentication(self, action="manage cart"):
        """Helper to check authentication and return standard error message"""
        if not self.user or not self.user.is_authenticated:
            return False, f"Please log in to {action}"
        return True, None

    def _get_cart_or_error(self):
        """Helper to get cart or return error tuple"""
        cart = self.get_or_create_cart()
        if not cart:
            return None, (False, "Cart not found")
        return cart, None

    def get_base_cart_context(self, cart, items_queryset, item_key, total_key, count_key):
        """
        Get base cart context structure for templates

        Args:
            cart: Cart instance or None
            items_queryset: Queryset of cart items
            item_key: Key name for items in context (e.g., 'cart_items')
            total_key: Key name for total in context (e.g., 'cart_total')
            count_key: Key name for count in context (e.g., 'cart_count')

        Returns:
            Dictionary with cart context
        """
        if not cart:
            return {
                'cart': None,
                item_key: [],
                total_key: Decimal('0.00'),
                count_key: 0,
            }

        items = items_queryset

        return {
            'cart': cart,
            item_key: items,
            total_key: sum(item.total_price for item in items),
            count_key: items.count(),
        }
