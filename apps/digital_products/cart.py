from apps.core.cart import BaseCartManager
from apps.private_teaching.models import Cart
from .models import DigitalProduct, DigitalProductCartItem, ProductPurchase


class DigitalProductCartManager(BaseCartManager):
    """Manage digital product cart operations"""

    def get_cart_model(self):
        """Return the Cart model class to use"""
        return Cart

    def add_product(self, product_id):
        """
        Add digital product to cart.

        Args:
            product_id: UUID of the product to add

        Returns:
            tuple: (success: bool, message: str)
        """
        # Check authentication
        is_auth, error = self._require_authentication("add products to cart")
        if not is_auth:
            return False, error

        # Check if product exists and is published
        try:
            product = DigitalProduct.objects.get(id=product_id, status='published')
        except DigitalProduct.DoesNotExist:
            return False, "Product not found or not available"

        # Check if already purchased
        if ProductPurchase.objects.filter(
            student=self.user,
            product=product,
            payment_status='completed'
        ).exists():
            return False, "You have already purchased this product"

        # Get or create cart
        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        # Check if already in cart
        if DigitalProductCartItem.objects.filter(cart=cart, product=product).exists():
            return False, "This product is already in your cart"

        # Add to cart
        DigitalProductCartItem.objects.create(
            cart=cart,
            product=product,
            price=product.price
        )

        return True, f"Added '{product.title}' to cart"

    def remove_product(self, product_id):
        """
        Remove product from cart.

        Args:
            product_id: UUID of the product to remove

        Returns:
            tuple: (success: bool, message: str)
        """
        is_auth, error = self._require_authentication()
        if not is_auth:
            return False, error

        cart, error_tuple = self._get_cart_or_error()
        if error_tuple:
            return error_tuple

        try:
            cart_item = DigitalProductCartItem.objects.get(cart=cart, product_id=product_id)
            product_name = cart_item.product.title
            cart_item.delete()
            return True, f"Removed '{product_name}' from cart"
        except DigitalProductCartItem.DoesNotExist:
            return False, "Product not in cart"

    def get_cart_context(self):
        """
        Get cart context for templates.

        Returns:
            dict: Cart context with items, total, and count
        """
        cart = self.get_cart()

        items = cart.digital_product_items.select_related('product__teacher', 'product__category').all() if cart else []

        return self.get_base_cart_context(
            cart=cart,
            items_queryset=items,
            item_key='digital_product_cart_items',
            total_key='digital_product_cart_total',
            count_key='digital_product_cart_count'
        )

    def clear_cart(self):
        """
        Clear all digital products from cart.

        Returns:
            tuple: (success: bool, message: str)
        """
        is_auth, error = self._require_authentication()
        if not is_auth:
            return False, error

        cart = self.get_cart()
        if not cart:
            return False, "No cart found"

        count = cart.digital_product_items.count()
        cart.digital_product_items.all().delete()
        return True, f"Removed {count} item(s) from cart"
