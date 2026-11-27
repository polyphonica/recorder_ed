"""
Tests for practice clips: upload, processing, access, replies, limits,
notifications and clean-up.

Processing tests need ffmpeg/ffprobe and are skipped without them.
Celery runs tasks eagerly in tests (CELERY_TASK_ALWAYS_EAGER).
"""

import os
import shutil
import subprocess
import tempfile
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.private_teaching.models import LessonRequest, Subject
from apps.practice.models import AudioStatus, PracticeClip, PracticeClipReply, PracticeEntry
from lessons.models import Lesson

User = get_user_model()



def ffmpeg_works():
    """True if ffmpeg and ffprobe are installed and actually run."""
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            return False
        try:
            if subprocess.run([tool, '-version'], capture_output=True, timeout=10).returncode != 0:
                return False
        except (OSError, subprocess.TimeoutExpired):
            return False
    return True


HAS_FFMPEG = ffmpeg_works()
AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


def make_audio(directory, name, seconds, codec_args):
    path = os.path.join(directory, name)
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
         *codec_args, path],
        check=True, capture_output=True,
    )
    with open(path, 'rb') as fh:
        return fh.read()


class ClipTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.audio_dir = tempfile.mkdtemp()
        if HAS_FFMPEG:
            cls.webm = make_audio(cls.audio_dir, 'short.webm', 3, ['-c:a', 'libopus'])
            cls.m4a = make_audio(cls.audio_dir, 'short.m4a', 3, ['-c:a', 'aac'])
            cls.long_webm = make_audio(cls.audio_dir, 'long.webm', 100, ['-c:a', 'libopus', '-b:a', '16k'])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.audio_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.private_root = tempfile.mkdtemp()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.private_root,
                                                   PRIVATE_MEDIA_X_ACCEL=False)
        self.settings_override.enable()

        self.teacher = self.make_user('teacher', teacher=True)
        self.other_teacher = self.make_user('otherteacher', teacher=True)
        self.student = self.make_user('student')
        self.other_student = self.make_user('otherstudent')

        self.lesson = self.make_lesson(self.teacher, self.student)
        self.make_lesson(self.other_teacher, self.other_student)

        self.entry = PracticeEntry.objects.create(
            student=self.student, teacher=self.teacher,
            practice_date=date.today(), duration_minutes=30,
        )

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.private_root, ignore_errors=True)

    # -- helpers -----------------------------------------------------------

    def make_user(self, username, teacher=False):
        user = User.objects.create_user(username=username, email=f'{username}@example.com',
                                        password='pw', first_name=username.title())
        profile = user.profile
        profile.is_teacher = teacher
        profile.is_student = not teacher
        profile.profile_completed = True
        profile.save()
        return user

    def make_lesson(self, teacher, student):
        subject = Subject.objects.create(teacher=teacher, subject='Recorder', base_price_60min=50)
        request = LessonRequest.objects.create(student=student)
        return Lesson.objects.create(
            lesson_request=request, subject=subject, student=student, teacher=teacher,
            lesson_date=date.today(), lesson_time=time(10, 0),
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
        )

    def upload(self, url, data=b'', name='clip.webm', title='G major scale', **extra):
        payload = {'kind': 'scale', 'title': title, 'note': 'bars 1-4',
                   'audio': SimpleUploadedFile(name, data, content_type='audio/webm')}
        payload.update(extra)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, payload, **AJAX)

    def add_clip(self, data=None, entry=None):
        self.client.force_login(self.student)
        entry = entry or self.entry
        response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': entry.pk}),
                               data if data is not None else self.webm)
        self.assertEqual(response.status_code, 200, response.content)
        return PracticeClip.objects.get(pk=response.json()['id'])

    def private_path(self, name):
        return os.path.join(self.private_root, name)

    def make_ready_clip(self, title='G major scale', entry=None):
        """A processed clip, created directly (no ffmpeg needed)."""
        clip = PracticeClip.objects.create(
            entry=entry or self.entry, uploaded_by=self.student, title=title, kind='scale',
            status=AudioStatus.READY, duration_seconds=3, teacher_notified_at=timezone.now(),
        )
        clip.audio_file.save('clip.m4a', SimpleUploadedFile('clip.m4a', b'fake audio'))
        return clip


