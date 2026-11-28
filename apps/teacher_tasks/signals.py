"""When a linked item is deleted, keep the task but drop the link."""
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete)
def drop_task_links(sender, instance, **kwargs):
    from .links import linkable_models
    from .models import Task
    model = sender._meta.concrete_model if hasattr(sender, '_meta') else None
    if model is None or model not in linkable_models():
        return
    Task.objects.filter(
        content_type=ContentType.objects.get_for_model(model), object_id=str(instance.pk)
    ).update(content_type=None, object_id='')
