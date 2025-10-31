from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
import logging

logger = logging.getLogger(__name__)


class InstructorNotificationService:
    """Service for sending course-related email notifications to instructors"""

    @staticmethod
    def get_site_name():
        """Get the current site name"""
        try:
            return Site.objects.get_current().name
        except:
            return getattr(settings, 'SITE_NAME', 'RECORDERED')

    @staticmethod
    def send_new_enrollment_notification(enrollment):
        """Send notification to instructor when someone enrolls in their course"""
        try:
            # Get the instructor email
            instructor = enrollment.course.instructor
            if not instructor or not instructor.email:
                logger.warning(f"No instructor email found for course {enrollment.course.id}")
                return False

            # Build URLs
            course_url = f"https://www.recorder-ed.com/courses/{enrollment.course.slug}/"
            analytics_url = f"https://www.recorder-ed.com/courses/instructor/{enrollment.course.slug}/analytics/"

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
                'site_name': InstructorNotificationService.get_site_name(),
            }

            # Render email content
            subject_and_message = render_to_string(
                'courses/emails/instructor_new_enrollment.txt',
                context
            )

            # Extract subject (first line)
            lines = subject_and_message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '') if lines else 'New Course Enrollment'
            message = '\n'.join(lines[1:]).strip()

            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instructor.email],
                fail_silently=False,
            )

            logger.info(f"New enrollment notification sent to instructor {instructor.username} for course {enrollment.course.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send new enrollment notification to instructor: {str(e)}")
            return False
