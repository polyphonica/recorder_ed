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


class LibraryShowToggleTests(TestCase):
    def setUp(self):
        from .models import Composer, PieceCollection, CollectionPiece
        self.mattheson = Composer.objects.create(name='Johann Mattheson')
        self.giesbert = Composer.objects.create(name='Franz J. Giesbert')
        self.sonata = Piece.objects.create(title='Sonata', composer=self.mattheson, is_public=True)
        duet = Piece.objects.create(title='Duet', composer=self.giesbert, is_public=True, show_in_library=False)
        self.duets = PieceCollection.objects.create(title='Giesbert Duets', is_public=True)
        CollectionPiece.objects.create(collection=self.duets, piece=duet, order=0)

    def context(self, query):
        from django.contrib.auth.models import AnonymousUser
        from django.test import RequestFactory
        from .views import PlayAlongLibraryView
        request = RequestFactory().get('/audioplayer/library/', query)
        request.user = AnonymousUser()
        view = PlayAlongLibraryView()
        view.setup(request)
        return view.get_context_data()

    def test_all_shows_both_with_counts(self):
        ctx = self.context({'mode': 'browse_all'})
        self.assertEqual(len(ctx['pieces']), 1)
        self.assertEqual(len(ctx['collections']), 1)
        counts = {o['value']: o['count'] for o in ctx['show_options']}
        self.assertEqual(counts, {'all': 2, 'pieces': 1, 'collections': 1})
        self.assertFalse(ctx['has_filters'])

    def test_pieces_only(self):
        ctx = self.context({'mode': 'browse_all', 'show': 'pieces'})
        self.assertEqual(len(ctx['pieces']), 1)
        self.assertEqual(len(ctx['collections']), 0)
        self.assertTrue(ctx['has_filters'])

    def test_collections_only(self):
        ctx = self.context({'mode': 'browse_all', 'show': 'collections'})
        self.assertEqual(len(ctx['pieces']), 0)
        self.assertEqual(len(ctx['collections']), 1)

    def test_invalid_value_means_all(self):
        ctx = self.context({'mode': 'browse_all', 'show': 'nonsense'})
        self.assertEqual(ctx['show'], 'all')

    def test_counts_follow_other_filters(self):
        ctx = self.context({'mode': 'browse_all', 'composer': str(self.giesbert.id)})
        counts = {o['value']: o['count'] for o in ctx['show_options']}
        self.assertEqual(counts, {'all': 1, 'pieces': 0, 'collections': 1})

    def test_toggle_links_keep_other_filters(self):
        ctx = self.context({'mode': 'browse_all', 'search': 'Giesbert', 'show': 'pieces'})
        urls = {o['value']: o['url'] for o in ctx['show_options']}
        self.assertIn('search=Giesbert', urls['collections'])
        self.assertIn('show=collections', urls['collections'])
        self.assertNotIn('show=', urls['all'])

    def test_page_renders_toggle(self):
        with override_settings(ALLOWED_HOSTS=['testserver']):
            response = self.client.get('/playalongs/library/', {'mode': 'browse_all', 'show': 'collections'})
        self.assertContains(response, 'Collections (1)')
        self.assertContains(response, 'name="show" value="collections"')


