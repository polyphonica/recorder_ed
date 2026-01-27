"""
Audio processing service using FFmpeg via pydub.
"""

import os
import tempfile
import uuid
import subprocess
from django.conf import settings


class AudioProcessor:
    """
    Wraps FFmpeg functionality for audio conversion and manipulation.
    """

    SUPPORTED_FORMATS = ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'aiff']
    MAX_DURATION_SECONDS = 600  # 10 minutes max

    def __init__(self):
        self.temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_audio')
        os.makedirs(self.temp_dir, exist_ok=True)

    def process(self, uploaded_file, output_format='mp3', speed=1.0,
                trim_start=None, trim_end=None, normalize=False):
        """
        Process an uploaded audio file.

        Args:
            uploaded_file: Django UploadedFile object
            output_format: Target format (mp3, wav, ogg, m4a, aac)
            speed: Playback speed multiplier (0.5 to 2.0)
            trim_start: Start time in seconds (optional)
            trim_end: End time in seconds (optional)
            normalize: Whether to normalize volume levels

        Returns:
            tuple: (output_file_path, original_filename)
        """
        from pydub import AudioSegment

        # Validate format
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f'Unsupported format: {output_format}')

        # Validate speed
        if not 0.5 <= speed <= 2.0:
            raise ValueError('Speed must be between 0.5 and 2.0')

        # Save uploaded file to temp location
        temp_input = os.path.join(self.temp_dir, f'{uuid.uuid4()}_input')
        with open(temp_input, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        try:
            # Load audio
            audio = AudioSegment.from_file(temp_input)

            # Validate duration
            duration_seconds = len(audio) / 1000
            if duration_seconds > self.MAX_DURATION_SECONDS:
                raise ValueError(
                    f'Audio exceeds maximum duration of {self.MAX_DURATION_SECONDS} seconds '
                    f'({self.MAX_DURATION_SECONDS // 60} minutes)'
                )

            # Apply trimming
            if trim_start is not None or trim_end is not None:
                start_ms = int((trim_start or 0) * 1000)
                end_ms = int((trim_end or duration_seconds) * 1000)
                audio = audio[start_ms:end_ms]

            # Apply speed change
            if speed != 1.0:
                audio = self._change_speed(audio, speed)

            # Apply normalization
            if normalize:
                audio = self._normalize(audio)

            # Export to output format
            output_filename = f'{uuid.uuid4()}.{output_format}'
            output_path = os.path.join(self.temp_dir, output_filename)

            # Handle format-specific export parameters
            export_kwargs = self._get_export_kwargs(output_format)
            audio.export(output_path, format=output_format, **export_kwargs)

            return output_path, uploaded_file.name

        finally:
            # Clean up input temp file
            if os.path.exists(temp_input):
                os.remove(temp_input)

    def _change_speed(self, audio, speed):
        """
        Change playback speed while preserving pitch.
        Uses atempo filter through raw ffmpeg.
        """
        from pydub import AudioSegment

        # Export to temp file
        temp_in = os.path.join(self.temp_dir, f'{uuid.uuid4()}_speed_in.wav')
        temp_out = os.path.join(self.temp_dir, f'{uuid.uuid4()}_speed_out.wav')

        audio.export(temp_in, format='wav')

        try:
            # atempo filter accepts 0.5 to 2.0
            cmd = [
                'ffmpeg', '-y', '-i', temp_in,
                '-filter:a', f'atempo={speed}',
                '-loglevel', 'error',
                temp_out
            ]
            result = subprocess.run(cmd, check=True, capture_output=True)
            return AudioSegment.from_wav(temp_out)
        except subprocess.CalledProcessError as e:
            raise ValueError(f'FFmpeg speed change failed: {e.stderr.decode()}')
        finally:
            for f in [temp_in, temp_out]:
                if os.path.exists(f):
                    os.remove(f)

    def _normalize(self, audio):
        """
        Normalize audio to target dBFS level.
        """
        target_dBFS = -20.0
        change_in_dBFS = target_dBFS - audio.dBFS
        return audio.apply_gain(change_in_dBFS)

    def _get_export_kwargs(self, format):
        """
        Get format-specific export parameters.
        """
        kwargs = {}
        if format == 'mp3':
            kwargs['bitrate'] = '192k'
        elif format == 'm4a':
            kwargs['codec'] = 'aac'
        elif format == 'aac':
            kwargs['codec'] = 'aac'
        return kwargs

    @classmethod
    def cleanup_old_files(cls, max_age_hours=24):
        """
        Clean up temporary files older than max_age_hours.
        Should be called periodically via management command or cron.
        """
        import time

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_audio')
        if not os.path.exists(temp_dir):
            return 0

        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0

        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            try:
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
            except OSError:
                pass  # File may have been deleted by another process

        return deleted_count
