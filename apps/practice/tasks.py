import logging
import os
import tempfile

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.files import File

from .audio import AudioError, convert_to_m4a, probe
from .models import AudioStatus, PracticeClip

logger = logging.getLogger(__name__)


@shared_task
def process_practice_audio(model_label, pk):
    """Check, convert and publish the audio of a clip or a clip reply.

    model_label is 'practice.PracticeClip' or 'practice.PracticeClipReply'.
    The notification email is sent only once the audio is playable.
    """
    from . import clips as clip_services

    Model = apps.get_model(model_label)
    obj = Model.objects.filter(pk=pk).first()
    if obj is None or obj.status != AudioStatus.PROCESSING or not obj.original_file:
        return

    is_clip = isinstance(obj, PracticeClip)
    if is_clip or not obj.from_teacher:
        max_seconds = settings.PRACTICE_CLIP_MAX_SECONDS
    else:
        max_seconds = settings.PRACTICE_CLIP_REPLY_MAX_SECONDS

    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = obj.original_file.path
            duration = probe(src)
            if duration > max_seconds + settings.PRACTICE_CLIP_DURATION_TOLERANCE:
                raise AudioError(f"The recording is longer than {max_seconds} seconds.")

            dst = os.path.join(tmp, 'audio.m4a')
            convert_to_m4a(src, dst, normalise=settings.PRACTICE_CLIP_NORMALISE)

            with open(dst, 'rb') as fh:
                obj.audio_file.save('audio.m4a', File(fh), save=False)
        obj.duration_seconds = max(1, round(duration))
        obj.status = AudioStatus.READY
        obj.failure_reason = ''
    except AudioError as exc:
        obj.status = AudioStatus.FAILED
        obj.failure_reason = str(exc)
    except Exception:
        logger.exception("Processing %s %s failed", model_label, pk)
        obj.status = AudioStatus.FAILED
        obj.failure_reason = "The recording couldn't be processed."

    old_original = obj.original_file.name
    obj.original_file = ''
    obj.save()
    clip_services.delete_files_on_commit([old_original])

    if obj.status == AudioStatus.FAILED:
        logger.info("Rejected %s %s: %s", model_label, pk, obj.failure_reason)

    if is_clip:
        if obj.entry_id:
            clip_services.notify_teacher_of_ready_clips(obj.entry_id)
    else:
        clip_services.notify_reply_ready(obj)
