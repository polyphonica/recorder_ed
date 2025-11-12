from django.urls import reverse
from django.utils import timezone
import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class WaitlistNotificationService(BaseNotificationService):
    """Service for sending waitlist-related email notifications"""

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
            }

            # Send email using base service
            success = WaitlistNotificationService.send_templated_email(
                template_path='workshops/emails/waitlist_promotion_notification.txt',
                context=context,
                recipient_list=[registration.email],
                default_subject='Spot Available',
                fail_silently=False,
                log_description=f"Promotion notification to {registration.student.username} for session {registration.session.id}"
            )

            if success:
                # Mark notification as sent
                registration.promotion_notification_sent = True
                registration.save(update_fields=['promotion_notification_sent'])

            return success

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
            }

            return WaitlistNotificationService.send_templated_email(
                template_path='workshops/emails/promotion_reminder.txt',
                context=context,
                recipient_list=[registration.email],
                default_subject='Reminder - Confirm Your Spot',
                fail_silently=False,
                log_description=f"Promotion reminder to {registration.student.username}"
            )

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
            }

            return WaitlistNotificationService.send_templated_email(
                template_path='workshops/emails/promotion_expired.txt',
                context=context,
                recipient_list=[registration.email],
                default_subject='Registration Deadline Passed',
                fail_silently=False,
                log_description=f"Promotion expired notification to {registration.student.username}"
            )

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
            }

            return WaitlistNotificationService.send_templated_email(
                template_path='workshops/emails/registration_confirmed.txt',
                context=context,
                recipient_list=[registration.email],
                default_subject='Registration Confirmed',
                fail_silently=False,
                log_description=f"Registration confirmed notification to {registration.student.username}"
            )

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


class InstructorNotificationService(BaseNotificationService):
    """Service for sending workshop-related email notifications to instructors"""

    @staticmethod
    def send_new_registration_notification(registration):
        """Send notification to instructor when someone registers for their workshop"""
        try:
            # Get the instructor email
            instructor = registration.session.workshop.instructor
            if not instructor or not instructor.email:
                logger.warning(f"No instructor email found for workshop {registration.session.workshop.id}")
                return False

            # Build URLs
            registrations_url = InstructorNotificationService._build_registrations_url(registration.session)

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'registrations_url': registrations_url,
            }

            return InstructorNotificationService.send_templated_email(
                template_path='workshops/emails/instructor_new_registration.txt',
                context=context,
                recipient_list=[instructor.email],
                default_subject='New Workshop Registration',
                fail_silently=False,
                log_description=f"New registration notification to instructor {instructor.username} for session {registration.session.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send new registration notification to instructor: {str(e)}")
            return False

    @staticmethod
    def send_registration_cancelled_notification(registration):
        """Send notification to instructor when someone cancels their registration"""
        try:
            # Get the instructor email
            instructor = registration.session.workshop.instructor
            if not instructor or not instructor.email:
                logger.warning(f"No instructor email found for workshop {registration.session.workshop.id}")
                return False

            # Build URLs
            registrations_url = InstructorNotificationService._build_registrations_url(registration.session)

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'registrations_url': registrations_url,
            }

            return InstructorNotificationService.send_templated_email(
                template_path='workshops/emails/instructor_registration_cancelled.txt',
                context=context,
                recipient_list=[instructor.email],
                default_subject='Workshop Registration Cancelled',
                fail_silently=False,
                log_description=f"Cancellation notification to instructor {instructor.username} for session {registration.session.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation notification to instructor: {str(e)}")
            return False

    @staticmethod
    def send_waitlist_promotion_notification(registration):
        """Send notification to instructor when a waitlisted student is promoted"""
        try:
            # Get the instructor email
            instructor = registration.session.workshop.instructor
            if not instructor or not instructor.email:
                logger.warning(f"No instructor email found for workshop {registration.session.workshop.id}")
                return False

            # Build URLs
            registrations_url = InstructorNotificationService._build_registrations_url(registration.session)

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'registrations_url': registrations_url,
            }

            return InstructorNotificationService.send_templated_email(
                template_path='workshops/emails/instructor_waitlist_promotion.txt',
                context=context,
                recipient_list=[instructor.email],
                default_subject='Waitlist Student Promoted',
                fail_silently=False,
                log_description=f"Waitlist promotion notification to instructor {instructor.username} for session {registration.session.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send waitlist promotion notification to instructor: {str(e)}")
            return False

    @staticmethod
    def _build_registrations_url(session):
        """Build URL for session registrations management page"""
        try:
            path = reverse('workshops:session_registrations', kwargs={'session_id': session.id})
            site = Site.objects.get_current()
            return f"http://{site.domain}{path}"
        except:
            return "#"  # Fallback


class WorkshopInterestNotificationService(BaseNotificationService):
    """Service for sending workshop interest-related email notifications"""

    @staticmethod
    def send_interest_confirmation(interest):
        """Send confirmation email when user expresses interest in a workshop"""
        try:
            # Build URLs
            workshop_url = WorkshopInterestNotificationService._build_workshop_url(interest.workshop)
            browse_url = WorkshopInterestNotificationService._build_browse_url()

            context = {
                'interest': interest,
                'workshop': interest.workshop,
                'user': interest.user,
                'workshop_url': workshop_url,
                'browse_url': browse_url,
            }

            return WorkshopInterestNotificationService.send_templated_email(
                template_path='workshops/emails/workshop_interest_confirmation.txt',
                context=context,
                recipient_list=[interest.email],
                default_subject='Workshop Interest Confirmation',
                fail_silently=False,
                log_description=f"Interest confirmation to {interest.user.username} for workshop {interest.workshop.title}"
            )

        except Exception as e:
            logger.error(f"Failed to send interest confirmation to {interest.user.username}: {str(e)}")
            return False

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
    def _build_browse_url():
        """Build URL for workshop list page"""
        try:
            path = reverse('workshops:list')
            site = Site.objects.get_current()
            return f"http://{site.domain}{path}"
        except:
            return "#"  # Fallback

    @staticmethod
    def send_new_session_notification(interest, session):
        """Send notification email when a new session is created for a workshop of interest"""
        try:
            # Build URLs
            workshop_url = WorkshopInterestNotificationService._build_workshop_url(interest.workshop)
            registration_url = WorkshopInterestNotificationService._build_registration_url(session)

            context = {
                'interest': interest,
                'workshop': interest.workshop,
                'session': session,
                'user': interest.user,
                'workshop_url': workshop_url,
                'registration_url': registration_url,
            }

            return WorkshopInterestNotificationService.send_templated_email(
                template_path='workshops/emails/new_session_notification.txt',
                context=context,
                recipient_list=[interest.email],
                default_subject=f'New Session Available - {interest.workshop.title}',
                fail_silently=False,
                log_description=f"New session notification to {interest.user.username} for workshop {interest.workshop.title}"
            )

        except Exception as e:
            logger.error(f"Failed to send new session notification to {interest.user.username}: {str(e)}")
            return False

    @staticmethod
    def _build_registration_url(session):
        """Build URL for session registration page"""
        try:
            path = reverse('workshops:register', kwargs={
                'workshop_slug': session.workshop.slug,
                'session_id': session.id
            })
            site = Site.objects.get_current()
            return f"http://{site.domain}{path}"
        except:
            return "#"  # Fallback