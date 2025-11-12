import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class TeacherNotificationService(BaseNotificationService):
    """Service for sending private teaching email notifications to teachers"""

    @staticmethod
    def send_new_lesson_request_notification(lesson_request, lessons, teacher):
        """Send notification to teacher when they receive a new lesson request"""
        try:
            # Get teacher email
            if not teacher or not teacher.email:
                logger.warning(f"No teacher email found for teacher {teacher.id if teacher else 'None'}")
                return False

            # Build URL for incoming requests page
            incoming_requests_url = TeacherNotificationService.build_absolute_url(
                'private_teaching:incoming_requests'
            )

            # Filter lessons for this specific teacher
            teacher_lessons = [lesson for lesson in lessons if lesson.teacher == teacher]

            context = {
                'lesson_request': lesson_request,
                'teacher': teacher,
                'lessons': teacher_lessons,
                'lesson_count': len(teacher_lessons),
                'student_display_name': lesson_request.student_name,
                'initial_message': lesson_request.messages.first().text if lesson_request.messages.exists() else None,
                'incoming_requests_url': incoming_requests_url,
            }

            return TeacherNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_new_lesson_request.txt',
                context=context,
                recipient_list=[teacher.email],
                default_subject='New Lesson Request',
                fail_silently=False,
                log_description=f"New lesson request notification to teacher {teacher.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send new lesson request notification to teacher: {str(e)}")
            return False

    @staticmethod
    def send_new_application_notification(application, teacher, initial_message=None):
        """Send notification to teacher when they receive a new student application"""
        try:
            # Get teacher email
            if not teacher or not teacher.email:
                logger.warning(f"No teacher email found for teacher {teacher.id if teacher else 'None'}")
                return False

            # Build URL for applications page
            applications_url = TeacherNotificationService.build_absolute_url(
                'private_teaching:teacher_applications'
            )

            context = {
                'application': application,
                'teacher': teacher,
                'student_name': application.student_name,
                'applicant': application.applicant,
                'child_profile': application.child_profile,
                'initial_message': initial_message,
                'applications_url': applications_url,
            }

            return TeacherNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_new_application.txt',
                context=context,
                recipient_list=[teacher.email],
                default_subject='New Student Application',
                fail_silently=False,
                log_description=f"New application notification to teacher {teacher.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send new application notification to teacher: {str(e)}")
            return False


class StudentNotificationService(BaseNotificationService):
    """Service for sending private teaching email notifications to students"""

    @staticmethod
    def send_lesson_request_response_notification(lesson_request, teacher, accepted_lessons, rejected_lessons, message_text=None):
        """Send notification to student when teacher responds to their lesson request"""
        try:
            # Get student email
            if not lesson_request.student or not lesson_request.student.email:
                logger.warning(f"No student email found for lesson request {lesson_request.id}")
                return False

            # Build URL for my requests page
            my_requests_url = StudentNotificationService.build_absolute_url(
                'private_teaching:my_requests'
            )

            context = {
                'lesson_request': lesson_request,
                'student': lesson_request.student,
                'teacher': teacher,
                'teacher_name': teacher.get_full_name() or teacher.username,
                'accepted_lessons': accepted_lessons,
                'rejected_lessons': rejected_lessons,
                'message_text': message_text,
                'my_requests_url': my_requests_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_lesson_request_response.txt',
                context=context,
                recipient_list=[lesson_request.student.email],
                default_subject='Lesson Request Update',
                fail_silently=False,
                log_description=f"Lesson request response notification to student {lesson_request.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send lesson request response notification to student: {str(e)}")
            return False

    @staticmethod
    def send_application_status_notification(application, teacher, new_status, teacher_notes=None):
        """Send notification to student when their application status changes"""
        try:
            # Get applicant email
            if not application.applicant or not application.applicant.email:
                logger.warning(f"No applicant email found for application {application.id}")
                return False

            # Build URLs based on status
            if new_status == 'accepted':
                action_url = StudentNotificationService.build_absolute_url(
                    'private_teaching:request_lesson'
                )
            else:
                action_url = StudentNotificationService.build_absolute_url(
                    'private_teaching:student_applications'
                )

            context = {
                'application': application,
                'student_name': application.student_name,
                'teacher': teacher,
                'teacher_name': teacher.get_full_name() or teacher.username,
                'new_status': new_status,
                'teacher_notes': teacher_notes,
                'action_url': action_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_application_status.txt',
                context=context,
                recipient_list=[application.applicant.email],
                default_subject='Application Status Update',
                fail_silently=False,
                log_description=f"Application status notification to student {application.applicant.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send application status notification to student: {str(e)}")
            return False
