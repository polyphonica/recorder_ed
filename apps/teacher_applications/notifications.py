"""
Email notifications for teacher applications.
Handles approval emails with signup tokens for applicants without accounts.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import logging

logger = logging.getLogger(__name__)


class TeacherSignupTokenGenerator:
    """
    Token generator for teacher signup links.
    Uses Django's signing framework to create secure, expiring tokens.
    """
    # Token expires after 7 days
    MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds

    def make_token(self, application):
        """
        Generate a secure token for the teacher application.

        Args:
            application: TeacherApplication instance

        Returns:
            Signed token string
        """
        signer = TimestampSigner()
        # Use application ID and email as the value to sign
        value = f"{application.id}:{application.email}"
        return signer.sign(value)

    def check_token(self, token):
        """
        Verify the token and extract application data.

        Args:
            token: Signed token string

        Returns:
            dict with 'application_id' and 'email' if valid, None otherwise
        """
        try:
            signer = TimestampSigner()
            # Verify signature and check expiration
            value = signer.unsign(token, max_age=self.MAX_AGE)
            application_id, email = value.split(':', 1)
            return {
                'application_id': int(application_id),
                'email': email
            }
        except (BadSignature, SignatureExpired, ValueError):
            return None


# Create instance
teacher_signup_token = TeacherSignupTokenGenerator()


def send_approval_email(request, application):
    """
    Send approval email with signup link to approved teacher applicant.

    Args:
        request: HTTP request object (for building absolute URLs)
        application: TeacherApplication instance

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Generate signup token
        token = teacher_signup_token.make_token(application)

        # Build signup URL
        current_site = get_current_site(request)
        signup_link = f"{request.scheme}://{current_site.domain}/accounts/teacher-signup/{token}/"

        # Prepare email context
        context = {
            'application': application,
            'signup_link': signup_link,
            'site_name': settings.SITE_NAME,
            'token_expiry_days': 7,
        }

        # Render email
        subject = f'Your teacher application has been approved! - {settings.SITE_NAME}'
        message = render_to_string('teacher_applications/emails/approval_email.txt', context)
        html_message = render_to_string('teacher_applications/emails/approval_email.html', context)

        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Approval email sent to {application.email} for application {application.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send approval email for application {application.id}: {e}")
        return False
