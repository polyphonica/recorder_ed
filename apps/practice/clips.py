"""
Practice clip services: access rules, creating clips and replies, linking
pending clips, notifications and file clean-up. Views stay thin.
"""

import logging
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from lessons.models import Lesson
from .models import AudioStatus, PracticeClip, PracticeClipReply, PracticeEntry, private_storage

logger = logging.getLogger(__name__)


class ClipError(Exception):
    """A request we refuse. The message is safe to show the user."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------
# Access
# --------------------------------------------------------------------------

def teacher_has_active_relationship(teacher, student):
    """True while the teacher has an accepted, non-deleted lesson with the student."""
    return Lesson.objects.filter(
        teacher=teacher,
        student=student,
        approved_status=Lesson.ApprovalStatus.ACCEPTED,
        is_deleted=False,
    ).exists()


def clip_role(user, clip):
    """'student', 'teacher', 'admin' or None for this user and clip.

    Student means the entry's student (adult or guardian), or the uploader of
    a pending clip. A teacher has access only while the relationship lasts.
    """
    if not user.is_authenticated:
        return None
    entry = clip.entry
    if entry is None:
        if clip.uploaded_by_id == user.id:
            return 'student'
    else:
        if entry.student_id == user.id:
            return 'student'
        if entry.teacher_id == user.id and teacher_has_active_relationship(user, entry.student):
            return 'teacher'
    if user.is_superuser:
        return 'admin'
    return None


def clip_json(clip):
    """What the recorder component needs to show a clip on the entry form."""
    from django.urls import reverse
    return {
        'ok': True,
        'id': str(clip.pk),
        'title': clip.title,
        'kind': clip.get_kind_display(),
        'note': clip.note,
        'status': clip.status,
        'failure_reason': clip.failure_reason,
        'duration_seconds': clip.duration_seconds,
        'audio_url': reverse('practice:clip_audio', kwargs={'pk': clip.pk})
        if clip.status == AudioStatus.READY else None,
        'delete_url': reverse('practice:delete_clip', kwargs={'pk': clip.pk}),
    }


# --------------------------------------------------------------------------
# Limits
# --------------------------------------------------------------------------

def check_rate_limit(user, action, per_hour):
    """Count an action for this user in the current hour; refuse over the limit."""
    bucket = int(time.time() // 3600)
    key = f'practice_clips:{action}:{user.id}:{bucket}'
    cache.add(key, 0, timeout=3700)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=3700)
        count = 1
    if count > per_hour:
        raise ClipError("You've sent a lot of recordings in the last hour. Please try again later.", status=429)


def check_upload(uploaded_file):
    if uploaded_file is None:
        raise ClipError("No recording was received.")
    max_bytes = settings.PRACTICE_CLIP_MAX_UPLOAD_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ClipError(f"The recording is larger than {settings.PRACTICE_CLIP_MAX_UPLOAD_MB} MB.", status=413)
    if uploaded_file.size == 0:
        raise ClipError("The recording is empty.")


def clean_clip_fields(data):
    kind = data.get('kind') or PracticeClip.Kind.PIECE
    if kind not in PracticeClip.Kind.values:
        raise ClipError("Please choose what the clip is.")
    title = (data.get('title') or '').strip()[:200]
    if not title:
        raise ClipError("Please give the clip a title.")
    note = (data.get('note') or '').strip()[:2000]
    return {'kind': kind, 'title': title, 'note': note}


# --------------------------------------------------------------------------
# Creating clips and replies
# --------------------------------------------------------------------------

def _queue_processing(obj):
    from .tasks import process_practice_audio
    label = f'practice.{obj.__class__.__name__}'
    transaction.on_commit(lambda: process_practice_audio.delay(label, str(obj.pk)))


def create_clip(user, uploaded_file, data, entry=None):
    """Create a clip on an entry, or a pending clip when entry is None."""
    check_upload(uploaded_file)
    fields = clean_clip_fields(data)
    check_rate_limit(user, 'upload', settings.PRACTICE_CLIP_UPLOADS_PER_HOUR)

    with transaction.atomic():
        if entry is not None:
            # Lock the entry so two quick uploads can't both pass the count
            PracticeEntry.objects.select_for_update().get(pk=entry.pk)
            if entry.clips.count() >= settings.PRACTICE_CLIP_MAX_PER_ENTRY:
                raise ClipError(f"An entry can have at most {settings.PRACTICE_CLIP_MAX_PER_ENTRY} clips.")
        else:
            # Lock the user's row to serialise their pending uploads
            get_user_model().objects.select_for_update().get(pk=user.pk)
            pending = PracticeClip.objects.filter(uploaded_by=user, entry__isnull=True).count()
            if pending >= settings.PRACTICE_CLIP_MAX_PENDING:
                raise ClipError("Please save your practice entry before adding more clips.")

        clip = PracticeClip(entry=entry, uploaded_by=user, status=AudioStatus.PROCESSING, **fields)
        clip.original_file.save(uploaded_file.name or 'clip', uploaded_file, save=False)
        clip.save()
        _queue_processing(clip)
    return clip


def link_pending_clips(user, entry, clip_ids):
    """Attach the user's pending clips to a newly saved entry (up to the limit)."""
    if not clip_ids:
        return 0
    with transaction.atomic():
        PracticeEntry.objects.select_for_update().get(pk=entry.pk)
        room = settings.PRACTICE_CLIP_MAX_PER_ENTRY - entry.clips.count()
        if room <= 0:
            return 0
        ids = list(
            PracticeClip.objects.filter(id__in=clip_ids, uploaded_by=user, entry__isnull=True)
            .order_by('created_at').values_list('id', flat=True)[:room]
        )
        PracticeClip.objects.filter(id__in=ids).update(entry=entry)
    if ids:
        transaction.on_commit(lambda: notify_teacher_of_ready_clips(entry.pk))
    return len(ids)


