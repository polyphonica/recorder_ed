"""
Tests for audioplayer app.
"""

from django.test import TestCase
from unittest.mock import MagicMock, patch
import os

from .utils import is_aiff_file
from .fields import AutoConvertAudioFileField


class IsAiffFileTests(TestCase):
    """Test AIFF file detection utility."""

    def test_detects_aiff_extension(self):
        """Should return True for .aiff files."""
        mock_file = MagicMock()
        mock_file.name = 'test.aiff'
        self.assertTrue(is_aiff_file(mock_file))

    def test_detects_aif_extension(self):
        """Should return True for .aif files."""
        mock_file = MagicMock()
        mock_file.name = 'test.aif'
        self.assertTrue(is_aiff_file(mock_file))

    def test_case_insensitive(self):
        """Should handle uppercase extensions."""
        mock_file = MagicMock()
        mock_file.name = 'test.AIFF'
        self.assertTrue(is_aiff_file(mock_file))

    def test_returns_false_for_mp3(self):
        """Should return False for MP3 files."""
        mock_file = MagicMock()
        mock_file.name = 'test.mp3'
        self.assertFalse(is_aiff_file(mock_file))

    def test_returns_false_for_wav(self):
        """Should return False for WAV files."""
        mock_file = MagicMock()
        mock_file.name = 'test.wav'
        self.assertFalse(is_aiff_file(mock_file))

    def test_returns_false_for_none(self):
        """Should return False for None."""
        self.assertFalse(is_aiff_file(None))

    def test_returns_false_for_no_name(self):
        """Should return False when file has no name."""
        mock_file = MagicMock()
        mock_file.name = None
        self.assertFalse(is_aiff_file(mock_file))


class AutoConvertAudioFileFieldTests(TestCase):
    """Test custom audio file field with auto-conversion."""

    def test_allowed_extensions(self):
        """Should include mp3, wav, aiff, aif."""
        field = AutoConvertAudioFileField()
        self.assertIn('.mp3', field.ALLOWED_EXTENSIONS)
        self.assertIn('.wav', field.ALLOWED_EXTENSIONS)
        self.assertIn('.aiff', field.ALLOWED_EXTENSIONS)
        self.assertIn('.aif', field.ALLOWED_EXTENSIONS)

    def test_rejects_invalid_extension(self):
        """Should reject unsupported file types."""
        from django import forms

        field = AutoConvertAudioFileField(required=False)

        mock_file = MagicMock()
        mock_file.name = 'test.exe'
        mock_file.size = 1024

        with self.assertRaises(forms.ValidationError) as ctx:
            field.clean(mock_file)
        self.assertIn('Unsupported file type', str(ctx.exception))

    def test_rejects_oversized_file(self):
        """Should reject files over 45MB."""
        from django import forms

        field = AutoConvertAudioFileField(required=False)

        mock_file = MagicMock()
        mock_file.name = 'test.mp3'
        mock_file.size = 50 * 1024 * 1024  # 50MB

        with self.assertRaises(forms.ValidationError) as ctx:
            field.clean(mock_file)
        self.assertIn('exceeds', str(ctx.exception))

    def test_passes_mp3_unchanged(self):
        """Should pass MP3 files without conversion."""
        field = AutoConvertAudioFileField(required=False)

        mock_file = MagicMock()
        mock_file.name = 'test.mp3'
        mock_file.size = 1024 * 1024  # 1MB

        result = field.clean(mock_file)
        # Should return the same file (not converted)
        self.assertEqual(result.name, 'test.mp3')

    @patch('apps.audioplayer.fields.convert_aiff_to_mp3')
    def test_converts_aiff_to_mp3(self, mock_convert):
        """Should convert AIFF files to MP3."""
        field = AutoConvertAudioFileField(required=False)

        mock_input_file = MagicMock()
        mock_input_file.name = 'test.aiff'
        mock_input_file.size = 1024 * 1024  # 1MB

        mock_output_file = MagicMock()
        mock_output_file.name = 'test.mp3'
        mock_convert.return_value = mock_output_file

        result = field.clean(mock_input_file)

        mock_convert.assert_called_once_with(mock_input_file)
        self.assertEqual(result.name, 'test.mp3')


# ===== Protected playalong files =====

import shutil
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import override_settings

from . import storage as playalong_storage
from .models import Piece, Stem


