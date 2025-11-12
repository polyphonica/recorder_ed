import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class StudentNotificationService(BaseNotificationService):
    """Service for sending course-related email notifications to students"""

    @staticmethod
    def send_enrollment_confirmation(enrollment):
        """Send enrollment confirmation email to student"""
        try:
            # Get student email
            if not enrollment.student or not enrollment.student.email:
                logger.warning(f"No student email found for enrollment {enrollment.id}")
                return False

            guardian_email = enrollment.student.email

            # Build URLs
            course_url = StudentNotificationService.build_absolute_url(
                'courses:detail',
                kwargs={'slug': enrollment.course.slug}
            )
            my_courses_url = StudentNotificationService.build_absolute_url(
                'courses:my_courses'
            )

            # Determine student name
            if enrollment.child_profile:
                student_name = enrollment.child_profile.full_name
                is_child_enrollment = True
            else:
                student_name = enrollment.student.get_full_name() or enrollment.student.username
                is_child_enrollment = False

            context = {
                'enrollment': enrollment,
                'course': enrollment.course,
                'student_name': student_name,
                'is_child_enrollment': is_child_enrollment,
                'course_url': course_url,
                'my_courses_url': my_courses_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='courses/emails/student_enrollment_confirmation.txt',
                context=context,
                recipient_list=[guardian_email],
                default_subject=f'Course Enrollment Confirmed - {enrollment.course.title}',
                fail_silently=False,
                log_description=f"Enrollment confirmation to student {enrollment.student.username} for course {enrollment.course.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send enrollment confirmation to student: {str(e)}")
            return False


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
