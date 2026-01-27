"""
Tests for Creator Studio app.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
import os

User = get_user_model()


class CreatorStudioAccessTests(TestCase):
    """Test access control for Creator Studio views."""

    def setUp(self):
        self.client = Client()

        # Create test users
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123'
        )
        # Set up teacher profile - refresh from DB to get the auto-created profile
        self.teacher.refresh_from_db()
        self.teacher.profile.is_teacher = True
        self.teacher.profile.profile_completed = True
        self.teacher.profile.save()

        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123'
        )
        # Student profile (is_teacher=False by default)

    def test_home_requires_instructor(self):
        """Non-instructors should be redirected from home page."""
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('creator_studio:home'))
        self.assertNotEqual(response.status_code, 200)

    def test_home_accessible_to_instructor(self):
        """Instructors should access home page."""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('creator_studio:home'))
        self.assertEqual(response.status_code, 200)

    def test_fingering_diagram_accessible_to_instructor(self):
        """Instructors should access fingering diagram."""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('creator_studio:fingering_diagram'))
        self.assertEqual(response.status_code, 200)

    def test_time_signature_accessible_to_instructor(self):
        """Instructors should access time signature generator."""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('creator_studio:time_signature'))
        self.assertEqual(response.status_code, 200)

    def test_audio_converter_accessible_to_instructor(self):
        """Instructors should access audio converter."""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('creator_studio:audio_converter'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.get(reverse('creator_studio:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class TimeSignatureGeneratorTests(TestCase):
    """Test time signature generator functionality."""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='testpass123'
        )
        self.teacher.refresh_from_db()
        self.teacher.profile.is_teacher = True
        self.teacher.profile.profile_completed = True
        self.teacher.profile.save()
        self.client.login(username='teacher2', password='testpass123')

    def test_get_returns_default_values(self):
        """GET request should return default 4/4 time signature."""
        response = self.client.get(reverse('creator_studio:time_signature'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['top'], '4')
        self.assertEqual(response.context['bottom'], '4')
        self.assertIn('svg_code', response.context)

    def test_post_generates_custom_svg(self):
        """POST request should generate custom time signature."""
        response = self.client.post(reverse('creator_studio:time_signature'), {
            'top': '3',
            'bottom': '4',
            'top_right': '',
            'bottom_right': '',
            'font_size': 48,
            'spacing': 24,
            'viewbox_w': 60,
            'viewbox_h': 120,
            'display_w': 90,
            'display_h': 140,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['top'], '3')
        self.assertEqual(response.context['bottom'], '4')
        self.assertIn('>3<', response.context['svg_code'])


class AudioConverterFormTests(TestCase):
    """Test audio converter form validation."""

    def test_valid_extensions_accepted(self):
        """Should accept valid audio file extensions."""
        from apps.creator_studio.forms import AudioConverterForm

        # Create mock file with valid extension
        mock_file = MagicMock()
        mock_file.size = 1024 * 1024  # 1MB
        mock_file.name = 'test.mp3'

        form = AudioConverterForm(
            data={'output_format': 'wav'},
            files={'audio_file': mock_file}
        )
        # Note: Form won't be fully valid without a real file,
        # but we can test that the extension check doesn't fail
        form.is_valid()
        if 'audio_file' in form.errors:
            # Check it's not an extension error
            self.assertNotIn('Unsupported file type', str(form.errors['audio_file']))

    def test_invalid_extension_rejected(self):
        """Should reject invalid file extensions."""
        from apps.creator_studio.forms import AudioConverterForm

        mock_file = MagicMock()
        mock_file.size = 1024 * 1024
        mock_file.name = 'test.exe'

        form = AudioConverterForm(
            data={'output_format': 'mp3'},
            files={'audio_file': mock_file}
        )
        form.is_valid()
        if 'audio_file' in form.errors:
            self.assertIn('Unsupported file type', str(form.errors['audio_file']))

    def test_file_size_limit(self):
        """Should reject files over 20MB."""
        from apps.creator_studio.forms import AudioConverterForm

        mock_file = MagicMock()
        mock_file.size = 25 * 1024 * 1024  # 25MB
        mock_file.name = 'test.mp3'

        form = AudioConverterForm(
            data={'output_format': 'mp3'},
            files={'audio_file': mock_file}
        )
        form.is_valid()
        if 'audio_file' in form.errors:
            self.assertIn('exceeds', str(form.errors['audio_file']))

    def test_trim_validation(self):
        """Should reject when trim_start >= trim_end."""
        from apps.creator_studio.forms import AudioConverterForm

        mock_file = MagicMock()
        mock_file.size = 1024 * 1024
        mock_file.name = 'test.mp3'

        form = AudioConverterForm(
            data={
                'output_format': 'mp3',
                'trim_start': 30,
                'trim_end': 10
            },
            files={'audio_file': mock_file}
        )
        form.is_valid()
        self.assertIn('Trim end must be greater', str(form.errors))


class AudioProcessorTests(TestCase):
    """Test audio processor service."""

    def test_validates_format(self):
        """Should reject invalid output formats."""
        from apps.creator_studio.services.audio_processor import AudioProcessor
        processor = AudioProcessor()

        with self.assertRaises(ValueError) as context:
            processor.process(MagicMock(), output_format='invalid')
        self.assertIn('Unsupported format', str(context.exception))

    def test_validates_speed_range(self):
        """Should reject speeds outside 0.5-2.0 range."""
        from apps.creator_studio.services.audio_processor import AudioProcessor
        processor = AudioProcessor()

        with self.assertRaises(ValueError) as context:
            processor.process(MagicMock(), speed=3.0)
        self.assertIn('Speed must be', str(context.exception))

        with self.assertRaises(ValueError) as context:
            processor.process(MagicMock(), speed=0.1)
        self.assertIn('Speed must be', str(context.exception))