# --------------------------------------------------------------------------
# Upload and processing
# --------------------------------------------------------------------------

class ClipProcessingTests(ClipTestBase):
    def setUp(self):
        if not HAS_FFMPEG:
            self.skipTest('ffmpeg not installed')
        super().setUp()

    def test_webm_and_m4a_convert_to_playable_m4a(self):
        for data, name in ((self.webm, 'a.webm'), (self.m4a, 'b.m4a')):
            self.client.force_login(self.student)
            response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}),
                                   data, name=name, title=name)
            clip = PracticeClip.objects.get(pk=response.json()['id'])
            self.assertEqual(clip.status, AudioStatus.READY, clip.failure_reason)
            self.assertTrue(clip.audio_file.name.endswith('.m4a'))
            self.assertIn(clip.duration_seconds, (3, 4))
            self.assertEqual(clip.original_file.name, '')
            self.assertTrue(os.path.exists(self.private_path(clip.audio_file.name)))

    def test_over_length_recording_rejected_after_processing(self):
        clip = self.add_clip(self.long_webm)
        self.assertEqual(clip.status, AudioStatus.FAILED)
        self.assertIn('longer than', clip.failure_reason)
        self.assertEqual(len(mail.outbox), 0)

    def test_non_audio_file_rejected(self):
        clip = self.add_clip(b'%PDF-1.4 definitely not audio' * 50)
        self.assertEqual(clip.status, AudioStatus.FAILED)
        self.assertEqual(clip.original_file.name, '')

    def test_files_not_stored_under_public_media(self):
        from django.conf import settings
        clip = self.add_clip()
        self.assertTrue(self.private_path(clip.audio_file.name).startswith(self.private_root))
        self.assertFalse(str(settings.MEDIA_ROOT) in self.private_path(clip.audio_file.name))


class ClipLimitTests(ClipTestBase):
    def setUp(self):
        if not HAS_FFMPEG:
            self.skipTest('ffmpeg not installed')
        super().setUp()

    def test_fourth_clip_rejected(self):
        for _ in range(3):
            self.add_clip()
        response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}), self.webm)
        self.assertEqual(response.status_code, 400)
        self.assertIn('at most 3', response.json()['error'])
        self.assertEqual(self.entry.clips.count(), 3)

    @override_settings(PRACTICE_CLIP_MAX_UPLOAD_MB=0)
    def test_oversize_upload_rejected_before_saving(self):
        self.client.force_login(self.student)
        response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}), self.webm)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(PracticeClip.objects.count(), 0)

    @override_settings(PRACTICE_CLIP_UPLOADS_PER_HOUR=1)
    def test_rate_limit(self):
        self.add_clip()
        response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}), self.webm)
        self.assertEqual(response.status_code, 429)

    def test_missing_title_rejected(self):
        self.client.force_login(self.student)
        response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}),
                               self.webm, title='   ')
        self.assertEqual(response.status_code, 400)


# --------------------------------------------------------------------------
# Pending clips on Log practice
# --------------------------------------------------------------------------

