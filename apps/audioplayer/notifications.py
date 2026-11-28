"""Emails about the Play-Along Library."""
import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class PlayalongNotificationService(BaseNotificationService):

    @staticmethod
    def _edit_url(item):
        from .models import Piece
        if isinstance(item, Piece):
            return PlayalongNotificationService.build_absolute_url('audioplayer:piece_edit', {'pk': item.pk})
        return PlayalongNotificationService.build_absolute_url('audioplayer:collection_edit', {'pk': item.pk})

    @staticmethod
    def _send_permission_email(item, template, subject, description):
        try:
            teacher = item.created_by
            is_valid, email = PlayalongNotificationService.validate_email(teacher, 'Teacher')
            if not is_valid:
                return False
            context = {
                'item': item,
                'expires': item.permission_expires,
                'teacher_name': PlayalongNotificationService.get_display_name(teacher, 'Teacher'),
                'edit_url': PlayalongNotificationService._edit_url(item),
            }
            return PlayalongNotificationService.send_templated_email(
                template_path=f'audioplayer/emails/{template}.txt',
                context=context,
                recipient_list=[email],
                default_subject=subject,
                fail_silently=False,
                log_description=f'{description} for {item}',
            )
        except Exception as e:
            logger.error(f'Failed to send {description} for {item}: {e}')
            return False

    @staticmethod
    def send_permission_expiring(item):
        return PlayalongNotificationService._send_permission_email(
            item, 'permission_expiring', 'Play-along permission expiring', 'Permission expiry reminder')

    @staticmethod
    def send_permission_expired(item):
        return PlayalongNotificationService._send_permission_email(
            item, 'permission_expired', 'Play-along made private', 'Permission expired notice')

    @staticmethod
    def send_library_welcome(user):
        """Sent once, when someone who signed up from the library verifies their email."""
        from .models import Piece, PieceCollection
        try:
            is_valid, email = PlayalongNotificationService.validate_email(user, 'Library user')
            if not is_valid:
                return False
            featured = list(PieceCollection.objects.filter(is_public=True, is_featured=True)[:3]) + list(
                Piece.objects.filter(is_public=True, show_in_library=True, is_featured=True)[:3])
            suggestions = [
                {'title': str(item), 'url': PlayalongNotificationService.build_absolute_url(
                    'playalongs:collection' if isinstance(item, PieceCollection) else 'playalongs:piece',
                    {'slug': item.slug})}
                for item in featured[:3]
            ]
            context = {
                'user_name': PlayalongNotificationService.get_display_name(user, 'there'),
                'suggestions': suggestions,
                'library_url': PlayalongNotificationService.build_absolute_url('playalongs:library'),
                'home_url': PlayalongNotificationService.build_absolute_url('domain_selector'),
            }
            return PlayalongNotificationService.send_templated_email(
                template_path='audioplayer/emails/library_welcome.txt',
                context=context,
                recipient_list=[email],
                default_subject='Welcome to the Recorder-ed Play-Along Library',
                fail_silently=False,
                log_description=f'Library welcome email to {user}',
            )
        except Exception as e:
            logger.error(f'Failed to send library welcome email to {user}: {e}')
            return False
