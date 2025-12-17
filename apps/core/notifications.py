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
            return getattr(settings, 'SITE_NAME', 'Recorder-ed')

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

    @classmethod
    def build_detail_url(cls, url_name, obj, slug_field='slug'):
        """
        Build URL for detail pages using an object's slug or other identifier.

        Args:
            url_name: Django URL name (e.g., 'workshops:detail')
            obj: Model instance with the identifier field
            slug_field: Name of the field to use (default: 'slug')

        Returns:
            Absolute URL string

        Example:
            build_detail_url('workshops:detail', workshop)
            # Same as build_absolute_url('workshops:detail', {'slug': workshop.slug})
        """
        return cls.build_absolute_url(url_name, kwargs={slug_field: getattr(obj, slug_field)})

    @classmethod
    def build_action_url(cls, url_name, obj, id_field='id'):
        """
        Build URL for action pages using an object's ID or other identifier.

        Args:
            url_name: Django URL name (e.g., 'workshops:confirm_promotion')
            obj: Model instance with the identifier field
            id_field: Name of the kwarg in the URL pattern (e.g., 'registration_id', 'session_id')

        Returns:
            Absolute URL string

        Example:
            build_action_url('workshops:confirm_promotion', registration, 'registration_id')
            # Uses registration.id for the URL

            build_action_url('workshops:session_registrations', session, 'session_id')
            # Uses session.id for the URL
        """
        # Always use the object's id attribute for the URL value
        field_value = obj.id
        return cls.build_absolute_url(url_name, kwargs={id_field: field_value})

    @staticmethod
    def build_base_context(**extra):
        """
        Build base context for all notifications with site_name.

        Args:
            **extra: Additional context variables to include

        Returns:
            Dictionary with site_name and any additional context

        Example:
            context = build_base_context(user=user, action='enrollment')
            # Returns: {'site_name': 'Recorder-ed', 'user': user, 'action': 'enrollment'}
        """
        context = {
            'site_name': BaseNotificationService.get_site_name(),
        }
        context.update(extra)
        return context

    @staticmethod
    def add_user_context(context, user, role='user'):
        """
        Add user-related context fields to existing context.

        Args:
            context: Existing context dictionary to update
            user: User instance to add
            role: Prefix for context keys (default: 'user')

        Returns:
            Updated context dictionary

        Example:
            context = {'site_name': 'Recorder-ed'}
            add_user_context(context, instructor, 'instructor')
            # context now has: instructor_name, instructor_email, instructor
        """
        if user:
            full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
            username = user.username if hasattr(user, 'username') else str(user)

            context[f'{role}_name'] = full_name or username
            context[f'{role}_email'] = user.email if hasattr(user, 'email') else ''
            context[role] = user
        return context

    @staticmethod
    def validate_email(user, log_prefix=''):
        """
        Validate that a user has a valid email address.

        Args:
            user: User instance to validate (can be None)
            log_prefix: Optional prefix for log messages (e.g., "Student", "Instructor")

        Returns:
            tuple: (is_valid: bool, email: str|None)
                - is_valid: True if user has valid email, False otherwise
                - email: The email address if valid, None otherwise

        Example:
            is_valid, email = BaseNotificationService.validate_email(user, 'Student')
            if not is_valid:
                return False
            # Use email for sending...
        """
        if not user:
            logger.warning(f"{log_prefix} user is None - cannot send email")
            return False, None

        if not hasattr(user, 'email') or not user.email:
            user_identifier = getattr(user, 'username', str(user))
            logger.warning(f"No email address found for {log_prefix} {user_identifier}")
            return False, None

        return True, user.email

    @staticmethod
    def check_opt_out(user, opt_out_field='workshop_email_notifications'):
        """
        Check if user has opted out of email notifications.

        Args:
            user: User instance to check (can be None)
            opt_out_field: Name of the profile field to check
                Common values: 'workshop_email_notifications', 'email_on_new_message'

        Returns:
            bool: True if email should be sent (user opted IN or profile missing)
                  False if user opted out (should NOT send email)

        Example:
            if not BaseNotificationService.check_opt_out(user, 'workshop_email_notifications'):
                logger.info(f"User {user.username} has opted out")
                return False
        """
        if not user:
            return True  # Default to sending if no user (shouldn't happen, but safe default)

        if not hasattr(user, 'profile'):
            # No profile exists - default to sending emails
            logger.debug(f"User {getattr(user, 'username', str(user))} has no profile - defaulting to send")
            return True

        try:
            opt_out_value = getattr(user.profile, opt_out_field, None)
            if opt_out_value is None:
                # Field doesn't exist on profile - default to sending
                logger.debug(f"Profile field {opt_out_field} not found - defaulting to send")
                return True

            # Field exists - use its value (True = send, False = opted out)
            return bool(opt_out_value)

        except Exception as e:
            logger.warning(f"Error checking opt-out field {opt_out_field}: {e} - defaulting to send")
            return True  # Default to sending on error (fail open)

    @staticmethod
    def get_display_name(user, fallback='User'):
        """
        Get display name for a user (full name, username, or fallback).

        Args:
            user: User instance to get name from (can be None)
            fallback: Fallback string if user is None or has no name/username

        Returns:
            str: User's full name, username, or fallback (never returns None/empty)

        Example:
            user_name = BaseNotificationService.get_display_name(user)
            # Returns "John Doe" or "jdoe" or "User"

            teacher_name = BaseNotificationService.get_display_name(teacher, 'Instructor')
            # Returns name or "Instructor" as fallback
        """
        if not user:
            return fallback

        # Try get_full_name() first
        if hasattr(user, 'get_full_name'):
            full_name = user.get_full_name()
            if full_name:  # Check for non-empty string
                return full_name

        # Fall back to username
        if hasattr(user, 'username') and user.username:
            return user.username

        # Last resort: use str(user) or fallback
        user_str = str(user)
        return user_str if user_str else fallback

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
