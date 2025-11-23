"""
Email notification service for support tickets.
Sends email notifications for ticket events.
"""

import logging
from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class TicketNotificationService(BaseNotificationService):
    """Service for sending ticket-related email notifications"""

    @staticmethod
    def send_ticket_created_notification(ticket):
        """
        Send confirmation email when a ticket is created.
        Goes to the ticket submitter.
        """
        try:
            # Build ticket URL
            ticket_url = TicketNotificationService.build_absolute_url(
                'support:ticket_detail',
                kwargs={'ticket_number': ticket.ticket_number},
                use_https=True
            )

            # Build email context
            context = {
                'ticket': ticket,
                'ticket_url': ticket_url,
                'site_name': TicketNotificationService.get_site_name(),
            }

            # Send email
            success = TicketNotificationService.send_templated_email(
                template_path='support/emails/ticket_created.txt',
                context=context,
                recipient_list=[ticket.email],
                default_subject=f'Support Ticket Created: {ticket.ticket_number}',
                fail_silently=False,
                log_description=f"Ticket created notification to {ticket.email}"
            )

            return success

        except Exception as e:
            logger.error(f"Failed to send ticket created notification: {str(e)}")
            return False

    @staticmethod
    def send_staff_reply_notification(ticket, message):
        """
        Send notification when staff replies to a ticket.
        Goes to the ticket submitter (not for internal notes).
        """
        if message.is_internal_note:
            return False  # Don't notify for internal notes

        try:
            # Build ticket URL
            ticket_url = TicketNotificationService.build_absolute_url(
                'support:ticket_detail',
                kwargs={'ticket_number': ticket.ticket_number},
                use_https=True
            )

            staff_name = message.author.get_full_name() or message.author.username if message.author else "Support Team"

            # Build email context
            context = {
                'ticket': ticket,
                'message': message,
                'staff_name': staff_name,
                'ticket_url': ticket_url,
                'site_name': TicketNotificationService.get_site_name(),
            }

            # Send email
            success = TicketNotificationService.send_templated_email(
                template_path='support/emails/staff_reply.txt',
                context=context,
                recipient_list=[ticket.email],
                default_subject=f'Response to Ticket {ticket.ticket_number}: {ticket.subject}',
                fail_silently=False,
                log_description=f"Staff reply notification to {ticket.email}"
            )

            return success

        except Exception as e:
            logger.error(f"Failed to send staff reply notification: {str(e)}")
            return False

    @staticmethod
    def send_status_changed_notification(ticket, old_status, new_status):
        """
        Send notification when ticket status changes.
        Goes to the ticket submitter.
        """
        try:
            # Only notify for significant status changes
            significant_statuses = ['resolved', 'closed', 'waiting_user']
            if new_status not in significant_statuses:
                return False

            # Build ticket URL
            ticket_url = TicketNotificationService.build_absolute_url(
                'support:ticket_detail',
                kwargs={'ticket_number': ticket.ticket_number},
                use_https=True
            )

            # Build email context
            context = {
                'ticket': ticket,
                'old_status': dict(ticket.STATUS_CHOICES).get(old_status),
                'new_status': dict(ticket.STATUS_CHOICES).get(new_status),
                'ticket_url': ticket_url,
                'site_name': TicketNotificationService.get_site_name(),
            }

            # Send email
            success = TicketNotificationService.send_templated_email(
                template_path='support/emails/status_changed.txt',
                context=context,
                recipient_list=[ticket.email],
                default_subject=f'Ticket {ticket.ticket_number} Status Updated',
                fail_silently=False,
                log_description=f"Status change notification to {ticket.email}"
            )

            return success

        except Exception as e:
            logger.error(f"Failed to send status changed notification: {str(e)}")
            return False

    @staticmethod
    def send_new_ticket_alert_to_staff(ticket):
        """
        Alert staff members when a new ticket is created.
        Goes to all staff members.
        For teacher applications, sends to admin/superuser emails.
        """
        try:
            from django.contrib.auth.models import User

            # For teacher applications, send to admin/superuser emails
            if ticket.category == 'teacher_application':
                admin_emails = list(
                    User.objects.filter(is_superuser=True, email__isnull=False)
                    .exclude(email='')
                    .values_list('email', flat=True)
                )

                if not admin_emails:
                    logger.info("No admin emails found for teacher application alert")
                    # Fall back to staff emails if no admin emails
                    admin_emails = list(
                        User.objects.filter(is_staff=True, email__isnull=False)
                        .exclude(email='')
                        .values_list('email', flat=True)
                    )

                if not admin_emails:
                    logger.warning("No admin or staff emails found for teacher application")
                    return False

                staff_emails = admin_emails
            else:
                # Get all staff users with email addresses for regular tickets
                staff_emails = list(
                    User.objects.filter(is_staff=True, email__isnull=False)
                    .exclude(email='')
                    .values_list('email', flat=True)
                )

            if not staff_emails:
                logger.info("No staff emails found for new ticket alert")
                return False

            # Build ticket URL
            ticket_url = TicketNotificationService.build_absolute_url(
                'support:ticket_detail',
                kwargs={'ticket_number': ticket.ticket_number},
                use_https=True
            )

            # Build email context
            context = {
                'ticket': ticket,
                'ticket_url': ticket_url,
                'site_name': TicketNotificationService.get_site_name(),
            }

            # Use different subject for teacher applications
            if ticket.category == 'teacher_application':
                subject = f'New Teacher Application: {ticket.ticket_number}'
            else:
                subject = f'New Support Ticket: {ticket.ticket_number}'

            # Send email
            success = TicketNotificationService.send_templated_email(
                template_path='support/emails/new_ticket_staff_alert.txt',
                context=context,
                recipient_list=staff_emails,
                default_subject=subject,
                fail_silently=False,
                log_description=f"New ticket alert to {'admin' if ticket.category == 'teacher_application' else 'staff'}"
            )

            return success

        except Exception as e:
            logger.error(f"Failed to send new ticket alert to staff: {str(e)}")
            return False
