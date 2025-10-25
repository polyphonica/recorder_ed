from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.sites.models import Site
import logging

logger = logging.getLogger(__name__)


class WaitlistNotificationService:
    """Service for sending waitlist-related email notifications"""
    
    @staticmethod
    def get_site_name():
        """Get the current site name"""
        try:
            return Site.objects.get_current().name
        except:
            return getattr(settings, 'SITE_NAME', 'Workshop Platform')
    
    @staticmethod
    def send_promotion_notification(registration, promotion):
        """Send initial promotion notification to student"""
        try:
            # Generate confirmation URL
            confirmation_url = WaitlistNotificationService._build_confirmation_url(registration)
            
            context = {
                'registration': registration,
                'session': registration.session,
                'promotion': promotion,
                'confirmation_url': confirmation_url,
                'site_name': WaitlistNotificationService.get_site_name(),
            }
            
            # Render email content
            subject_and_message = render_to_string(
                'workshops/emails/waitlist_promotion_notification.txt', 
                context
            )
            
            # Extract subject (first line)
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '') if lines else 'Spot Available'
            message = '\n'.join(lines[1:]).strip()
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[registration.email],
                fail_silently=False,
            )
            
            # Mark notification as sent
            registration.promotion_notification_sent = True
            registration.save(update_fields=['promotion_notification_sent'])
            
            logger.info(f"Promotion notification sent to {registration.student.username} for session {registration.session.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send promotion notification to {registration.student.username}: {str(e)}")
            return False
    
    @staticmethod
    def send_promotion_reminder(registration, promotion):
        """Send reminder notification before deadline"""
        try:
            now = timezone.now()
            hours_remaining = (promotion.expires_at - now).total_seconds() / 3600
            
            confirmation_url = WaitlistNotificationService._build_confirmation_url(registration)
            
            context = {
                'registration': registration,
                'session': registration.session,
                'promotion': promotion,
                'confirmation_url': confirmation_url,
                'hours_remaining': hours_remaining,
                'site_name': WaitlistNotificationService.get_site_name(),
            }
            
            subject_and_message = render_to_string(
                'workshops/emails/promotion_reminder.txt', 
                context
            )
            
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '') if lines else 'Reminder - Confirm Your Spot'
            message = '\n'.join(lines[1:]).strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[registration.email],
                fail_silently=False,
            )
            
            logger.info(f"Promotion reminder sent to {registration.student.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send promotion reminder to {registration.student.username}: {str(e)}")
            return False
    
    @staticmethod
    def send_promotion_expired_notification(registration):
        """Send notification when promotion expires"""
        try:
            workshop_url = WaitlistNotificationService._build_workshop_url(registration.session.workshop)
            
            context = {
                'registration': registration,
                'session': registration.session,
                'workshop_url': workshop_url,
                'site_name': WaitlistNotificationService.get_site_name(),
            }
            
            subject_and_message = render_to_string(
                'workshops/emails/promotion_expired.txt', 
                context
            )
            
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '') if lines else 'Registration Deadline Passed'
            message = '\n'.join(lines[1:]).strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[registration.email],
                fail_silently=False,
            )
            
            logger.info(f"Promotion expired notification sent to {registration.student.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send promotion expired notification to {registration.student.username}: {str(e)}")
            return False
    
    @staticmethod
    def send_registration_confirmed_notification(registration):
        """Send confirmation when student confirms their promotion"""
        try:
            materials_url = WaitlistNotificationService._build_materials_url(registration.session)
            
            context = {
                'registration': registration,
                'session': registration.session,
                'materials_url': materials_url,
                'site_name': WaitlistNotificationService.get_site_name(),
            }
            
            subject_and_message = render_to_string(
                'workshops/emails/registration_confirmed.txt', 
                context
            )
            
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '') if lines else 'Registration Confirmed'
            message = '\n'.join(lines[1:]).strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[registration.email],
                fail_silently=False,
            )
            
            logger.info(f"Registration confirmed notification sent to {registration.student.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send registration confirmed notification to {registration.student.username}: {str(e)}")
            return False
    
    @staticmethod
    def _build_confirmation_url(registration):
        """Build URL for confirming waitlist promotion"""
        try:
            path = reverse('workshops:confirm_promotion', kwargs={'registration_id': registration.id})
            site = Site.objects.get_current()
            return f"http://{site.domain}{path}"
        except:
            return "#"  # Fallback
    
    @staticmethod
    def _build_workshop_url(workshop):
        """Build URL for workshop detail page"""
        try:
            path = reverse('workshops:detail', kwargs={'slug': workshop.slug})
            site = Site.objects.get_current()
            return f"http://{site.domain}{path}"
        except:
            return "#"  # Fallback
    
    @staticmethod
    def _build_materials_url(session):
        """Build URL for session materials page"""
        try:
            path = reverse('workshops:detail', kwargs={'slug': session.workshop.slug})
            site = Site.objects.get_current()
            return f"http://{site.domain}{path}#materials"
        except:
            return "#"  # Fallback