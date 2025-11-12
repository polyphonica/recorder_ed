"""
Centralized email notification service for consistent email sending across apps
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
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
    - Absolute URL building with current site domain
    """

    @staticmethod
    def get_site_name():
        """Get the current site name from Django sites framework or settings"""
        try:
            return Site.objects.get_current().name
        except Exception:
            return getattr(settings, 'SITE_NAME', 'RECORDERED')

    @staticmethod
    def build_absolute_url(url_name, kwargs=None, use_https=True, fragment=None):
        """
        Build an absolute URL using the current site domain.

        Args:
            url_name: Django URL name to reverse (e.g., 'workshops:detail')
            kwargs: Dictionary of URL parameters (e.g., {'slug': 'my-workshop'})
            use_https: Whether to use https:// or http:// (default: True)
            fragment: Optional fragment/anchor to append (e.g., 'materials' for #materials)

        Returns:
            Full absolute URL string, or "#" if URL building fails

        Example:
            build_absolute_url('workshops:detail', {'slug': 'recorder-101'})
            # Returns: "https://www.recorder-ed.com/workshops/recorder-101/"
        """
        try:
            # Build the path using Django's reverse
            path = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)

            # Get current site domain
            site = Site.objects.get_current()
            protocol = 'https' if use_https else 'http'

            # Build full URL
            url = f"{protocol}://{site.domain}{path}"

            # Append fragment if provided
            if fragment:
                url = f"{url}#{fragment}"

            return url

        except Exception as e:
            logger.warning(f"Failed to build URL for {url_name}: {str(e)}")
            return "#"  # Fallback

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

        Automatically sends multipart emails (HTML + plain text) if an HTML template exists.
        Falls back to plain text only if no HTML template is found.

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
            Plain text (.txt): First line should be: Subject: Your subject here
            HTML (.html): Use {% block subject %}Your subject here{% endblock %} in template
        """
        try:
            # Ensure site_name is in context
            if 'site_name' not in context:
                context['site_name'] = BaseNotificationService.get_site_name()

            # Render plain text template
            subject_and_message = render_to_string(template_path, context)

            # Extract subject from first line
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '').strip() if lines else default_subject
            text_message = '\n'.join(lines[1:]).strip()

            # Check if HTML template exists
            html_template_path = template_path.replace('.txt', '.html')
            html_message = None

            try:
                # Try to render HTML template
                html_message = render_to_string(html_template_path, context)
            except Exception:
                # HTML template doesn't exist, that's OK - we'll send plain text only
                pass

            # Send multipart email if we have HTML, otherwise plain text only
            if html_message:
                # Create multipart email
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=fail_silently)

                if log_description:
                    logger.info(f"Multipart email sent: {log_description}")
            else:
                # Send plain text only
                send_mail(
                    subject=subject,
                    message=text_message,
                    from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    fail_silently=fail_silently,
                )

                if log_description:
                    logger.info(f"Plain text email sent: {log_description}")

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
