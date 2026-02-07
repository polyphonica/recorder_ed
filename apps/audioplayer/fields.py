"""
Custom form fields for audioplayer app.
"""

import os
from django import forms
from .utils import is_aiff_file, convert_aiff_to_mp3


class AutoConvertAudioFileField(forms.FileField):
    """
    A FileField that automatically converts AIFF files to MP3 during validation.

    Accepts: .mp3, .wav, .aiff, .aif
    If an AIFF file is uploaded, it's automatically converted to MP3.
    """

    ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.aiff', '.aif']
    MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB per stem

    def clean(self, data, initial=None):
        """
        Validate and optionally convert the uploaded file.

        If the file is AIFF, convert it to MP3 before returning.
        """
        # Let parent class do basic validation
        file = super().clean(data, initial)

        if not file:
            return file

        # Validate file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                f'Unsupported file type "{ext}". '
                f'Allowed formats: {", ".join(self.ALLOWED_EXTENSIONS)}'
            )

        # Validate file size
        if file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError(
                f'File size ({file.size // (1024*1024)}MB) exceeds '
                f'maximum allowed ({self.MAX_FILE_SIZE // (1024*1024)}MB).'
            )

        # If AIFF, convert to MP3
        if is_aiff_file(file):
            try:
                file = convert_aiff_to_mp3(file)
            except Exception as e:
                raise forms.ValidationError(
                    f'Failed to convert AIFF to MP3: {str(e)}'
                )

        return file
