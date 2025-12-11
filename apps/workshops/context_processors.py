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
        # PERFORMANCE FIX: Use annotate to get counts in single query
        from django.db.models import Count
        cart = Cart.objects.annotate(
            workshop_count=Count('workshop_items'),
            lesson_count=Count('items')
        ).get(user=request.user)

        total_count = cart.workshop_count + cart.lesson_count

        return {
            'total_cart_count': total_count,
            'workshop_cart_count': cart.workshop_count,
            'lesson_cart_count': cart.lesson_count,
        }
    except Cart.DoesNotExist:
        return {
            'total_cart_count': 0,
            'workshop_cart_count': 0,
            'lesson_cart_count': 0,
        }