class CopyrightLockTests(TestCase):
    def setUp(self):
        from .models import Composer, PieceCollection, CollectionPiece
        self.PieceCollection, self.CollectionPiece = PieceCollection, CollectionPiece
        from django.contrib.auth import get_user_model
        self.teacher = get_user_model().objects.create_user('lock_teacher', password='x')
        self.giesbert = Composer.objects.create(name='Giesbert', in_copyright=True)
        self.handel = Composer.objects.create(name='Handel')
        self.duet = Piece.objects.create(title='Duet', composer=self.giesbert, is_public=False,
                                         created_by=self.teacher)
        self.sonata = Piece.objects.create(title='Sonata', composer=self.handel, is_public=True,
                                           created_by=self.teacher)

    def test_piece_by_in_copyright_composer_cannot_be_saved_public(self):
        self.duet.is_public = True
        self.duet.save()
        self.duet.refresh_from_db()
        self.assertFalse(self.duet.is_public)

    def test_piece_clean_explains_why(self):
        from django.core.exceptions import ValidationError
        self.duet.is_public = True
        with self.assertRaises(ValidationError) as ctx:
            self.duet.full_clean()
        self.assertIn('is_public', ctx.exception.message_dict)

    def test_piece_marked_in_copyright_even_if_composer_is_not(self):
        self.sonata.in_copyright = True  # e.g. a modern arrangement
        self.sonata.save()
        self.sonata.refresh_from_db()
        self.assertFalse(self.sonata.is_public)

    def test_public_domain_piece_can_be_public(self):
        self.sonata.save()
        self.sonata.refresh_from_db()
        self.assertTrue(self.sonata.is_public)

    def test_marking_composer_makes_pieces_and_collections_private(self):
        col = self.PieceCollection.objects.create(title='Handel works', is_public=True)
        self.CollectionPiece.objects.create(collection=col, piece=self.sonata, order=0)
        self.handel.in_copyright = True
        self.handel.save()
        self.sonata.refresh_from_db(); col.refresh_from_db()
        self.assertFalse(self.sonata.is_public)
        self.assertFalse(col.is_public)

    def test_adding_locked_piece_makes_public_collection_private(self):
        col = self.PieceCollection.objects.create(title='Mixed', is_public=True)
        self.CollectionPiece.objects.create(collection=col, piece=self.duet, order=0)
        col.refresh_from_db()
        self.assertFalse(col.is_public)

    def test_collection_with_locked_piece_cannot_be_saved_public(self):
        col = self.PieceCollection.objects.create(title='Duets', is_public=False)
        self.CollectionPiece.objects.create(collection=col, piece=self.duet, order=0)
        col.is_public = True
        col.save()
        col.refresh_from_db()
        self.assertFalse(col.is_public)

    def test_collection_by_in_copyright_composer_cannot_be_public(self):
        col = self.PieceCollection.objects.create(title='G', composer=self.giesbert, is_public=True)
        col.refresh_from_db()
        self.assertFalse(col.is_public)

    def collection_form(self, col, pieces, is_public):
        from .forms import PieceCollectionForm
        from django.http import QueryDict
        data = QueryDict(mutable=True)
        data.update({'title': col.title, 'grade_level': 'N/A'})
        if is_public:
            data['is_public'] = 'on'
        data.setlist('pieces', [str(p.id) for p in pieces])
        return PieceCollectionForm(data, instance=col, user=self.teacher)

    def test_collection_form_rejects_public_with_locked_piece_selected(self):
        col = self.PieceCollection.objects.create(title='C', is_public=False)
        form = self.collection_form(col, [self.duet], is_public=True)
        self.assertFalse(form.is_valid())
        self.assertEqual(list(form.errors), ['is_public'])

    def test_collection_form_allows_public_after_removing_locked_piece(self):
        col = self.PieceCollection.objects.create(title='C', is_public=False)
        self.CollectionPiece.objects.create(collection=col, piece=self.duet, order=0)
        form = self.collection_form(col, [self.sonata], is_public=True)
        self.assertTrue(form.is_valid(), form.errors)

    def test_piece_form_rejects_public_for_in_copyright_composer(self):
        from .forms import PieceForm
        form = PieceForm({'title': 'New duet', 'composer': self.giesbert.id, 'grade_level': 'N/A',
                          'is_public': 'on'})
        self.assertFalse(form.is_valid())
        self.assertEqual(list(form.errors), ['is_public'])


class CollectionPieceEditLinkTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from .models import PieceCollection, CollectionPiece
        self.teacher = get_user_model().objects.create_user('link_teacher', password='x')
        self.piece = Piece.objects.create(title='Exercise 1', created_by=self.teacher)
        self.collection = PieceCollection.objects.create(title='Duets', created_by=self.teacher)
        CollectionPiece.objects.create(collection=self.collection, piece=self.piece, order=0)
        self.request = RequestFactory().get('/')
        self.request.user = self.teacher
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)

    def test_library_collection_card_links_to_pieces_page(self):
        from django.template.loader import render_to_string
        from django.urls import reverse
        html = render_to_string('audioplayer/piece_list.html', {
            'pieces': [], 'collections': [self.collection], 'view_filter': 'all', 'title': 'x',
        }, request=self.request)
        self.assertIn(reverse('audioplayer:collection_detail', kwargs={'pk': self.collection.pk}), html)

    def test_collection_form_builds_piece_edit_links(self):
        from django.template.loader import render_to_string
        from .forms import PieceCollectionForm
        html = render_to_string('audioplayer/collection_form.html', {
            'form': PieceCollectionForm(instance=self.collection, user=self.teacher),
            'collection': self.collection, 'collection_pieces': [], 'title': 'x', 'submit_text': 'Save',
        }, request=self.request)
        self.assertIn("'/audioplayer/pieces/0/edit/'.replace('/0/'", html)
        self.assertIn('href="${pieceEditUrl(piece.id)}"', html)