def add_reply(user, clip, role, text, uploaded_file=None):
    """Add a teacher reply or a student follow-up to a clip's thread."""
    text = (text or '').strip()[:5000]
    if not text and uploaded_file is None:
        raise ClipError("Please write a reply or record one.")
    if uploaded_file is not None:
        check_upload(uploaded_file)
    check_rate_limit(user, 'reply', settings.PRACTICE_CLIP_REPLIES_PER_HOUR)

    from_teacher = role == 'teacher'
    now = timezone.now()
    with transaction.atomic():
        reply = PracticeClipReply(
            clip=clip, author=user, from_teacher=from_teacher, text=text,
            status=AudioStatus.PROCESSING if uploaded_file is not None else AudioStatus.NONE,
        )
        if uploaded_file is not None:
            reply.original_file.save(uploaded_file.name or 'reply', uploaded_file, save=False)
        reply.save()

        updates = {'last_activity_at': now}
        if from_teacher:
            updates['resolved_at'] = now
            if clip.teacher_listened_at is None:
                updates['teacher_listened_at'] = now
        else:
            updates['resolved_at'] = None  # back in the teacher's inbox
        PracticeClip.objects.filter(pk=clip.pk).update(**updates)

        if uploaded_file is not None:
            _queue_processing(reply)
        else:
            transaction.on_commit(lambda: notify_reply_ready(reply))
    return reply


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------

def notify_teacher_of_ready_clips(entry_id):
    """Email the teacher once per batch, when no clip on the entry is still processing."""
    from .notifications import PracticeNotificationService

    with transaction.atomic():
        entry = PracticeEntry.objects.select_for_update().filter(pk=entry_id).first()
        if entry is None:
            return
        clips = entry.clips.all()
        if clips.filter(status=AudioStatus.PROCESSING).exists():
            return
        to_announce = list(clips.filter(status=AudioStatus.READY, teacher_notified_at__isnull=True))
        if not to_announce:
            return
        PracticeClip.objects.filter(pk__in=[c.pk for c in to_announce]).update(teacher_notified_at=timezone.now())

    PracticeNotificationService.send_clips_shared_notification(entry, to_announce)


def notify_reply_ready(reply):
    """Email the other party about a reply once it can be seen."""
    from .notifications import PracticeNotificationService

    if not reply.is_visible:
        return  # audio-only reply that failed: the author sees the failure instead
    if reply.from_teacher:
        PracticeNotificationService.send_clip_reply_notification(reply)
    else:
        PracticeNotificationService.send_clip_followup_notification(reply)


# --------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------

def delete_files_on_commit(names):
    """Delete private files once the surrounding transaction has committed."""
    names = [n for n in names if n]
    if not names:
        return

    def _delete():
        storage = private_storage()
        for name in names:
            try:
                storage.delete(name)
            except OSError:
                logger.warning("Could not delete private file %s", name)

    transaction.on_commit(_delete)


def files_of(obj):
    return [obj.original_file.name, obj.audio_file.name]