class PendingClipTests(ClipTestBase):
    def setUp(self):
        if not HAS_FFMPEG:
            self.skipTest('ffmpeg not installed')
        super().setUp()

    def upload_pending(self, user, title='Pending'):
        self.client.force_login(user)
        response = self.upload(reverse('practice:upload_pending_clip'), self.webm, title=title)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['id']

    def log_practice(self, clip_ids):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('practice:log_practice'), {
                'practice_date': date.today().isoformat(),
                'duration_minutes': 20,
                'teacher': self.teacher.pk,
                'pending_clip_ids': clip_ids,
            })

    def test_pending_clips_linked_on_save_with_one_email(self):
        ids = [self.upload_pending(self.student, 'One'), self.upload_pending(self.student, 'Two')]
        self.assertEqual(len(mail.outbox), 0)  # no entry yet, so no email

        response = self.log_practice(ids)
        self.assertEqual(response.status_code, 302)
        entry = PracticeEntry.objects.exclude(pk=self.entry.pk).get()
        self.assertEqual(set(str(i) for i in entry.clips.values_list('id', flat=True)), set(ids))

        clip_emails = [m for m in mail.outbox if 'clip' in m.subject]
        self.assertEqual(len(clip_emails), 1)
        self.assertIn('2 practice clips', clip_emails[0].subject)
        self.assertEqual(clip_emails[0].to, [self.teacher.email])

    def test_cannot_link_someone_elses_pending_clip(self):
        clip_id = self.upload_pending(self.other_student)
        self.client.force_login(self.student)
        self.log_practice([clip_id])
        self.assertIsNone(PracticeClip.objects.get(pk=clip_id).entry)

    def test_pending_clip_only_visible_to_uploader(self):
        clip_id = self.upload_pending(self.student)
        url = reverse('practice:clip_audio', kwargs={'pk': clip_id})
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_abandoned_pending_clips_purged(self):
        clip_id = self.upload_pending(self.student)
        clip = PracticeClip.objects.get(pk=clip_id)
        path = self.private_path(clip.audio_file.name)
        PracticeClip.objects.filter(pk=clip_id).update(created_at=timezone.now() - timedelta(hours=25))
        with self.captureOnCommitCallbacks(execute=True):
            call_command('purge_practice_clips', stdout=open(os.devnull, 'w'))
        self.assertFalse(PracticeClip.objects.filter(pk=clip_id).exists())
        self.assertFalse(os.path.exists(path))


# --------------------------------------------------------------------------
# Access
# --------------------------------------------------------------------------

class ClipAccessTests(ClipTestBase):
    def setUp(self):
        super().setUp()
        self.clip = self.make_ready_clip()
        self.audio_url = reverse('practice:clip_audio', kwargs={'pk': self.clip.pk})

    def get_as(self, user, url):
        if user is None:
            self.client.logout()
        else:
            self.client.force_login(user)
        response = self.client.get(url)
        if hasattr(response, 'streaming_content'):
            response.close()
        return response.status_code

    def test_audio_access(self):
        self.assertEqual(self.get_as(self.student, self.audio_url), 200)
        self.assertEqual(self.get_as(self.teacher, self.audio_url), 200)
        self.assertEqual(self.get_as(self.other_teacher, self.audio_url), 404)
        self.assertEqual(self.get_as(self.other_student, self.audio_url), 404)
        self.assertEqual(self.get_as(None, self.audio_url), 302)

    def test_audio_headers(self):
        self.client.force_login(self.student)
        response = self.client.get(self.audio_url)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        response.close()

    @override_settings(PRIVATE_MEDIA_X_ACCEL=True)
    def test_x_accel_redirect_in_production(self):
        self.client.force_login(self.student)
        response = self.client.get(self.audio_url)
        self.assertEqual(response['X-Accel-Redirect'], '/protected/' + self.clip.audio_file.name)
        self.assertEqual(response.content, b'')

    def test_former_teacher_loses_access(self):
        self.lesson.is_deleted = True
        self.lesson.save()
        self.assertEqual(self.get_as(self.teacher, self.audio_url), 404)
        detail = reverse('practice:teacher_clip_detail', kwargs={'pk': self.clip.pk})
        self.assertEqual(self.get_as(self.teacher, detail), 404)

    def test_teacher_detail_only_for_entry_teacher(self):
        detail = reverse('practice:teacher_clip_detail', kwargs={'pk': self.clip.pk})
        self.assertEqual(self.get_as(self.teacher, detail), 200)
        self.assertEqual(self.get_as(self.other_teacher, detail), 404)

    def test_only_owner_can_delete(self):
        url = reverse('practice:delete_clip', kwargs={'pk': self.clip.pk})
        for user in (self.teacher, self.other_student):
            self.client.force_login(user)
            self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(PracticeClip.objects.filter(pk=self.clip.pk).exists())

        path = self.private_path(self.clip.audio_file.name)
        self.client.force_login(self.student)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url)
        self.assertFalse(PracticeClip.objects.filter(pk=self.clip.pk).exists())
        self.assertFalse(os.path.exists(path))

    def test_cannot_add_clip_to_someone_elses_entry(self):
        self.client.force_login(self.other_student)
        response = self.upload(reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}), b'x' * 100)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(PracticeClip.objects.count(), 1)


