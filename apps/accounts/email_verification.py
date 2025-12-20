"""
Email verification utilities for user registration.
Uses Django's built-in token generation for security.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom token generator for email verification.
    Only uses password and email verified status (not last_login).
    This prevents tokens from being invalidated when user logs in.
    """
    def _make_hash_value(self, user, timestamp):
        # Use email_verified status instead of last_login
        try:
            email_verified = user.profile.email_verified if hasattr(user, 'profile') else False
        except:
            email_verified = False
        return f"{user.pk}{timestamp}{user.password}{email_verified}"


# Create instance of custom token generator
email_verification_token = EmailVerificationTokenGenerator()


def send_verification_email(request, user):
    """
    Send email verification link to the user.

    Args:
        request: HTTP request object (for building absolute URLs)
        user: User instance to send verification email to
    """
    # Generate token using custom generator
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Build verification URL
    current_site = get_current_site(request)
    verification_link = f"{request.scheme}://{current_site.domain}/accounts/verify-email/{uid}/{token}/"

    # Prepare email context
    is_guardian = user.profile.is_guardian if hasattr(user, 'profile') else False
    context = {
        'user': user,
        'verification_link': verification_link,
        'site_name': settings.SITE_NAME,
        'is_guardian': is_guardian,
    }

    # Render email
    subject = f'Verify your email address - {settings.SITE_NAME}'
    message = render_to_string('accounts/emails/verification_email.txt', context)
    html_message = render_to_string('accounts/emails/verification_email.html', context)

    # Send email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def verify_token(uidb64, token):
    """
    Verify the email verification token.

    Args:
        uidb64: Base64 encoded user ID
        token: Verification token

    Returns:
        User instance if valid, None otherwise
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None

    # Check if token is valid using custom generator
    if email_verification_token.check_token(user, token):
        return user

    return None
