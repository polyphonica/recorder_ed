"""
ffprobe/ffmpeg helpers for practice clips.

Called with argument lists (never a shell) and timeouts. The file type is
decided by what ffprobe finds inside the file, not by its name or the
browser-supplied content type.
"""

import json
import subprocess

# ffprobe format names we accept (webm/mkv, ogg, mp4/m4a/3gp, mp3, wav, aiff)
ALLOWED_FORMATS = {'matroska', 'webm', 'ogg', 'mov', 'mp4', 'm4a', '3gp', '3g2', 'mp3', 'wav', 'aiff'}

PROBE_TIMEOUT = 30
CONVERT_TIMEOUT = 300


class AudioError(Exception):
    """A recording we can't accept. The message is safe to show the user."""


def probe(path):
    """Return the duration in seconds of an audio file, or raise AudioError."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-print_format', 'json',
             '-show_format', '-show_streams', path],
            capture_output=True, timeout=PROBE_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired:
        raise AudioError("The recording couldn't be read.")
    if result.returncode != 0:
        raise AudioError("This doesn't look like an audio file.")

    try:
        info = json.loads(result.stdout or b'{}')
    except ValueError:
        raise AudioError("This doesn't look like an audio file.")

    fmt = info.get('format', {})
    format_names = set((fmt.get('format_name') or '').split(','))
    if not format_names & ALLOWED_FORMATS:
        raise AudioError("This audio format isn't supported.")

    streams = info.get('streams', [])
    if not any(s.get('codec_type') == 'audio' for s in streams):
        raise AudioError("The file has no audio in it.")
    if any(s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')
           for s in streams):
        raise AudioError("Please upload audio only, not video.")

    duration = fmt.get('duration')
    if duration is None:
        # Browser WebM recordings often have no duration in the header;
        # fall back to the audio stream's, then to decoding the file.
        for s in streams:
            if s.get('codec_type') == 'audio' and s.get('duration'):
                duration = s['duration']
                break
    if duration is None:
        duration = _decoded_duration(path)
    try:
        return float(duration)
    except (TypeError, ValueError):
        raise AudioError("The recording's length couldn't be read.")


def _decoded_duration(path):
    """Decode the whole file to find its length (for headerless WebM)."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', path, '-f', 'null', '-progress', 'pipe:1', '-'],
            capture_output=True, timeout=PROBE_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    out_time = None
    for line in (result.stdout or b'').decode(errors='ignore').splitlines():
        if line.startswith('out_time_us='):
            try:
                out_time = int(line.split('=', 1)[1]) / 1_000_000
            except ValueError:
                pass
    return out_time


def convert_to_m4a(src, dst, normalise=False):
    """Convert to mono AAC in an .m4a container, which every browser plays."""
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-vn', '-ac', '1']
    if normalise:
        cmd += ['-af', 'loudnorm']
    cmd += ['-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', '-f', 'mp4', dst]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=CONVERT_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        raise AudioError("The recording took too long to process.")
    if result.returncode != 0:
        raise AudioError("The recording couldn't be converted.")
