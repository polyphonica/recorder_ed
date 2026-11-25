"""Duplicate a workshop as a new draft, optionally with its sessions and materials.

Used by DuplicateWorkshopView. Kept separate so the copying rules live in one place.
"""
import logging
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from .models import Workshop, WorkshopMaterial, WorkshopSession

logger = logging.getLogger(__name__)

# Workshop fields carried over to the copy. Status, featured flag, publish date and
# counters are deliberately left out: the copy starts as a fresh, unfeatured draft.
WORKSHOP_COPY_FIELDS = [
    'description', 'short_description',
    'learning_objectives', 'prerequisites', 'materials_needed',
    'category_id', 'tags', 'difficulty_level',
    'duration_value', 'duration_unit',
    'promo_video_url',
    'is_free', 'price',
    'is_series', 'series_price', 'series_description',
    'require_full_series_registration',
    'delivery_method',
    'venue_name', 'venue_address', 'venue_city', 'venue_postcode',
    'venue_map_link', 'venue_notes', 'max_venue_capacity',
]

# Session fields carried over. Not copied: registrations/counts, cancellation state,
# recordings, and meeting link/ID/password (an old meeting link sent out in reminder
# emails for a new date is worse than a blank one the instructor has to fill in).
SESSION_COPY_FIELDS = [
    'session_title', 'timezone_name', 'max_participants', 'waitlist_enabled',
    'session_notes', 'session_delivery_override', 'session_venue_notes',
]

MATERIAL_COPY_FIELDS = [
    'title', 'description', 'material_type', 'external_url', 'access_timing',
    'is_downloadable', 'requires_registration', 'order', 'is_featured',
]


def unique_workshop_slug(title):
    max_len = Workshop._meta.get_field('slug').max_length
    base = (slugify(title) or 'workshop')[:max_len - 4].strip('-')
    candidate, counter = base, 2
    while Workshop.objects.filter(slug=candidate).exists():
        candidate = f'{base}-{counter}'
        counter += 1
    return candidate


def copy_file(field_file):
    """Return a ContentFile copy of a stored file, or None if it can't be read.

    The copy gets its own file on disk, so deleting or replacing it on one
    workshop never affects the other.
    """
    if not field_file:
        return None
    try:
        with field_file.open('rb') as f:
            return ContentFile(f.read(), name=os.path.basename(field_file.name))
    except (OSError, ValueError) as e:
        logger.warning(f"Could not copy file {field_file.name}: {e}")
        return None


def _copy_name(name):
    """A fresh filename for a copied image that keeps any `_optimized.jpg` ending.

    The pre_save optimizer skips files ending in `_optimized.jpg`. If storage had to
    de-duplicate the name it would add a suffix after that ending, and the already
    optimized image would be needlessly recompressed.
    """
    marker = '_optimized.jpg'
    if name.endswith(marker):
        return f'{name[:-len(marker)]}-{uuid.uuid4().hex[:8]}{marker}'
    return name


def _zone(name):
    try:
        return ZoneInfo(name or 'UTC')
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo('UTC')


def shift_datetime(dt, days, tz_name):
    """Move `dt` by whole days, keeping the same local clock time in `tz_name`.

    Shifting in local time (not UTC) means a 10:00 session in October stays at
    10:00 when copied into, say, January, despite the clocks changing.
    """
    zone = _zone(tz_name)
    local = dt.astimezone(zone).replace(tzinfo=None) + timedelta(days=days)
    return local.replace(tzinfo=zone)


def source_sessions(workshop):
    """Sessions worth copying: active and not cancelled, earliest first."""
    return list(
        workshop.sessions.filter(is_active=True, is_cancelled=False).order_by('start_datetime')
    )


@transaction.atomic
def duplicate_workshop(original, title, first_session_date=None, copy_materials=False):
    """Create a draft copy of `original` owned by the same instructor.

    first_session_date: if given, copy the original's sessions so the earliest one
        falls on this date; the others keep the same spacing and times of day.
    copy_materials: copy workshop-wide materials, plus session materials for any
        sessions that were copied.
    """
    new = Workshop(
        instructor=original.instructor,
        title=title,
        slug=unique_workshop_slug(title),
        status=Workshop.Status.DRAFT,
        is_featured=False,
    )
    for field in WORKSHOP_COPY_FIELDS:
        setattr(new, field, getattr(original, field))

    image = copy_file(original.featured_image)
    if image:
        new.featured_image.save(_copy_name(image.name), image, save=False)
    new.save()

    session_map = {}
    if first_session_date:
        sessions = source_sessions(original)
        if sessions:
            first = sessions[0]
            first_local_date = first.start_datetime.astimezone(_zone(first.timezone_name)).date()
            days = (first_session_date - first_local_date).days
            for old in sessions:
                copy = WorkshopSession(
                    workshop=new,
                    start_datetime=shift_datetime(old.start_datetime, days, old.timezone_name),
                    end_datetime=shift_datetime(old.end_datetime, days, old.timezone_name),
                )
                for field in SESSION_COPY_FIELDS:
                    setattr(copy, field, getattr(old, field))
                copy.save()
                session_map[old.pk] = copy

    if copy_materials:
        for material in original.materials.all():
            if material.session_id and material.session_id not in session_map:
                continue  # belongs to a session that wasn't copied
            copy = WorkshopMaterial(workshop=new, session=session_map.get(material.session_id))
            for field in MATERIAL_COPY_FIELDS:
                setattr(copy, field, getattr(material, field))
            file_copy = copy_file(material.file)
            if material.file and not file_copy:
                continue  # file missing on disk; skip rather than create a broken material
            if file_copy:
                copy.file.save(file_copy.name, file_copy, save=False)
            copy.save()

    return new
