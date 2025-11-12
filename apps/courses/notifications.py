import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class InstructorNotificationService(BaseNotificationService):
    """Service for sending course-related email notifications to instructors"""

    @staticmethod
    def send_new_enrollment_notification(enrollment):
        """Send notification to instructor when someone enrolls in their course"""
        try:
            # Get the instructor email
            instructor = enrollment.course.instructor
            if not instructor or not instructor.email:
                logger.warning(f"No instructor email found for course {enrollment.course.id}")
                return False

            # Build URLs using centralized URL builder
            course_url = InstructorNotificationService.build_absolute_url(
                'courses:detail',
                kwargs={'slug': enrollment.course.slug}
            )
            analytics_url = InstructorNotificationService.build_absolute_url(
                'courses:course_analytics',
                kwargs={'slug': enrollment.course.slug}
            )

            # Determine student name
            if enrollment.child_profile:
                student_name = enrollment.child_profile.full_name
                guardian_info = f"{enrollment.student.get_full_name() or enrollment.student.username} (Guardian)"
            else:
                student_name = enrollment.student.get_full_name() or enrollment.student.username
                guardian_info = None

            context = {
                'enrollment': enrollment,
                'course': enrollment.course,
                'student_name': student_name,
                'guardian_info': guardian_info,
                'course_url': course_url,
                'analytics_url': analytics_url,
            }

            return InstructorNotificationService.send_templated_email(
                template_path='courses/emails/instructor_new_enrollment.txt',
                context=context,
                recipient_list=[instructor.email],
                default_subject='New Course Enrollment',
                fail_silently=False,
                log_description=f"New enrollment notification to instructor {instructor.username} for course {enrollment.course.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send new enrollment notification to instructor: {str(e)}")
            return False
