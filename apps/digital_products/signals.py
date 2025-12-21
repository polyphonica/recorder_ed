from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProductReview


@receiver(post_save, sender=ProductReview)
def update_product_rating(sender, instance, **kwargs):
    """
    Update product average rating and review count when a review is saved.
    This keeps denormalized rating stats in sync.
    """
    instance.product.update_rating_stats()
