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

            # Determine recipient email - use registration.email if available, else student.email
            recipient_email = registration.email if registration.email else registration.student.email

            if not recipient_email:
                logger.error(f"No email address found for registration {registration.id} - student {registration.student.username}")
                return False

            logger.info(f"Sending promotion notification to {recipient_email} for registration {registration.id}")

            # Send email using base service
            success = WaitlistNotificationService.send_templated_email(
                template_path='workshops/emails/waitlist_promotion_notification.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject='Spot Available',
                fail_silently=False,
                log_description=f"Promotion notification to {registration.student.username} ({recipient_email}) for session {registration.session.id}"
            )

            if success:
                logger.info(f"Successfully sent promotion notification to {recipient_email}")
                # Mark notification as sent
                registration.promotion_notification_sent = True
                registration.save(update_fields=['promotion_notification_sent'])
            else:
                logger.error(f"Failed to send promotion notification to {recipient_email} - send_templated_email returned False")

            return success

        except Exception as e:
            logger.error(f"Exception sending promotion notification to {registration.student.username}: {str(e)}", exc_info=True)
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
        return WaitlistNotificationService.build_action_url(
            'workshops:confirm_promotion',
            registration,
            'registration_id'
        )

    @staticmethod
    def _build_workshop_url(workshop):
        """Build URL for workshop detail page"""
        return WaitlistNotificationService.build_detail_url('workshops:detail', workshop)

    @staticmethod
    def _build_materials_url(session):
        """Build URL for session materials page"""
        return WaitlistNotificationService.build_absolute_url(
            'workshops:detail',
            kwargs={'slug': session.workshop.slug},
            fragment='materials'
        )


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
        return InstructorNotificationService.build_action_url(
            'workshops:session_registrations',
            session,
            'session_id'
        )


class StudentNotificationService(BaseNotificationService):
    """Service for sending workshop-related email notifications to students"""

    @staticmethod
    def send_registration_confirmation(registration):
        """Send registration confirmation email to student for a single workshop"""
        try:
            # Get student email
            if not registration.student or not registration.student.email:
                logger.warning(f"No student email found for registration {registration.id}")
                return False

            guardian_email = registration.email or registration.student.email

            # Build URLs
            my_registrations_url = StudentNotificationService.build_absolute_url(
                'workshops:my_registrations'
            )

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'student_name': registration.student_name,  # Uses property for child or adult
                'is_child_registration': registration.is_for_child,  # Uses inherited property
                'my_registrations_url': my_registrations_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='workshops/emails/student_registration_confirmation.txt',
                context=context,
                recipient_list=[guardian_email],
                default_subject=f'Workshop Registration Confirmed - {registration.session.workshop.title}',
                fail_silently=False,
                log_description=f"Registration confirmation to student {registration.student.username} for session {registration.session.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send registration confirmation to student: {str(e)}")
            return False

    @staticmethod
    def send_cart_registration_confirmation(user, registrations, total_amount):
        """Send confirmation email for multiple workshop registrations from cart"""
        try:
            # Get user email
            if not user or not user.email:
                logger.warning(f"No user email found for cart confirmation")
                return False

            # Build URLs
            my_registrations_url = StudentNotificationService.build_absolute_url(
                'workshops:my_registrations'
            )

            context = {
                'user': user,
                'user_name': user.get_full_name() or user.username,
                'registrations': registrations,
                'total_amount': total_amount,
                'registration_count': len(registrations),
                'payment_date': registrations[0].paid_at if registrations else None,
                'my_registrations_url': my_registrations_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='workshops/emails/student_cart_confirmation.txt',
                context=context,
                recipient_list=[user.email],
                default_subject=f"Workshop Registration Confirmed - {len(registrations)} Session{'s' if len(registrations) > 1 else ''}",
                fail_silently=False,
                log_description=f"Cart confirmation to student {user.username} for {len(registrations)} registrations"
            )

        except Exception as e:
            logger.error(f"Failed to send cart confirmation to student: {str(e)}")
            return False

    @staticmethod
    def send_cancellation_with_refund_notification(registration, refund_amount):
        """Send notification when registration is cancelled with refund"""
        try:
            if not registration.student or not registration.student.email:
                logger.warning(f"No student email found for registration {registration.id}")
                return False

            recipient_email = registration.email or registration.student.email

            # Build URLs
            my_registrations_url = StudentNotificationService.build_absolute_url('workshops:my_registrations')
            browse_workshops_url = StudentNotificationService.build_absolute_url('workshops:list')

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'student_name': registration.student_name,
                'refund_amount': refund_amount,
                'my_registrations_url': my_registrations_url,
                'browse_workshops_url': browse_workshops_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='workshops/emails/cancellation_with_refund.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Workshop Cancellation & Refund - {registration.session.workshop.title}',
                fail_silently=False,
                log_description=f"Cancellation with refund notification to {registration.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation with refund notification: {str(e)}")
            return False

    @staticmethod
    def send_cancellation_no_refund_notification(registration, reason='less_than_7_days'):
        """Send notification when registration is cancelled without refund"""
        try:
            if not registration.student or not registration.student.email:
                logger.warning(f"No student email found for registration {registration.id}")
                return False

            recipient_email = registration.email or registration.student.email

            # Build URLs
            my_registrations_url = StudentNotificationService.build_absolute_url('workshops:my_registrations')
            browse_workshops_url = StudentNotificationService.build_absolute_url('workshops:list')

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'student_name': registration.student_name,
                'reason': reason,
                'my_registrations_url': my_registrations_url,
                'browse_workshops_url': browse_workshops_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='workshops/emails/cancellation_no_refund.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Workshop Cancellation - {registration.session.workshop.title}',
                fail_silently=False,
                log_description=f"Cancellation without refund notification to {registration.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation without refund notification: {str(e)}")
            return False

    @staticmethod
    def send_cancellation_notification(registration):
        """Send simple cancellation notification for free/unpaid registrations"""
        try:
            if not registration.student or not registration.student.email:
                logger.warning(f"No student email found for registration {registration.id}")
                return False

            recipient_email = registration.email or registration.student.email

            # Build URLs
            my_registrations_url = StudentNotificationService.build_absolute_url('workshops:my_registrations')
            browse_workshops_url = StudentNotificationService.build_absolute_url('workshops:list')

            context = {
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'student_name': registration.student_name,
                'my_registrations_url': my_registrations_url,
                'browse_workshops_url': browse_workshops_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='workshops/emails/cancellation_notification.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Workshop Cancellation - {registration.session.workshop.title}',
                fail_silently=False,
                log_description=f"Cancellation notification to {registration.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation notification: {str(e)}")
            return False


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
        return WorkshopInterestNotificationService.build_detail_url('workshops:detail', workshop)

    @staticmethod
    def _build_browse_url():
        """Build URL for workshop list page"""
        return WorkshopInterestNotificationService.build_absolute_url('workshops:list')

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
        return WorkshopInterestNotificationService.build_absolute_url(
            'workshops:register',
            kwargs={
                'workshop_slug': session.workshop.slug,
                'session_id': session.id
            },
            use_https=False
        )