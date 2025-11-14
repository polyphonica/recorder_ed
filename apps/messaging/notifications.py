"""
Email notification service for messaging app.
Sends email notifications when users receive new messages.
"""

import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class MessageNotificationService(BaseNotificationService):
    """Service for sending message-related email notifications"""

    @staticmethod
    def send_new_message_notification(message):
        """
        Send email notification when a user receives a new message.
        Only sends if recipient has email_on_new_message enabled.
        """
        try:
            conversation = message.conversation
            sender = message.sender

            # Determine recipient (the other participant)
            recipient = conversation.get_other_participant(sender)

            # Check if recipient has email notifications enabled
            if not hasattr(recipient, 'profile') or not recipient.profile.email_on_new_message:
                logger.info(f"Skipping email notification - {recipient.username} has notifications disabled")
                return False

            if not recipient.email:
                logger.warning(f"No email address for {recipient.username}")
                return False

            # Build conversation URL
            conversation_url = MessageNotificationService.build_absolute_url(
                'messaging:conversation_detail',
                kwargs={'conversation_id': str(conversation.id)},
                use_https=True
            )

            # Determine context based on domain
            context_info = ""
            if conversation.domain == 'workshop' and conversation.workshop:
                context_info = f"Workshop: {conversation.workshop.title}"
            elif conversation.domain == 'private_teaching':
                if conversation.child_profile:
                    context_info = f"Private Teaching - {conversation.child_profile.full_name}"
                else:
                    context_info = "Private Teaching"

            # Build email context
            context = {
                'recipient': recipient,
                'recipient_name': recipient.get_full_name() or recipient.username,
                'sender': sender,
                'sender_name': sender.get_full_name() or sender.username,
                'message': message,
                'conversation': conversation,
                'context_info': context_info,
                'conversation_url': conversation_url,
                'site_name': MessageNotificationService.get_site_name(),
            }

            # Send email
            success = MessageNotificationService.send_templated_email(
                template_path='messaging/emails/new_message_notification.txt',
                context=context,
                recipient_list=[recipient.email],
                default_subject='New Message',
                fail_silently=False,
                log_description=f"New message notification to {recipient.username} from {sender.username}"
            )

            return success

        except Exception as e:
            logger.error(f"Failed to send new message notification: {str(e)}")
            return False