# --------------------------------------------------------------------------
# Replies, follow-ups and the inbox
# --------------------------------------------------------------------------

class ClipThreadTests(ClipTestBase):
    def setUp(self):
        super().setUp()
        self.clip = self.make_ready_clip()
        mail.outbox.clear()

    def post(self, user, url, data):
        self.client.force_login(user)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, data, **AJAX)

    def test_teacher_text_reply(self):
        response = self.post(self.teacher, reverse('practice:add_clip_reply', kwargs={'pk': self.clip.pk}),
                             {'text': 'Try slower, with breath before bar 3.'})
        self.assertEqual(response.status_code, 200)
        self.clip.refresh_from_db()
        self.assertIsNotNone(self.clip.resolved_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.student.email])
        self.assertIn('replied to your clip', mail.outbox[0].subject)

    def test_empty_reply_rejected(self):
        response = self.post(self.teacher, reverse('practice:add_clip_reply', kwargs={'pk': self.clip.pk}),
                             {'text': '  '})
        self.assertEqual(response.status_code, 400)

    def test_student_follow_up_reopens_and_emails_teacher(self):
        self.post(self.teacher, reverse('practice:add_clip_reply', kwargs={'pk': self.clip.pk}), {'text': 'Try X'})
        mail.outbox.clear()
        response = self.post(self.student, reverse('practice:clip_follow_up', kwargs={'pk': self.clip.pk}),
                             {'text': 'Tried it, better?'})
        self.assertEqual(response.status_code, 200)
        self.clip.refresh_from_db()
        self.assertIsNone(self.clip.resolved_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.teacher.email])
        reply = self.clip.replies.filter(from_teacher=False).get()
        self.assertEqual(reply.author, self.student)

    def test_only_owner_can_follow_up(self):
        for user in (self.other_student, self.teacher):
            response = self.post(user, reverse('practice:clip_follow_up', kwargs={'pk': self.clip.pk}),
                                 {'text': 'hi'})
            self.assertEqual(response.status_code, 404)

    def test_other_teacher_cannot_reply(self):
        response = self.post(self.other_teacher, reverse('practice:add_clip_reply', kwargs={'pk': self.clip.pk}),
                             {'text': 'hi'})
        self.assertEqual(response.status_code, 404)

    def test_inbox_and_mark_done(self):
        self.client.force_login(self.teacher)
        inbox = self.client.get(reverse('practice:teacher_clip_inbox'))
        self.assertContains(inbox, self.clip.title)
        self.assertEqual(inbox.context['practice_clip_inbox_count'], 1)

        self.client.post(reverse('practice:mark_clip_done', kwargs={'pk': self.clip.pk}))
        inbox = self.client.get(reverse('practice:teacher_clip_inbox'))
        self.assertEqual(list(inbox.context['clips']), [])
        self.assertEqual(inbox.context['practice_clip_inbox_count'], 0)

    def test_practice_log_shows_new_reply_then_marks_read(self):
        self.post(self.teacher, reverse('practice:add_clip_reply', kwargs={'pk': self.clip.pk}), {'text': 'Nice'})
        self.client.force_login(self.student)
        page = self.client.get(reverse('practice:practice_log'))
        self.assertContains(page, 'New reply')
        self.assertIsNotNone(self.clip.replies.get().read_at)
        page = self.client.get(reverse('practice:practice_log'))
        self.assertNotContains(page, 'New reply')

    def test_entry_forms_include_clip_recorder(self):
        self.client.force_login(self.student)
        page = self.client.get(reverse('practice:log_practice'))
        self.assertContains(page, 'Clips for Your Teacher')
        self.assertContains(page, reverse('practice:upload_pending_clip'))
        self.assertContains(page, 'audio-recorder.js')

        page = self.client.get(reverse('practice:edit_practice', kwargs={'pk': self.entry.pk}))
        self.assertContains(page, reverse('practice:add_clip', kwargs={'entry_id': self.entry.pk}))
        self.assertContains(page, str(self.clip.pk))  # existing clip passed to the recorder

    def test_teacher_student_practice_page_shows_clip(self):
        self.client.force_login(self.teacher)
        page = self.client.get(reverse('practice:teacher_student_practice', kwargs={'student_id': self.student.pk}))
        self.assertContains(page, self.clip.title)
        self.assertContains(page, reverse('practice:teacher_clip_detail', kwargs={'pk': self.clip.pk}))


