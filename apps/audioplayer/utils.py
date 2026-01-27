"""
Audio conversion utilities for audioplayer app.

Provides AIFF to MP3 auto-conversion for stem uploads.
"""

import os
import tempfile
import uuid
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO


def is_aiff_file(uploaded_file):
    """
    Check if an uploaded file is an AIFF file based on extension.

    Args:
        uploaded_file: Django UploadedFile object

    Returns:
        bool: True if file has .aiff or .aif extension
    """
    if not uploaded_file or not uploaded_file.name:
        return False

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    return ext in ['.aiff', '.aif']


def convert_aiff_to_mp3(uploaded_file):
    """
    Convert an AIFF uploaded file to MP3 format.

    Uses the AudioProcessor from creator_studio for consistent conversion.
    Returns an InMemoryUploadedFile that can replace the original in form processing.

    Args:
        uploaded_file: Django UploadedFile object containing AIFF data

    Returns:
        InMemoryUploadedFile: MP3 version of the audio file

    Raises:
        ValueError: If conversion fails
    """
    from apps.creator_studio.services.audio_processor import AudioProcessor

    processor = AudioProcessor()

    try:
        # Process the file - convert to MP3 with default settings
        output_path, original_name = processor.process(
            uploaded_file,
            output_format='mp3',
            speed=1.0,
            normalize=False
        )

        # Read the converted file into memory
        with open(output_path, 'rb') as f:
            mp3_content = f.read()

        # Create new filename with .mp3 extension
        base_name = os.path.splitext(original_name)[0]
        new_filename = f"{base_name}.mp3"

        # Create an InMemoryUploadedFile
        mp3_buffer = BytesIO(mp3_content)
        mp3_file = InMemoryUploadedFile(
            file=mp3_buffer,
            field_name='audio_file',
            name=new_filename,
            content_type='audio/mpeg',
            size=len(mp3_content),
            charset=None
        )

        return mp3_file

    finally:
        # Clean up the temp output file
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
