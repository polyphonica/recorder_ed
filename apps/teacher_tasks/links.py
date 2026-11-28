"""
What a task can be linked to, which area of teaching that is, where the
link goes, and whether a teacher may link to it.
"""
from functools import lru_cache

from django.contrib.auth import get_user_model
from django.urls import reverse


def _student_allowed(user, student):
    from lessons.models import Lesson
    return Lesson.objects.filter(
        teacher=user, student=student,
        approved_status=Lesson.ApprovalStatus.ACCEPTED, is_deleted=False,
    ).exists()


@lru_cache(maxsize=1)
def _registry():
    from apps.audioplayer.models import Piece, PieceCollection
    from apps.courses.models import Course
    from apps.digital_products.models import DigitalProduct
    from apps.workshops.models import Workshop
    User = get_user_model()
    return {
        User: {
            'area': 'private_teaching',
            'icon': 'fa-user',
            'label': lambda o: o.get_full_name() or o.username,
            'url': lambda o: reverse('private_teaching:teacher_student_progress', kwargs={'student_id': o.pk}),
            'allowed': _student_allowed,
        },
        Workshop: {
            'area': 'workshops',
            'icon': 'fa-chalkboard-teacher',
            'label': str,
            'url': lambda o: reverse('workshops:manage_sessions', kwargs={'slug': o.slug}),
            'allowed': lambda user, o: o.instructor_id == user.pk,
        },
        Course: {
            'area': 'courses',
            'icon': 'fa-graduation-cap',
            'label': str,
            'url': lambda o: reverse('courses:edit', kwargs={'slug': o.slug}),
            'allowed': lambda user, o: o.instructor_id == user.pk,
        },
        DigitalProduct: {
            'area': 'products',
            'icon': 'fa-box',
            'label': str,
            'url': lambda o: reverse('digital_products:edit_product', kwargs={'product_id': o.pk}),
            'allowed': lambda user, o: o.teacher_id == user.pk,
        },
        Piece: {
            'area': 'playalongs',
            'icon': 'fa-music',
            'label': str,
            'url': lambda o: reverse('audioplayer:piece_edit', kwargs={'pk': o.pk}),
            'allowed': lambda user, o: o.created_by_id == user.pk,
        },
        PieceCollection: {
            'area': 'playalongs',
            'icon': 'fa-folder-open',
            'label': str,
            'url': lambda o: reverse('audioplayer:collection_detail', kwargs={'pk': o.pk}),
            'allowed': lambda user, o: o.created_by_id == user.pk,
        },
    }


def link_info(obj):
    """The registry entry for obj's model, or None if tasks can't link to it."""
    if obj is None:
        return None
    return _registry().get(type(obj)._meta.concrete_model)


def linkable_models():
    return list(_registry().keys())