class ClipAudioThreadTests(ClipTestBase):
    """Thread tests that process real audio."""

    def setUp(self):
        if not HAS_FFMPEG:
            self.skipTest('ffmpeg not installed')
        super().setUp()
        self.clip = self.make_ready_clip()
        mail.outbox.clear()

    post = ClipThreadTests.post

    def test_follow_up_audio_limited_to_clip_length(self):
        self.post(self.student, reverse('practice:clip_follow_up', kwargs={'pk': self.clip.pk}),
                  {'audio': SimpleUploadedFile('long.webm', self.long_webm)})
        reply = self.clip.replies.get()
        self.assertEqual(reply.status, AudioStatus.FAILED)
        self.assertEqual(len(mail.outbox), 0)

    def test_teacher_audio_reply_processed_then_emailed(self):
        response = self.post(self.teacher, reverse('practice:add_clip_reply', kwargs={'pk': self.clip.pk}),
                             {'text': '', 'audio': SimpleUploadedFile('r.m4a', self.m4a)})
        self.assertEqual(response.status_code, 200)
        reply = self.clip.replies.get()
        self.assertEqual(reply.status, AudioStatus.READY)
        self.assertEqual(len(mail.outbox), 1)
        self.client.force_login(self.student)
        audio = self.client.get(reverse('practice:clip_reply_audio', kwargs={'pk': reply.pk}))
        self.assertEqual(audio.status_code, 200)
        audio.close()

    def test_clip_shared_email_after_processing(self):
        PracticeClip.objects.all().delete()
        mail.outbox.clear()
        self.add_clip()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('shared a practice clip', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [self.teacher.email])


# --------------------------------------------------------------------------
# Data rules and clean-up
# --------------------------------------------------------------------------

class ClipDataTests(ClipTestBase):
    def test_reply_needs_text_or_audio(self):
        clip = PracticeClip.objects.create(entry=self.entry, uploaded_by=self.student, title='x',
                                           status=AudioStatus.READY)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PracticeClipReply.objects.create(clip=clip, author=self.teacher, text='', status=AudioStatus.NONE)

    def test_retention_deletes_old_unkept_clips_with_files(self):
        def make(title, keep, age_days):
            clip = PracticeClip.objects.create(entry=self.entry, uploaded_by=self.student, title=title,
                                               status=AudioStatus.READY, keep=keep)
            clip.audio_file.save('a.m4a', SimpleUploadedFile('a.m4a', b'data'))
            PracticeClip.objects.filter(pk=clip.pk).update(
                last_activity_at=timezone.now() - timedelta(days=age_days))
            return clip

        old = make('old', False, 400)
        kept = make('kept', True, 400)
        recent = make('recent', False, 30)
        old_path = self.private_path(old.audio_file.name)
        self.assertTrue(os.path.exists(old_path))

        with self.captureOnCommitCallbacks(execute=True):
            call_command('purge_practice_clips', stdout=open(os.devnull, 'w'))

        remaining = set(PracticeClip.objects.values_list('title', flat=True))
        self.assertEqual(remaining, {'kept', 'recent'})
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(self.private_path(kept.audio_file.name)))
        self.assertTrue(os.path.exists(self.private_path(recent.audio_file.name)))

    def test_deleting_entry_deletes_clip_files(self):
        clip = PracticeClip.objects.create(entry=self.entry, uploaded_by=self.student, title='x',
                                           status=AudioStatus.READY)
        clip.audio_file.save('a.m4a', SimpleUploadedFile('a.m4a', b'data'))
        reply = PracticeClipReply.objects.create(clip=clip, author=self.teacher, text='hi',
                                                 status=AudioStatus.READY)
        reply.audio_file.save('r.m4a', SimpleUploadedFile('r.m4a', b'data'))
        paths = [self.private_path(clip.audio_file.name), self.private_path(reply.audio_file.name)]

        with self.captureOnCommitCallbacks(execute=True):
            self.entry.delete()
        for path in paths:
            self.assertFalse(os.path.exists(path))
