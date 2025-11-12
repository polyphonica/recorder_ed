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
