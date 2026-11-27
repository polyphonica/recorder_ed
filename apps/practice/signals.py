from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import PracticeClip, PracticeClipReply


@receiver(post_delete, sender=PracticeClip)
@receiver(post_delete, sender=PracticeClipReply)
def delete_clip_files(sender, instance, **kwargs):
    """Remove the audio files when a clip or reply is deleted, including by
    cascade from a practice entry or an account."""
    from .clips import delete_files_on_commit, files_of
    delete_files_on_commit(files_of(instance))
