from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Message


@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, created, **kwargs):
    """Keep Conversation.updated_at current so inbox sorts by last message."""
    if created:
        instance.conversation.__class__.objects.filter(
            pk=instance.conversation_id
        ).update(updated_at=timezone.now())
