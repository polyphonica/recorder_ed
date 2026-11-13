"""
Cloudflare Turnstile bot protection for public forms.

Forms add `turnstile = TurnstileField()` and render `{{ form.turnstile }}`;
hand-written forms use `{% load turnstile %}{% turnstile_widget %}` plus
`verify_turnstile(request)` in the view. With no keys configured the widget
renders nothing and every check passes, so forms keep working.
"""
import logging

import requests
from django import forms
from django.conf import settings
from django.utils.html import format_html

logger = logging.getLogger(__name__)

SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
SITEVERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
RESPONSE_FIELD = 'cf-turnstile-response'
ERROR_MESSAGE = 'Please complete the verification check and try again.'


def turnstile_enabled():
    return bool(settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY)


def verify_turnstile_token(token):
    """Check a widget token with Cloudflare. Fails open if Cloudflare can't be reached."""
    if not turnstile_enabled():
        return True
    if not token:
        return False
    try:
        response = requests.post(
            SITEVERIFY_URL,
            data={'secret': settings.TURNSTILE_SECRET_KEY, 'response': token},
            timeout=5,
        )
        return bool(response.json().get('success'))
    except (requests.RequestException, ValueError) as e:
        # Don't lock real people out during a Cloudflare outage; the
        # honeypot and timing checks still apply
        logger.warning(f"Turnstile verification unavailable: {e}")
        return True


def verify_turnstile(request):
    return verify_turnstile_token(request.POST.get(RESPONSE_FIELD, ''))


def widget_html():
    """
    Widget markup. A page can hold several widgets (e.g. both workshop interest
    forms), so the script is added once, after the page has parsed, and then
    renders every widget it finds.
    """
    if not turnstile_enabled():
        return ''
    return format_html(
        '<div class="cf-turnstile" data-sitekey="{}" data-theme="light" data-size="flexible"></div>'
        '<script>if (!window.turnstileScriptAdded) {{'
        'window.turnstileScriptAdded = true;'
        'document.addEventListener("DOMContentLoaded", function () {{'
        'var s = document.createElement("script"); s.src = "{}"; s.async = true;'
        'document.head.appendChild(s);'
        '}});'
        '}}</script>',
        settings.TURNSTILE_SITE_KEY,
        SCRIPT_URL,
    )


class TurnstileWidget(forms.Widget):
    def value_from_datadict(self, data, files, name):
        return data.get(RESPONSE_FIELD, '')

    def render(self, name, value, attrs=None, renderer=None):
        return widget_html()


class TurnstileField(forms.Field):
    widget = TurnstileWidget

    def __init__(self, **kwargs):
        kwargs.setdefault('label', '')
        kwargs.setdefault('required', False)  # Checked in validate() so disabled keys pass
        super().__init__(**kwargs)

    def validate(self, value):
        super().validate(value)
        if not verify_turnstile_token(value):
            raise forms.ValidationError(ERROR_MESSAGE)
