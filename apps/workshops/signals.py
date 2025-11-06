from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import WorkshopRegistration, WorkshopSession, WorkshopInterest


@receiver(post_save, sender=WorkshopRegistration)
def update_session_registrations_on_save(sender, instance, created, **kwargs):
    """Update session registration count when registration is created or updated"""
    session = instance.session
    
    # Count active registrations (not cancelled)
    active_count = WorkshopRegistration.objects.filter(
        session=session,
        status__in=['registered', 'attended', 'waitlisted']
    ).count()
    
    # Update the session's current_registrations count
    if session.current_registrations != active_count:
        session.current_registrations = active_count
        session.save(update_fields=['current_registrations'])


@receiver(post_delete, sender=WorkshopRegistration)
def update_session_registrations_on_delete(sender, instance, **kwargs):
    """Update session registration count when registration is deleted"""
    session = instance.session
    
    # Count active registrations (including promoted students who hold spots)
    active_count = WorkshopRegistration.objects.filter(
        session=session,
        status__in=['registered', 'promoted', 'promoted', 'attended', 'waitlisted']
    ).count()
    
    # Update the session's current_registrations count
    if session.current_registrations != active_count:
        session.current_registrations = active_count
        session.save(update_fields=['current_registrations'])


@receiver(post_save, sender=WorkshopSession)
def process_waitlist_on_capacity_change(sender, instance, created, **kwargs):
    """Process waitlist promotions when session capacity increases"""
    if not created and 'max_participants' in (kwargs.get('update_fields') or []):
        # Only process if we're specifically updating max_participants
        promoted = instance.process_waitlist_promotions(reason='capacity_increase')

        # Send notification emails to promoted students and instructor
        if promoted:
            from .notifications import WaitlistNotificationService, InstructorNotificationService
            for registration in promoted:
                # Get the promotion record
                promotion = registration.promotions.filter(
                    expired=False,
                    confirmed_at__isnull=True
                ).first()

                if promotion:
                    # Notify student about promotion
                    WaitlistNotificationService.send_promotion_notification(registration, promotion)

                    # Notify instructor about waitlist promotion
                    try:
                        InstructorNotificationService.send_waitlist_promotion_notification(registration)
                    except Exception as e:
                        print(f"Failed to send instructor waitlist promotion notification: {e}")


@receiver(post_save, sender=WorkshopSession)
def notify_interested_users_on_new_session(sender, instance, created, **kwargs):
    """Notify users who expressed interest when a new session is created"""
    if created and instance.is_active:
        from .notifications import WorkshopInterestNotificationService
        import logging
        logger = logging.getLogger(__name__)

        # Get all active interest requests for this workshop that want immediate notifications
        interested_users = WorkshopInterest.objects.filter(
            workshop=instance.workshop,
            is_active=True,
            notify_immediately=True,
            has_been_notified=False
        )

        notification_count = 0
        for interest in interested_users:
            try:
                # Send notification email
                success = WorkshopInterestNotificationService.send_new_session_notification(interest, instance)

                if success:
                    # Mark as notified
                    interest.has_been_notified = True
                    interest.notification_sent_at = timezone.now()
                    interest.save(update_fields=['has_been_notified', 'notification_sent_at'])
                    notification_count += 1
            except Exception as e:
                logger.error(f"Failed to notify interested user {interest.user.username}: {str(e)}")

        if notification_count > 0:
            logger.info(f"Sent {notification_count} new session notifications for workshop '{instance.workshop.title}'")