"""
Context processors for private teaching app
"""
from .cart import CartManager


def cart_context(request):
    """Add cart context to all templates"""
    if request.user.is_authenticated:
        # Only add cart context for private teaching pages
        if hasattr(request, 'resolver_match') and request.resolver_match and request.resolver_match.namespace == 'private_teaching':
            cart_manager = CartManager(request)
            cart_context = cart_manager.get_cart_context()
            return {
                'cart_count': cart_context['cart_count'],
                'cart_total': cart_context['cart_total'],
                'cart_lesson_ids': [item.lesson.id for item in cart_context['cart_items']],
            }

    return {
        'cart_count': 0,
        'cart_total': 0,
        'cart_lesson_ids': [],
    }