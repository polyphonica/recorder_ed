"""
Private storage for playalong files (stems, score PDFs, notation images).

Files live under PRIVATE_MEDIA_ROOT, which nginx does not serve publicly.
Their URLs are signed links to `audioplayer:protected_file` that expire, so a
file can only be fetched shortly after a page that checked access handed out
its link.

Links are signed per time window rather than per request, so the same file
gets the same URL for a few hours and browsers can cache the audio.
"""
import os
import time

from django.core import signing
from django.urls import reverse

from apps.practice.models import PrivateMediaStorage

# Only files under this folder can be served through a signed link
PROTECTED_PREFIX = 'audioplayer/'

SIGNING_SALT = 'audioplayer.protected-file'

# A link is minted in the current window and accepted for one more after it,
# so it lasts between WINDOW_SECONDS and twice that.
WINDOW_SECONDS = 6 * 60 * 60


def _current_window():
    return int(time.time() // WINDOW_SECONDS)


def make_token(name):
    return signing.dumps({'n': name, 'w': _current_window()}, salt=SIGNING_SALT, compress=True)


def read_token(token):
    """Return the file name a token grants, or None if it is invalid or expired."""
    try:
        data = signing.loads(token, salt=SIGNING_SALT)
    except signing.BadSignature:
        return None
    name, window = data.get('n'), data.get('w')
    if not isinstance(name, str) or not isinstance(window, int):
        return None
    if not 0 <= _current_window() - window <= 1:
        return None
    if not name.startswith(PROTECTED_PREFIX) or '..' in name.split('/'):
        return None
    return name


class ProtectedPlayalongStorage(PrivateMediaStorage):
    def url(self, name):
        # The file's own name goes last so downloads keep a sensible filename
        return reverse('audioplayer:protected_file', kwargs={
            'token': make_token(name),
            'filename': os.path.basename(name),
        })


def protected_storage():
    """A callable so migrations don't capture the server's path."""
    return ProtectedPlayalongStorage()
