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
            response = self.client.get('/audioplayer/library/', {'mode': 'browse_all', 'show': 'collections'})
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
