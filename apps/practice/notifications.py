import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class PracticeNotificationService(BaseNotificationService):
    """Service for sending practice diary email notifications"""

    @staticmethod
    def send_practice_logged_notification(practice_entry):
        """Send notification to teacher when a student logs a practice session"""
        try:
            teacher = practice_entry.teacher
            is_valid, email = PracticeNotificationService.validate_email(teacher, 'Teacher')
            if not is_valid:
                return False

            practice_url = PracticeNotificationService.build_absolute_url(
                'practice:teacher_student_practice',
                kwargs={'student_id': practice_entry.student.id}
            )

            context = {
                'practice_entry': practice_entry,
                'teacher': teacher,
                'student': practice_entry.student,
                'student_name': PracticeNotificationService.get_display_name(practice_entry.student),
                'practice_url': practice_url,
            }

            return PracticeNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_practice_logged.txt',
                context=context,
                recipient_list=[email],
                default_subject='Student Practice Session Logged',
                fail_silently=False,
                log_description=f"Practice logged notification to teacher {teacher.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send practice logged notification to teacher: {str(e)}")
            return False

    @staticmethod
    def send_practice_comment_notification(practice_entry):
        """Send notification to student when teacher comments on a practice entry"""
        try:
            is_valid, email = PracticeNotificationService.validate_email(practice_entry.student, 'Student')
            if not is_valid:
                return False

            practice_log_url = PracticeNotificationService.build_absolute_url(
                'practice:practice_log'
            )

            context = {
                'practice_entry': practice_entry,
                'student': practice_entry.student,
                'student_name': PracticeNotificationService.get_display_name(practice_entry.student),
                'teacher': practice_entry.teacher,
                'teacher_name': PracticeNotificationService.get_display_name(practice_entry.teacher),
                'practice_log_url': practice_log_url,
            }

            return PracticeNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_practice_comment.txt',
                context=context,
                recipient_list=[email],
                default_subject='Feedback on Your Practice Entry',
                fail_silently=False,
                log_description=f"Practice comment notification to student {practice_entry.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send practice comment notification to student: {str(e)}")
            return False
