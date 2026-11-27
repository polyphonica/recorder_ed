"""
Views for practice clips: student uploads and follow-ups, teacher inbox and
replies, and private audio serving.

Access is always decided by apps.practice.clips.clip_role. Anyone without
access gets a 404, never a 403, so clip IDs can't be probed.
"""

import logging
import mimetypes

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.private_teaching.mixins import TeacherProfileCompletedMixin
from .clips import (
    ClipError, add_reply, clip_json, clip_role, create_clip,
)
from .models import AudioStatus, PracticeClip, PracticeClipReply, PracticeEntry

logger = logging.getLogger(__name__)


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _back(request, fallback):
    nxt = request.POST.get('next') or request.GET.get('next')
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return redirect(nxt)
    return redirect(fallback)


def _error(request, exc, fallback):
    if _is_ajax(request):
        return JsonResponse({'ok': False, 'error': str(exc)}, status=exc.status)
    messages.error(request, str(exc))
    return _back(request, fallback)


def _get_clip(request, pk, roles):
    """The clip if the user has one of `roles` on it, else 404."""
    clip = get_object_or_404(PracticeClip.objects.select_related('entry', 'entry__student', 'entry__teacher'), pk=pk)
    role = clip_role(request.user, clip)
    if role not in roles:
        raise Http404
    return clip, role


# --------------------------------------------------------------------------
# Student side
# --------------------------------------------------------------------------

class UploadPendingClipView(LoginRequiredMixin, View):
    """Upload a clip on Log practice, before the entry exists."""

    def post(self, request):
        try:
            clip = create_clip(request.user, request.FILES.get('audio'), request.POST)
        except ClipError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=exc.status)
        return JsonResponse(clip_json(clip))


class AddClipView(LoginRequiredMixin, View):
    """Upload a clip to an existing entry (Edit practice)."""

    def post(self, request, entry_id):
        entry = get_object_or_404(PracticeEntry, pk=entry_id, student=request.user)
        try:
            clip = create_clip(request.user, request.FILES.get('audio'), request.POST, entry=entry)
        except ClipError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=exc.status)
        return JsonResponse(clip_json(clip))


class ClipStatusView(LoginRequiredMixin, View):
    """Poll a clip's processing status (the recorder shows it on the form)."""

    def get(self, request, pk):
        clip, _ = _get_clip(request, pk, {'student', 'teacher', 'admin'})
        return JsonResponse(clip_json(clip))


class DeleteClipView(LoginRequiredMixin, View):
    """The student or guardian deletes their clip; its files go with it."""

    def post(self, request, pk):
        clip, _ = _get_clip(request, pk, {'student'})
        logger.info("Practice clip %s deleted by user %s", clip.pk, request.user.pk)
        clip.delete()
        if _is_ajax(request):
            return JsonResponse({'ok': True})
        messages.success(request, 'Clip deleted.')
        return _back(request, reverse('practice:practice_log'))


class ToggleKeepClipView(LoginRequiredMixin, View):
    """Exempt a clip from automatic deletion, or undo that."""

    def post(self, request, pk):
        clip, role = _get_clip(request, pk, {'student', 'teacher'})
        clip.keep = not clip.keep
        clip.save(update_fields=['keep'])
        messages.success(request, 'Clip will be kept.' if clip.keep else 'Clip will be deleted automatically after 12 months.')
        fallback = (reverse('practice:teacher_clip_detail', kwargs={'pk': clip.pk}) if role == 'teacher'
                    else reverse('practice:practice_log'))
        return _back(request, fallback)


class AddStudentFollowUpView(LoginRequiredMixin, View):
    """The student or guardian follows up in a clip's thread."""

    def post(self, request, pk):
        clip, role = _get_clip(request, pk, {'student'})
        fallback = reverse('practice:practice_log') + f'#clip-{clip.pk}'
        if clip.is_pending:
            raise Http404
        try:
            add_reply(request.user, clip, role, request.POST.get('text'), request.FILES.get('audio'))
        except ClipError as exc:
            return _error(request, exc, fallback)
        if _is_ajax(request):
            return JsonResponse({'ok': True})
        messages.success(request, 'Follow-up sent to your teacher.')
        return _back(request, fallback)


# --------------------------------------------------------------------------
# Audio serving
# --------------------------------------------------------------------------

def _serve_private_audio(file_field):
    if not file_field:
        raise Http404
    content_type = mimetypes.guess_type(file_field.name)[0] or 'audio/mp4'
    if settings.PRIVATE_MEDIA_X_ACCEL:
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = '/protected/' + file_field.name
    else:
        try:
            response = FileResponse(file_field.open('rb'), content_type=content_type)
        except FileNotFoundError:
            raise Http404
    response['Cache-Control'] = 'private, no-store'
    response['Content-Disposition'] = 'inline'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