class ProtectedPlayalongFileTests(TestCase):
    def setUp(self):
        self.private_root = tempfile.mkdtemp()
        self.public_root = tempfile.mkdtemp()
        self.override = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_root,
            MEDIA_ROOT=self.public_root,
            PRIVATE_MEDIA_X_ACCEL=False,
            ALLOWED_HOSTS=['testserver'],
        )
        self.override.enable()
        self.piece = Piece.objects.create(title='Sonata', is_public=False)
        self.stem = Stem(piece=self.piece, instrument_name='Piano', order=0)
        self.stem.audio_file.save('piano.mp3', ContentFile(b'ID3 fake mp3'), save=True)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.private_root, ignore_errors=True)
        shutil.rmtree(self.public_root, ignore_errors=True)

    def test_file_is_stored_privately_not_in_media(self):
        self.assertTrue((Path(self.private_root) / self.stem.audio_file.name).is_file())
        self.assertFalse(any(Path(self.public_root).rglob('*.mp3')))

    def test_url_is_signed_link_not_media_path(self):
        url = self.stem.audio_file.url
        self.assertTrue(url.startswith('/audioplayer/files/'))
        self.assertTrue(url.endswith('/' + os.path.basename(self.stem.audio_file.name)))
        self.assertNotIn('/media/', url)

    def test_signed_link_serves_file(self):
        response = self.client.get(self.stem.audio_file.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'ID3 fake mp3')
        self.assertEqual(response['Content-Type'], 'audio/mpeg')
        self.assertIn('private', response['Cache-Control'])

    def test_link_is_stable_within_window(self):
        self.assertEqual(self.stem.audio_file.url, self.stem.audio_file.url)

    def test_expired_link_is_rejected(self):
        url = self.stem.audio_file.url
        later = playalong_storage._current_window() + 2
        with patch.object(playalong_storage, '_current_window', return_value=later):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_link_still_valid_in_next_window(self):
        url = self.stem.audio_file.url
        later = playalong_storage._current_window() + 1
        with patch.object(playalong_storage, '_current_window', return_value=later):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_tampered_token_is_rejected(self):
        name = os.path.basename(self.stem.audio_file.name)
        self.assertEqual(self.client.get(f'/audioplayer/files/not-a-token/{name}').status_code, 404)

    def test_filename_must_match_token(self):
        url = self.stem.audio_file.url.rsplit('/', 1)[0] + '/other.mp3'
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_token_outside_playalong_folder_is_rejected(self):
        token = playalong_storage.signing.dumps(
            {'n': 'practice_clips/1/x.m4a', 'w': playalong_storage._current_window()},
            salt=playalong_storage.SIGNING_SALT, compress=True)
        self.assertEqual(self.client.get(f'/audioplayer/files/{token}/x.m4a').status_code, 404)

    @override_settings(PRIVATE_MEDIA_X_ACCEL=True)
    def test_x_accel_redirect_in_production(self):
        response = self.client.get(self.stem.audio_file.url)
        self.assertEqual(response['X-Accel-Redirect'], '/protected/' + self.stem.audio_file.name)

    def test_svg_gets_sandbox_policy(self):
        self.piece.svg_image.save('score.svg', ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg"/>'), save=True)
        response = self.client.get(self.piece.svg_image.url)
        self.assertIn('sandbox', response['Content-Security-Policy'])

    def test_move_command_moves_public_files(self):
        old = Path(self.public_root) / 'audioplayer/pdf_scores/old.pdf'
        old.parent.mkdir(parents=True)
        old.write_bytes(b'%PDF')
        call_command('move_playalong_files_private', '--dry-run', stdout=open(os.devnull, 'w'))
        self.assertTrue(old.exists())
        call_command('move_playalong_files_private', stdout=open(os.devnull, 'w'))
        self.assertFalse(old.exists())
        self.assertFalse((Path(self.public_root) / 'audioplayer/pdf_scores').exists())
        self.assertEqual((Path(self.private_root) / 'audioplayer/pdf_scores/old.pdf').read_bytes(), b'%PDF')
        # Running again is harmless
        call_command('move_playalong_files_private', stdout=open(os.devnull, 'w'))


class LibraryPlayerAccessTests(TestCase):
    def setUp(self):
        self.override = override_settings(ALLOWED_HOSTS=['testserver'])
        self.override.enable()
        self.public = Piece.objects.create(title='Public', is_public=True)
        self.private = Piece.objects.create(title='Private', is_public=False)

    def tearDown(self):
        self.override.disable()

    def test_public_piece_open_to_visitors(self):
        self.assertEqual(self.client.get(f'/audioplayer/library/piece/{self.public.id}/pieces-json/').status_code, 200)

    def test_private_piece_sends_visitor_to_login(self):
        response = self.client.get(f'/audioplayer/library/piece/{self.private.id}/pieces-json/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


class CourseLessonPlayerAccessTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.courses.models import Course, Topic, Lesson
        User = get_user_model()
        self.instructor = User.objects.create_user('instr', password='x')
        self.student = User.objects.create_user('stud', password='x')
        self.course = Course.objects.create(slug='c', title='C', cost=10, instructor=self.instructor,
                                            status=Course.Status.PUBLISHED)
        topic = Topic.objects.create(course=self.course, topic_number=1, topic_title='T')
        self.lesson = Lesson.objects.create(topic=topic, slug='l', lesson_number=1, lesson_title='L',
                                            status=Lesson.Status.PUBLISHED)

    def check(self, user):
        from django.contrib.auth.models import AnonymousUser
        from .views import _can_access_course_lesson
        return _can_access_course_lesson(user or AnonymousUser(), self.lesson)

    def test_visitor_and_unenrolled_student_blocked(self):
        self.assertFalse(self.check(None))
        self.assertFalse(self.check(self.student))

    def test_owner_allowed(self):
        self.assertTrue(self.check(self.instructor))

    def test_enrolled_student_allowed(self):
        from apps.courses.models import CourseEnrollment
        CourseEnrollment.objects.create(course=self.course, student=self.student, is_active=True)
        self.assertTrue(self.check(self.student))

    def test_preview_lesson_open_to_visitors(self):
        self.lesson.is_preview = True
        self.lesson.save()
        self.assertTrue(self.check(None))

    def test_player_json_sends_visitor_to_login(self):
        with override_settings(ALLOWED_HOSTS=['testserver']):
            response = self.client.get(f'/audioplayer/lesson/{self.lesson.id}/pieces-json/')
        self.assertEqual(response.status_code, 302)
