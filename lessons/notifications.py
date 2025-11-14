"""
Notification services for lesson-related emails
"""
import logging
from django.urls import reverse
from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class LessonNotificationService(BaseNotificationService):
    """Service for sending lesson-related notifications"""

    @staticmethod
    def send_lesson_assigned_notification(lesson, teacher_name):
        """Send notification to student when lesson is assigned (Draft -> Assigned)"""
        try:
            # Validate student and email
            if not lesson.student or not lesson.student.email:
                logger.warning(f"No student email found for lesson {lesson.id}")
                return False

            # Build lesson URL
            lesson_url = LessonNotificationService.build_absolute_url(
                'lessons:lesson_detail',
                args=[lesson.pk]
            )

            # Get student name
            student_name = lesson.student.get_full_name() or lesson.student.username

            context = {
                'lesson': lesson,
                'teacher_name': teacher_name,
                'student_name': student_name,
                'lesson_url': lesson_url,
            }

            return LessonNotificationService.send_templated_email(
                template_path='lessons/emails/lesson_assigned.txt',
                context=context,
                recipient_list=[lesson.student.email],
                default_subject='Your Lesson is Ready to View',
                fail_silently=True,
                log_description=f"Lesson assigned notification to {student_name} for lesson {lesson.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send lesson assigned notification: {str(e)}")
            return False
