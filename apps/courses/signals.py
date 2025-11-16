"""
Signal handlers to keep Course denormalized counts up to date.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Course, Topic, Lesson


@receiver(post_save, sender=Topic)
@receiver(post_delete, sender=Topic)
def update_course_on_topic_change(sender, instance, **kwargs):
    """Update course counts when a topic is added, modified, or deleted"""
    if instance.course:
        instance.course.update_counts()


@receiver(post_save, sender=Lesson)
@receiver(post_delete, sender=Lesson)
def update_course_on_lesson_change(sender, instance, **kwargs):
    """Update course counts when a lesson is added, modified, or deleted"""
    if instance.topic and instance.topic.course:
        instance.topic.course.update_counts()
