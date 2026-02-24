import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class ExamNotificationService(BaseNotificationService):
    """Service for sending exam registration email notifications"""

    @staticmethod
    def send_exam_registration_notification(exam):
        """Send notification to student/parent when registered for an exam"""
        try:
            is_valid, recipient_email = ExamNotificationService.validate_email(
                exam.student, 'Student'
            )
            if not is_valid:
                return False

            recipient_name = ExamNotificationService.get_display_name(exam.student)
            exam_detail_url = ExamNotificationService.build_action_url(
                'exams:exam_detail', exam, 'pk'
            )

            context = {
                'exam': exam,
                'student_name': exam.student_name,
                'recipient_name': recipient_name,
                'teacher': exam.teacher,
                'exam_detail_url': exam_detail_url,
                'requires_payment': exam.requires_payment and not exam.is_paid,
            }

            return ExamNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_exam_registration.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Exam Registration: {exam.display_name}',
                fail_silently=False,
                log_description=f"Exam registration notification to {recipient_name}"
            )

        except Exception as e:
            logger.error(f"Failed to send exam registration notification: {str(e)}")
            return False

    @staticmethod
    def send_exam_results_notification(exam):
        """Send notification to student/parent when exam results are available"""
        try:
            is_valid, recipient_email = ExamNotificationService.validate_email(
                exam.student, 'Student'
            )
            if not is_valid:
                return False

            recipient_name = ExamNotificationService.get_display_name(exam.student)
            exam_detail_url = ExamNotificationService.build_action_url(
                'exams:exam_detail', exam, 'pk'
            )

            context = {
                'exam': exam,
                'student_name': exam.student_name,
                'recipient_name': recipient_name,
                'teacher': exam.teacher,
                'exam_detail_url': exam_detail_url,
                'has_results': exam.has_results,
            }

            return ExamNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_exam_results.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Exam Results: {exam.display_name}',
                fail_silently=False,
                log_description=f"Exam results notification to {recipient_name}"
            )

        except Exception as e:
            logger.error(f"Failed to send exam results notification: {str(e)}")
            return False
