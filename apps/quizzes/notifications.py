import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class QuizTeacherNotificationService(BaseNotificationService):
    """Service for sending quiz-related email notifications to teachers"""

    @staticmethod
    def send_quiz_submission_notification(attempt):
        """Send notification to teacher when a student submits a quiz"""
        try:
            teacher = attempt.assignment.teacher
            is_valid, email = QuizTeacherNotificationService.validate_email(teacher, 'Teacher')
            if not is_valid:
                return False

            results_url = QuizTeacherNotificationService.build_absolute_url(
                'quizzes:teacher_quiz_attempt_results',
                kwargs={'pk': attempt.pk}
            )

            context = {
                'attempt': attempt,
                'assignment': attempt.assignment,
                'quiz': attempt.assignment.quiz,
                'teacher': teacher,
                'student': attempt.assignment.student,
                'student_name': QuizTeacherNotificationService.get_display_name(attempt.assignment.student),
                'results_url': results_url,
            }

            return QuizTeacherNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_quiz_submission.txt',
                context=context,
                recipient_list=[email],
                default_subject='Student Quiz Submitted',
                fail_silently=False,
                log_description=f"Quiz submission notification to teacher {teacher.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send quiz submission notification to teacher: {str(e)}")
            return False


class QuizStudentNotificationService(BaseNotificationService):
    """Service for sending quiz-related email notifications to students"""

    @staticmethod
    def send_quiz_assignment_notification(assignment):
        """Send notification to student when teacher assigns a quiz"""
        try:
            is_valid, email = QuizStudentNotificationService.validate_email(assignment.student, 'Student')
            if not is_valid:
                return False

            quiz_url = QuizStudentNotificationService.build_absolute_url(
                'quizzes:quiz_take',
                kwargs={'assignment_id': assignment.pk}
            )

            context = {
                'assignment': assignment,
                'quiz': assignment.quiz,
                'student': assignment.student,
                'student_name': QuizStudentNotificationService.get_display_name(assignment.student),
                'teacher': assignment.teacher,
                'teacher_name': QuizStudentNotificationService.get_display_name(assignment.teacher),
                'quiz_url': quiz_url,
            }

            return QuizStudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_quiz_assigned.txt',
                context=context,
                recipient_list=[email],
                default_subject='New Quiz Assigned',
                fail_silently=False,
                log_description=f"Quiz assignment notification to student {assignment.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send quiz assignment notification to student: {str(e)}")
            return False
