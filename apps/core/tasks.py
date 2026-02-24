"""
Celery tasks for asynchronous email sending.
"""
from celery import shared_task
from django.core.mail import EmailMultiAlternatives, send_mail
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_task(self, subject, body, html_body, recipient_list, from_email):
    """
    Send an email asynchronously.

    Retries up to 3 times on failure with exponential backoff:
    - 1st retry: 60s
    - 2nd retry: 120s
    - 3rd retry: 240s

    Args:
        subject: Email subject line
        body: Plain text body
        html_body: HTML body (None for plain-text-only emails)
        recipient_list: List of recipient email addresses
        from_email: Sender email address
    """
    try:
        if html_body:
            email = EmailMultiAlternatives(subject, body, from_email, recipient_list)
            email.attach_alternative(html_body, 'text/html')
            email.send()
        else:
            send_mail(subject, body, from_email, recipient_list)
        logger.info("Email sent: '%s' to %s", subject, recipient_list)
    except Exception as exc:
        logger.error("Email failed: '%s' to %s: %s", subject, recipient_list, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
