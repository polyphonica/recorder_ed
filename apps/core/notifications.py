"""
Centralized email notification service for consistent email sending across apps
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site
import logging

logger = logging.getLogger(__name__)


class BaseNotificationService:
    """
    Base service for sending email notifications with consistent patterns.

    Provides common functionality for:
    - Template rendering
    - Subject extraction from templates
    - Email sending with error handling
    - Site name retrieval
    """

    @staticmethod
    def get_site_name():
        """Get the current site name from Django sites framework or settings"""
        try:
            return Site.objects.get_current().name
        except Exception:
            return getattr(settings, 'SITE_NAME', 'RECORDERED')

    @staticmethod
    def send_templated_email(
        template_path,
        context,
        recipient_list,
        default_subject='Notification',
        from_email=None,
        fail_silently=True,
        log_description=None
    ):
        """
        Send an email using a template with consistent error handling.

        Args:
            template_path: Path to email template (e.g., 'app/emails/notification.txt')
            context: Dictionary of context variables for template
            recipient_list: List of recipient email addresses
            default_subject: Fallback subject if not in template
            from_email: From email address (defaults to DEFAULT_FROM_EMAIL)
            fail_silently: Whether to suppress email errors
            log_description: Optional description for logging

        Returns:
            True if email sent successfully, False otherwise

        Template Format:
            First line should be: Subject: Your subject here
            Remaining lines are the email body
        """
        try:
            # Ensure site_name is in context
            if 'site_name' not in context:
                context['site_name'] = BaseNotificationService.get_site_name()

            # Render template
            subject_and_message = render_to_string(template_path, context)

            # Extract subject from first line
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '').strip() if lines else default_subject
            message = '\n'.join(lines[1:]).strip()

            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=fail_silently,
            )

            # Log success
            if log_description:
                logger.info(f"Email sent: {log_description}")

            return True

        except Exception as e:
            logger.error(f"Error sending email: {log_description or template_path} - {str(e)}")
            if not fail_silently:
                raise
            return False

    @staticmethod
    def send_simple_email(
        subject,
        message,
        recipient_list,
        from_email=None,
        fail_silently=True,
        log_description=None
    ):
        """
        Send a simple plain text email without template rendering.

        Args:
            subject: Email subject line
            message: Email body text
            recipient_list: List of recipient email addresses
            from_email: From email address (defaults to DEFAULT_FROM_EMAIL)
            fail_silently: Whether to suppress email errors
            log_description: Optional description for logging

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=fail_silently,
            )

            # Log success
            if log_description:
                logger.info(f"Email sent: {log_description}")

            return True

        except Exception as e:
            logger.error(f"Error sending email: {log_description or subject} - {str(e)}")
            if not fail_silently:
                raise
            return False