# ===== Free Play-Along Library =====

import datetime
import io

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone


def _user(username, teacher=False):
    user = get_user_model().objects.create_user(username, email=f'{username}@example.com', password='x')
    user.profile.is_teacher = teacher
    # Complete profiles, so the profile-completion middleware lets them through
    user.profile.profile_completed = True
    user.profile.email_verified = True
    user.profile.save()
    return user


def _teacher(username='lib_teacher'):
    return _user(username, teacher=True)


EMAIL_SETTINGS = dict(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)


@override_settings(ALLOWED_HOSTS=['testserver'], **EMAIL_SETTINGS)
class PlayalongPermissionTests(TestCase):
    """Permission recorded for in-copyright music lifts the lock for the audio only."""

    def setUp(self):
        from .models import Composer, PieceCollection, CollectionPiece
        self.PieceCollection, self.CollectionPiece = PieceCollection, CollectionPiece
        self.giesbert = Composer.objects.create(name='Giesbert', in_copyright=True)
        self.duet = Piece.objects.create(title='Duet', composer=self.giesbert, is_public=False)

    def test_piece_with_permission_can_be_public(self):
        self.duet.audio_permission = True
        self.duet.music_source_title = 'Giesbert Method'
        self.duet.is_public = True
        self.duet.full_clean()
        self.duet.save()
        self.duet.refresh_from_db()
        self.assertTrue(self.duet.is_public)
        self.assertEqual(self.duet.copyright_status, 'permitted')

    def test_expired_permission_does_not_count(self):
        self.duet.audio_permission = True
        self.duet.permission_expires = timezone.localdate() - datetime.timedelta(days=1)
        self.duet.is_public = True
        self.duet.save()
        self.duet.refresh_from_db()
        self.assertFalse(self.duet.is_public)

    def test_collection_permission_covers_its_pieces(self):
        col = self.PieceCollection.objects.create(title='Duets', is_public=False, audio_permission=True,
                                                  music_source_title='Giesbert Method')
        self.CollectionPiece.objects.create(collection=col, piece=self.duet, order=0)
        col.is_public = True
        col.save()
        col.refresh_from_db()
        self.assertTrue(col.is_public)
        self.assertTrue(self.duet.is_cleared)
        self.assertEqual(self.duet.music_source(), col)
        self.assertEqual(self.duet.permission_source(), col)

    def test_public_in_copyright_needs_music_source(self):
        from django.core.exceptions import ValidationError
        self.duet.audio_permission = True
        self.duet.is_public = True
        with self.assertRaises(ValidationError) as ctx:
            self.duet.full_clean()
        self.assertIn('music_source_title', ctx.exception.message_dict)

    def test_no_sheet_music_on_in_copyright_piece(self):
        from django.core.exceptions import ValidationError
        root = tempfile.mkdtemp()
        with override_settings(PRIVATE_MEDIA_ROOT=root):
            self.duet.pdf_score.save('x.pdf', ContentFile(b'%PDF-1.4 test'), save=False)
            with self.assertRaises(ValidationError) as ctx:
                self.duet.full_clean()
        shutil.rmtree(root, ignore_errors=True)
        self.assertIn('pdf_score', ctx.exception.message_dict)

    def test_score_hidden_from_players_for_in_copyright(self):
        from django.contrib.auth.models import AnonymousUser
        from .views import _score_url
        self.duet.svg_image.name = 'audioplayer/svg_images/x.png'
        self.assertIsNone(_score_url(self.duet, 'svg_image', AnonymousUser()))
        self.assertIsNotNone(_score_url(self.duet, 'svg_image', _teacher()))

    def test_pdf_needs_an_account(self):
        from django.contrib.auth.models import AnonymousUser
        from .views import _score_url
        piece = Piece.objects.create(title='Sonata', is_public=True)
        piece.pdf_score.name = 'audioplayer/pdf_scores/s.pdf'
        self.assertIsNone(_score_url(piece, 'pdf_score', AnonymousUser()))
        student = get_user_model().objects.create_user('pdf_student', password='x')
        self.assertIsNotNone(_score_url(piece, 'pdf_score', student))

    def test_expiry_command_makes_private_and_reminds(self):
        from .models import Composer
        today = timezone.localdate()
        teacher = _teacher()
        self.duet.created_by = teacher
        self.duet.audio_permission = True
        self.duet.music_source_title = 'Method'
        self.duet.is_public = True
        self.duet.save()
        Piece.objects.filter(pk=self.duet.pk).update(permission_expires=today - datetime.timedelta(days=1))
        soon = Piece.objects.create(title='Soon', composer=self.giesbert, created_by=teacher, audio_permission=True,
                                    music_source_title='Method', is_public=True,
                                    permission_expires=today + datetime.timedelta(days=30))
        call_command('expire_playalong_permissions', stdout=io.StringIO())
        self.duet.refresh_from_db(); soon.refresh_from_db()
        self.assertFalse(self.duet.is_public)
        self.assertTrue(soon.is_public)
        subjects = [m.subject for m in mail.outbox]
        self.assertTrue(any('made private' in s for s in subjects), subjects)
        self.assertTrue(any('expires' in s for s in subjects), subjects)


