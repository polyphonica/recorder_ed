"""
Context processors for workshops app - provides unified cart data
"""
from apps.private_teaching.models import Cart


def unified_cart_context(request):
    """
    Add unified cart context (workshops + lessons) to all templates.
    This provides cart counts for the navbar regardless of which section user is in.
    """
    if not request.user.is_authenticated:
        return {
            'total_cart_count': 0,
            'workshop_cart_count': 0,
            'lesson_cart_count': 0,
        }

    try:
        cart = Cart.objects.get(user=request.user)
        workshop_count = cart.workshop_items.count()
        lesson_count = cart.items.count()
        total_count = workshop_count + lesson_count

        return {
            'total_cart_count': total_count,
            'workshop_cart_count': workshop_count,
            'lesson_cart_count': lesson_count,
        }
    except Cart.DoesNotExist:
        return {
            'total_cart_count': 0,
            'workshop_cart_count': 0,
            'lesson_cart_count': 0,
        }
