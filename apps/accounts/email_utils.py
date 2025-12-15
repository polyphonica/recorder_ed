"""
Email utilities for accounts app.
Provides helper functions for generating email-related links.
"""
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site


def generate_unsubscribe_url(user, request=None):
    """
    Generate an unsubscribe URL for workshop email notifications.

    Args:
        user: User object to generate unsubscribe link for
        request: Optional request object to build absolute URL

    Returns:
        str: Unsubscribe URL (absolute if request provided, relative otherwise)
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    unsubscribe_path = reverse('accounts:unsubscribe_workshops', kwargs={
        'uidb64': uidb64,
        'token': token,
    })

    if request:
        # Build absolute URL
        current_site = get_current_site(request)
        protocol = 'https' if request.is_secure() else 'http'
        return f"{protocol}://{current_site.domain}{unsubscribe_path}"

    return unsubscribe_path
