from django.urls import reverse
from django.contrib.sites.models import Site
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

            # Build URLs - use Site.objects.get_current() for proper domain
            try:
                site = Site.objects.get_current()
                domain = site.domain
            except:
                domain = "www.recorder-ed.com"

            course_url = f"https://{domain}/courses/{enrollment.course.slug}/"
            analytics_url = f"https://{domain}/courses/instructor/{enrollment.course.slug}/analytics/"

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