@override_settings(ALLOWED_HOSTS=['testserver'])
class PlayalongPublicPagesTests(TestCase):
    def setUp(self):
        from .models import Composer, PieceCollection, CollectionPiece
        self.mattheson = Composer.objects.create(name='Johann Mattheson', period='Baroque', bio='<p>Bio</p>')
        self.sonata = Piece.objects.create(title='Sonata', composer=self.mattheson, is_public=True)
        self.private = Piece.objects.create(title='Draft', composer=self.mattheson, is_public=False)
        self.col = PieceCollection.objects.create(title='Sonatas', is_public=True)
        CollectionPiece.objects.create(collection=self.col, piece=self.sonata, order=0)

    def test_pages_open_to_visitors(self):
        for url in ['/playalongs/', '/playalongs/library/', '/playalongs/editions/',
                    self.sonata.get_absolute_url(), self.col.get_absolute_url(), self.mattheson.get_absolute_url()]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_slugs_are_readable(self):
        self.assertEqual(self.sonata.get_absolute_url(), '/playalongs/piece/johann-mattheson-sonata/')
        self.assertEqual(self.col.get_absolute_url(), '/playalongs/collection/sonatas/')

    def test_private_piece_page_needs_login(self):
        response = self.client.get(self.private.get_absolute_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_visitors_get_preview(self):
        html = self.client.get(self.sonata.get_absolute_url()).content.decode()
        self.assertIn('id="is-preview" value="true"', html)
        self.assertIn('id="preview-signup"', html)

    def test_logged_in_players_get_full_player(self):
        self.client.force_login(_user('player'))
        context = self.client.get(self.sonata.get_absolute_url()).context
        self.assertFalse(context['is_preview'])

    def test_visitor_library_shows_collections(self):
        response = self.client.get('/playalongs/library/')
        self.assertEqual(len(response.context['collections']), 1)
        self.assertFalse(response.context['is_student_view'])

    def test_period_filter(self):
        response = self.client.get('/playalongs/library/', {'period': 'baroque'})
        self.assertEqual(len(response.context['pieces']), 1)
        response = self.client.get('/playalongs/library/', {'period': 'Romantic'})
        self.assertEqual(len(response.context['pieces']), 0)

    def test_teacher_can_view_as_visitor(self):
        self.client.force_login(_teacher())
        response = self.client.get('/playalongs/library/', {'as_visitor': '1'})
        self.assertFalse(response.context['is_teacher'])
        self.assertTrue(response.context['as_visitor'])
        response = self.client.get(self.sonata.get_absolute_url(), {'as_visitor': '1'})
        self.assertTrue(response.context['is_preview'])

    def test_old_addresses_redirect(self):
        response = self.client.get('/audioplayer/library/?search=x')
        self.assertEqual(response['Location'], '/playalongs/library/?search=x')
        response = self.client.get(f'/audioplayer/library/piece/{self.sonata.id}/player/')
        self.assertEqual(response['Location'], self.sonata.get_absolute_url())

    def test_sitemap_lists_public_items_only(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn(self.sonata.get_absolute_url(), xml)
        self.assertIn(self.col.get_absolute_url(), xml)
        self.assertIn(self.mattheson.get_absolute_url(), xml)
        self.assertNotIn(self.private.slug, xml)

    def test_home_page_links_to_library(self):
        self.assertContains(self.client.get('/'), reverse('playalongs:home'))


@override_settings(ALLOWED_HOSTS=['testserver'])
class PlayalongManagementTests(TestCase):
    def setUp(self):
        from .models import Composer, PieceCollection, CollectionPiece
        self.teacher = _teacher()
        self.col = PieceCollection.objects.create(title='Exercises', is_public=False, created_by=self.teacher)
        self.pieces = [Piece.objects.create(title=f'Ex {i}', is_public=False, created_by=self.teacher) for i in range(2)]
        for i, p in enumerate(self.pieces):
            CollectionPiece.objects.create(collection=self.col, piece=p, order=i)
        self.client.force_login(self.teacher)

    def test_publish_collection_makes_it_and_its_pieces_public(self):
        self.client.post(reverse('audioplayer:collection_publish', kwargs={'pk': self.col.pk}))
        self.col.refresh_from_db()
        self.assertTrue(self.col.is_public)
        self.assertTrue(all(Piece.objects.get(pk=p.pk).is_public for p in self.pieces))

    def test_publish_refuses_locked_collection(self):
        from .models import Composer
        g = Composer.objects.create(name='G', in_copyright=True)
        Piece.objects.filter(pk=self.pieces[0].pk).update(composer=g)
        self.client.post(reverse('audioplayer:collection_publish', kwargs={'pk': self.col.pk}))
        self.col.refresh_from_db()
        self.assertFalse(self.col.is_public)

    def test_needs_attention_lists_public_items_without_edition(self):
        from .views import _attention_issues
        Piece.objects.filter(pk=self.pieces[0].pk).update(is_public=True)
        piece = Piece.objects.get(pk=self.pieces[0].pk)
        self.assertIn('Public, but no edition PDF yet', _attention_issues(piece, False))
        self.col.is_public = True
        self.col.save()
        self.assertTrue(any('private piece' in i for i in _attention_issues(self.col, True)))


@override_settings(ALLOWED_HOSTS=['testserver'])
class PlayalongProductMoveTests(TestCase):
    def test_play_along_products_move_into_library(self):
        from apps.digital_products.models import DigitalProduct, DigitalProductCollection
        from .models import PieceCollection
        teacher = _teacher()
        col = PieceCollection.objects.create(title='Williams Sonata', is_public=False)
        product = DigitalProduct.objects.create(
            slug='williams', title='Williams Sonata', description='x', short_description='x', teacher=teacher,
            product_type='play_along', price=0, status='published')
        DigitalProductCollection.objects.create(product=product, collection=col)
        call_command('move_playalong_products_to_library', stdout=io.StringIO())
        col.refresh_from_db(); product.refresh_from_db()
        self.assertTrue(col.is_public)
        self.assertEqual(product.status, 'archived')
        response = self.client.get('/products/product/williams/')
        self.assertEqual(response['Location'], col.get_absolute_url())

    def test_new_products_cannot_be_play_alongs(self):
        from apps.digital_products.forms import ProductForm
        choices = [c[0] for c in ProductForm().fields['product_type'].choices]
        self.assertNotIn('play_along', choices)


@override_settings(ALLOWED_HOSTS=['testserver'], **EMAIL_SETTINGS)
class PlayalongSignupTests(TestCase):
    def test_login_returns_to_the_page_asked_for(self):
        user = get_user_model().objects.create_user('back', email='back@example.com', password='pw-12345!')
        response = self.client.post('/accounts/login/?next=/playalongs/piece/x/',
                                    {'username': 'back@example.com', 'password': 'pw-12345!',
                                     'next': '/playalongs/piece/x/'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/playalongs/piece/x/')

    def test_login_ignores_unsafe_next(self):
        get_user_model().objects.create_user('safe', email='safe@example.com', password='pw-12345!')
        response = self.client.post('/accounts/login/', {'username': 'safe@example.com', 'password': 'pw-12345!',
                                                         'next': 'https://evil.example.com/'})
        self.assertNotIn('evil', response.get('Location', ''))

    def test_welcome_email_sent_once_on_verification(self):
        from apps.accounts.email_verification import email_verification_token
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        user = get_user_model().objects.create_user('lib', email='lib@example.com', password='x')
        user.profile.signup_source = 'playalongs'
        user.profile.save()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        mail.outbox = []
        self.client.get(reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token}))
        self.assertTrue(any('Play-Along Library' in m.subject for m in mail.outbox), [m.subject for m in mail.outbox])
        # A second click on the link doesn't send it again
        mail.outbox = []
        self.client.get(reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token}))
        self.assertFalse(any('Play-Along Library' in m.subject for m in mail.outbox))
