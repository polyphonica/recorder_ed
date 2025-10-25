from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import WorkshopRegistration, WorkshopSession


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
        
        # Send notification emails to promoted students
        if promoted:
            from .notifications import WaitlistNotificationService
            for registration in promoted:
                # Get the promotion record
                promotion = registration.promotions.filter(
                    expired=False,
                    confirmed_at__isnull=True
                ).first()
                
                if promotion:
                    WaitlistNotificationService.send_promotion_notification(registration, promotion)