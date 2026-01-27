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
        """Should reject files over 10MB."""
        from django import forms

        field = AutoConvertAudioFileField(required=False)

        mock_file = MagicMock()
        mock_file.name = 'test.mp3'
        mock_file.size = 15 * 1024 * 1024  # 15MB

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
