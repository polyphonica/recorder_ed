from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import WorkshopRegistration, WorkshopSession, WorkshopInterest, Workshop
from .image_utils import optimize_workshop_image
import logging
import sys

logger = logging.getLogger(__name__)


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
    
    # Count active registrations (including promoted students who hold places)
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


@receiver(pre_save, sender=Workshop)
def optimize_workshop_featured_image(sender, instance, **kwargs):
    """
    Automatically optimize workshop featured images before saving.

    This signal processes images when:
    1. A new workshop is created with an image
    2. An existing workshop's image is changed

    The signal will NOT process if:
    - No image is attached
    - Image hasn't changed (same file)
    - Image has already been optimized (contains '_optimized.jpg')

    Processing includes:
    - Resizing to 800x400px (2:1 aspect ratio)
    - Center cropping to maintain aspect ratio
    - JPEG optimization at 85% quality
    - Conversion to RGB (handles PNG transparency)
    """
    # Skip if no image
    if not instance.featured_image:
        return

    # Check if this is a new workshop or if the image has changed
    try:
        # Try to get the existing workshop from database
        old_instance = Workshop.objects.get(pk=instance.pk)
        old_image = old_instance.featured_image

        # If image hasn't changed, skip processing
        if old_image and old_image.name == instance.featured_image.name:
            logger.debug(f"Image unchanged for workshop '{instance.title}' - skipping optimization")
            return

    except Workshop.DoesNotExist:
        # New workshop - process the image
        logger.info(f"New workshop '{instance.title}' - will optimize image")
        pass

    # Check if image has already been optimized (to avoid re-processing)
    if '_optimized.jpg' in instance.featured_image.name:
        logger.debug(f"Image already optimized for workshop '{instance.title}' - skipping")
        return

    try:
        # Log the optimization attempt
        original_size = instance.featured_image.size
        logger.info(f"Optimizing image for workshop '{instance.title}' (original size: {original_size / 1024:.2f} KB)")

        # Optimize the image
        optimized_image = optimize_workshop_image(
            instance.featured_image,
            target_width=800,
            target_height=400,
            quality=85
        )

        if optimized_image:
            # Replace the image field with optimized version
            instance.featured_image = optimized_image
            new_size = sys.getsizeof(optimized_image)
            logger.info(
                f"Successfully optimized image for '{instance.title}' "
                f"(new size: {new_size / 1024:.2f} KB, "
                f"reduction: {((original_size - new_size) / original_size * 100):.1f}%)"
            )
        else:
            logger.warning(f"Image optimization returned None for '{instance.title}' - keeping original")

    except Exception as e:
        # Log error but don't prevent saving
        logger.error(f"Failed to optimize image for '{instance.title}': {str(e)}")
        # Image will be saved as-is if optimization fails