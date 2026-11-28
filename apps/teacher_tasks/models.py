import datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class TaskQuerySet(models.QuerySet):
    def open(self):
        return self.filter(done_at__isnull=True)

    def done(self):
        return self.filter(done_at__isnull=False)

    def due_by_today(self):
        return self.open().filter(due_date__lte=timezone.localdate())

    def for_object(self, obj):
        return self.filter(content_type=ContentType.objects.get_for_model(obj), object_id=str(obj.pk))


class Task(models.Model):
    """A teacher's own to-do item, optionally linked to something on the site."""

    class Area(models.TextChoices):
        GENERAL = 'general', 'General'
        PRIVATE_TEACHING = 'private_teaching', 'Private Lessons'
        WORKSHOPS = 'workshops', 'Workshops'
        COURSES = 'courses', 'Courses'
        PLAYALONGS = 'playalongs', 'Play-Alongs'
        PRODUCTS = 'products', 'Digital Products'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_tasks')
    title = models.CharField(max_length=300)
    notes = models.TextField(blank=True)
    area = models.CharField(max_length=30, choices=Area.choices, default=Area.GENERAL)
    due_date = models.DateField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)

    # Optional link to a student, workshop, course, product, piece or collection
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=64, blank=True)
    linked = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ['done_at', models.F('due_date').asc(nulls_last=True), 'created_at']
        indexes = [models.Index(fields=['owner', 'done_at', 'due_date'])]

    def __str__(self):
        return self.title

    @property
    def is_done(self):
        return self.done_at is not None

    @property
    def is_overdue(self):
        return not self.is_done and self.due_date is not None and self.due_date < timezone.localdate()

    @property
    def group(self):
        """Which heading the task appears under on the Tasks page."""
        if self.is_done:
            return 'done'
        if self.due_date is None:
            return 'later'
        today = timezone.localdate()
        if self.due_date < today:
            return 'overdue'
        if self.due_date == today:
            return 'today'
        if self.due_date <= today + datetime.timedelta(days=7):
            return 'week'
        return 'later'

    def set_link(self, obj):
        from .links import link_info
        if obj is None:
            self.content_type, self.object_id = None, ''
            return
        self.content_type = ContentType.objects.get_for_model(obj)
        self.object_id = str(obj.pk)
        info = link_info(obj)
        if info and self.area == self.Area.GENERAL:
            self.area = info['area']

    @property
    def link(self):
        """{'label', 'url', 'icon'} for the linked item, or None if there isn't one any more."""
        from .links import link_info
        if not self.content_type_id:
            return None
        try:
            obj = self.linked
        except Exception:
            return None
        info = link_info(obj)
        if not info:
            return None
        return {'label': info['label'](obj), 'url': info['url'](obj), 'icon': info['icon']}