class ClipAudioView(LoginRequiredMixin, View):
    def get(self, request, pk):
        clip, _ = _get_clip(request, pk, {'student', 'teacher', 'admin'})
        if clip.status != AudioStatus.READY:
            raise Http404
        return _serve_private_audio(clip.audio_file)


class ClipReplyAudioView(LoginRequiredMixin, View):
    def get(self, request, pk):
        reply = get_object_or_404(PracticeClipReply.objects.select_related('clip', 'clip__entry'), pk=pk)
        if clip_role(request.user, reply.clip) is None or reply.status != AudioStatus.READY:
            raise Http404
        return _serve_private_audio(reply.audio_file)


# --------------------------------------------------------------------------
# Teacher side
# --------------------------------------------------------------------------

def active_student_ids(teacher):
    from lessons.models import Lesson
    return Lesson.objects.filter(
        teacher=teacher, approved_status=Lesson.ApprovalStatus.ACCEPTED, is_deleted=False,
    ).values_list('student_id', flat=True)


def teacher_inbox_clips(teacher):
    """Clips waiting for this teacher: shared, playable, not yet resolved."""
    return PracticeClip.objects.filter(
        entry__teacher=teacher,
        entry__student_id__in=active_student_ids(teacher),
        status=AudioStatus.READY,
        resolved_at__isnull=True,
    )


class TeacherClipInboxView(TeacherProfileCompletedMixin, ListView):
    template_name = 'practice/teacher_clip_inbox.html'
    context_object_name = 'clips'
    paginate_by = 30

    def get_queryset(self):
        return (teacher_inbox_clips(self.request.user)
                .select_related('entry', 'entry__student', 'entry__child_profile')
                .order_by('created_at'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_done'] = (
            PracticeClip.objects.filter(
                entry__teacher=self.request.user,
                entry__student_id__in=active_student_ids(self.request.user),
                resolved_at__isnull=False,
            ).select_related('entry', 'entry__student', 'entry__child_profile')
            .order_by('-resolved_at')[:10]
        )
        return context


class TeacherClipDetailView(TeacherProfileCompletedMixin, TemplateView):
    template_name = 'practice/teacher_clip_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clip, _ = _get_clip(self.request, kwargs['pk'], {'teacher'})
        now = timezone.now()
        if clip.teacher_listened_at is None and clip.status == AudioStatus.READY:
            clip.teacher_listened_at = now
            clip.save(update_fields=['teacher_listened_at'])
        clip.replies.filter(from_teacher=False, read_at__isnull=True).update(read_at=now)

        entry = clip.entry
        context.update({
            'clip': clip,
            'entry': entry,
            'replies': clip.replies.select_related('author'),
            'earlier_clips': PracticeClip.objects.filter(
                entry__student=entry.student,
                entry__teacher=self.request.user,
                entry__child_profile=entry.child_profile,
                title__iexact=clip.title,
                status=AudioStatus.READY,
                created_at__lt=clip.created_at,
            ).select_related('entry').order_by('-created_at')[:5],
            'reply_max_seconds': settings.PRACTICE_CLIP_REPLY_MAX_SECONDS,
            'max_upload_mb': settings.PRACTICE_CLIP_MAX_UPLOAD_MB,
        })
        return context


class AddClipReplyView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk):
        clip, role = _get_clip(request, pk, {'teacher'})
        fallback = reverse('practice:teacher_clip_detail', kwargs={'pk': clip.pk})
        try:
            add_reply(request.user, clip, role, request.POST.get('text'), request.FILES.get('audio'))
        except ClipError as exc:
            return _error(request, exc, fallback)
        if _is_ajax(request):
            return JsonResponse({'ok': True})
        messages.success(request, 'Reply sent.')
        return _back(request, fallback)


class MarkClipDoneView(TeacherProfileCompletedMixin, View):
    """Take a clip out of the inbox without replying (e.g. 'will cover in lesson')."""

    def post(self, request, pk):
        clip, _ = _get_clip(request, pk, {'teacher'})
        now = timezone.now()
        clip.resolved_at = now
        if clip.teacher_listened_at is None:
            clip.teacher_listened_at = now
        clip.save(update_fields=['resolved_at', 'teacher_listened_at'])
        messages.success(request, f'"{clip.title}" marked as done.')
        return _back(request, reverse('practice:teacher_clip_inbox'))
