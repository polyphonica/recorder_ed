import logging

from apps.core.notifications import BaseNotificationService

logger = logging.getLogger(__name__)


class TeacherNotificationService(BaseNotificationService):
    """Service for sending private teaching email notifications to teachers"""

    @staticmethod
    def send_new_lesson_request_notification(lesson_request, lessons, teacher):
        """Send notification to teacher when they receive a new lesson request"""
        try:
            # Validate teacher email
            is_valid, email = TeacherNotificationService.validate_email(teacher, 'Teacher')
            if not is_valid:
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
                'initial_message': lesson_request.messages.first().message if lesson_request.messages.exists() else None,
                'incoming_requests_url': incoming_requests_url,
            }

            return TeacherNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_new_lesson_request.txt',
                context=context,
                recipient_list=[email],
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
            # Validate teacher email
            is_valid, email = TeacherNotificationService.validate_email(teacher, 'Teacher')
            if not is_valid:
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
                recipient_list=[email],
                default_subject='New Student Application',
                fail_silently=False,
                log_description=f"New application notification to teacher {teacher.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send new application notification to teacher: {str(e)}")
            return False

    @staticmethod
    def send_cancellation_request_notification(cancellation_request, lesson, student):
        """Send notification to teacher when student requests to cancel or reschedule a lesson"""
        try:
            from apps.private_teaching.models import LessonCancellationRequest

            # Validate teacher email
            is_valid, email = TeacherNotificationService.validate_email(
                cancellation_request.teacher,
                'Teacher'
            )
            if not is_valid:
                return False

            # Determine request type
            is_reschedule = cancellation_request.request_type == LessonCancellationRequest.RESCHEDULE

            # Build URL for cancellation request detail page
            request_detail_url = TeacherNotificationService.build_absolute_url(
                'private_teaching:cancellation_request_detail',
                cancellation_request.id
            )

            context = {
                'cancellation_request': cancellation_request,
                'lesson': lesson,
                'student': student,
                'student_name': TeacherNotificationService.get_display_name(student),
                'teacher': cancellation_request.teacher,
                'is_reschedule': is_reschedule,
                'is_cancellation': not is_reschedule,
                'request_detail_url': request_detail_url,
                'has_student_message': bool(cancellation_request.student_message),
            }

            # Different subject for reschedule vs cancellation
            subject = 'Lesson Reschedule Request' if is_reschedule else 'Lesson Cancellation Request'

            return TeacherNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_cancellation_request.txt',
                context=context,
                recipient_list=[email],
                default_subject=subject,
                fail_silently=False,
                log_description=f"Cancellation/reschedule request notification to teacher {cancellation_request.teacher.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation request notification to teacher: {str(e)}")
            return False


class StudentNotificationService(BaseNotificationService):
    """Service for sending private teaching email notifications to students"""

    @staticmethod
    def send_lesson_request_response_notification(lesson_request, teacher, accepted_lessons, rejected_lessons, message_text=None):
        """Send notification to student when teacher responds to their lesson request"""
        try:
            # Validate student email
            is_valid, email = StudentNotificationService.validate_email(
                lesson_request.student,
                'Student'
            )
            if not is_valid:
                return False

            # Build URL for my requests page
            my_requests_url = StudentNotificationService.build_absolute_url(
                'private_teaching:my_requests'
            )

            context = {
                'lesson_request': lesson_request,
                'student': lesson_request.student,
                'teacher': teacher,
                'teacher_name': StudentNotificationService.get_display_name(teacher),
                'accepted_lessons': accepted_lessons,
                'rejected_lessons': rejected_lessons,
                'message_text': message_text,
                'my_requests_url': my_requests_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_lesson_request_response.txt',
                context=context,
                recipient_list=[email],
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
            # Validate applicant email
            is_valid, email = StudentNotificationService.validate_email(
                application.applicant,
                'Applicant'
            )
            if not is_valid:
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
                'teacher_name': StudentNotificationService.get_display_name(teacher),
                'new_status': new_status,
                'teacher_notes': teacher_notes,
                'action_url': action_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_application_status.txt',
                context=context,
                recipient_list=[email],
                default_subject='Application Status Update',
                fail_silently=False,
                log_description=f"Application status notification to student {application.applicant.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send application status notification to student: {str(e)}")
            return False

    @staticmethod
    def send_payment_confirmation(order):
        """Send payment confirmation email to student"""
        try:
            # Validate student email
            is_valid, email = StudentNotificationService.validate_email(order.student, 'Student')
            if not is_valid:
                return False

            # Build URL for lessons page
            lessons_url = StudentNotificationService.build_absolute_url(
                'private_teaching:home'
            )

            # Get order items
            from apps.private_teaching.models import OrderItem
            order_items = OrderItem.objects.filter(order=order).select_related(
                'lesson__teacher', 'lesson__subject'
            )

            context = {
                'order': order,
                'student': order.student,
                'order_items': order_items,
                'lessons_url': lessons_url,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_payment_confirmation.txt',
                context=context,
                recipient_list=[email],
                default_subject='Payment Confirmation',
                fail_silently=False,
                log_description=f"Payment confirmation to student {order.student.username} for order {order.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send payment confirmation to student: {str(e)}")
            return False

    @staticmethod
    def send_exam_registration_notification(exam):
        """Send notification to student/parent when registered for an exam"""
        try:
            # Validate recipient email (student or guardian)
            is_valid, recipient_email = StudentNotificationService.validate_email(
                exam.student,
                'Student'
            )
            if not is_valid:
                return False

            recipient_name = StudentNotificationService.get_display_name(exam.student)

            # Build URLs
            exam_detail_url = StudentNotificationService.build_action_url(
                'private_teaching:exam_detail',
                exam,
                'pk'
            )

            context = {
                'exam': exam,
                'student_name': exam.student_name,
                'recipient_name': recipient_name,
                'teacher': exam.teacher,
                'exam_detail_url': exam_detail_url,
                'requires_payment': exam.requires_payment and not exam.is_paid,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_exam_registration.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Exam Registration: {exam.display_name}',
                fail_silently=True,
                log_description=f"Exam registration notification to {recipient_name}"
            )

        except Exception as e:
            logger.error(f"Failed to send exam registration notification: {str(e)}")
            return False

    @staticmethod
    def send_exam_results_notification(exam):
        """Send notification to student/parent when exam results are available"""
        try:
            # Validate recipient email (student or guardian)
            is_valid, recipient_email = StudentNotificationService.validate_email(
                exam.student,
                'Student'
            )
            if not is_valid:
                return False

            recipient_name = StudentNotificationService.get_display_name(exam.student)

            # Build URLs
            exam_detail_url = StudentNotificationService.build_action_url(
                'private_teaching:exam_detail',
                exam,
                'pk'
            )

            context = {
                'exam': exam,
                'student_name': exam.student_name,
                'recipient_name': recipient_name,
                'teacher': exam.teacher,
                'exam_detail_url': exam_detail_url,
                'has_results': exam.has_results,
            }

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_exam_results.txt',
                context=context,
                recipient_list=[recipient_email],
                default_subject=f'Exam Results: {exam.display_name}',
                fail_silently=True,
                log_description=f"Exam results notification to {recipient_name}"
            )

        except Exception as e:
            logger.error(f"Failed to send exam results notification: {str(e)}")
            return False

    @staticmethod
    def send_cancellation_approved_notification(cancellation_request, lesson):
        """Send notification to student when teacher approves their cancellation/reschedule request"""
        try:
            from apps.private_teaching.models import LessonCancellationRequest

            # Validate student email
            is_valid, email = StudentNotificationService.validate_email(
                cancellation_request.student,
                'Student'
            )
            if not is_valid:
                return False

            # Determine request type
            is_reschedule = cancellation_request.request_type == LessonCancellationRequest.RESCHEDULE

            # Build URL for request detail page
            request_detail_url = StudentNotificationService.build_absolute_url(
                'private_teaching:cancellation_request_detail',
                cancellation_request.id
            )

            # Build URL for my lessons page
            my_lessons_url = StudentNotificationService.build_absolute_url(
                'private_teaching:my_lessons'
            )

            context = {
                'cancellation_request': cancellation_request,
                'lesson': lesson,
                'student': cancellation_request.student,
                'teacher': cancellation_request.teacher,
                'teacher_name': StudentNotificationService.get_display_name(cancellation_request.teacher),
                'is_reschedule': is_reschedule,
                'is_cancellation': not is_reschedule,
                'request_detail_url': request_detail_url,
                'my_lessons_url': my_lessons_url,
                'has_teacher_response': bool(cancellation_request.teacher_response),
                'has_refund': cancellation_request.refund_amount and cancellation_request.refund_amount > 0,
            }

            # Different subject for reschedule vs cancellation
            subject = 'Reschedule Request Approved' if is_reschedule else 'Cancellation Request Approved'

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_cancellation_approved.txt',
                context=context,
                recipient_list=[email],
                default_subject=subject,
                fail_silently=False,
                log_description=f"Cancellation/reschedule approved notification to student {cancellation_request.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation approved notification to student: {str(e)}")
            return False

    @staticmethod
    def send_cancellation_rejected_notification(cancellation_request, lesson):
        """Send notification to student when teacher rejects their cancellation/reschedule request"""
        try:
            from apps.private_teaching.models import LessonCancellationRequest

            # Validate student email
            is_valid, email = StudentNotificationService.validate_email(
                cancellation_request.student,
                'Student'
            )
            if not is_valid:
                return False

            # Determine request type
            is_reschedule = cancellation_request.request_type == LessonCancellationRequest.RESCHEDULE

            # Build URL for request detail page
            request_detail_url = StudentNotificationService.build_absolute_url(
                'private_teaching:cancellation_request_detail',
                cancellation_request.id
            )

            # Build URL for my lessons page
            my_lessons_url = StudentNotificationService.build_absolute_url(
                'private_teaching:my_lessons'
            )

            context = {
                'cancellation_request': cancellation_request,
                'lesson': lesson,
                'student': cancellation_request.student,
                'teacher': cancellation_request.teacher,
                'teacher_name': StudentNotificationService.get_display_name(cancellation_request.teacher),
                'is_reschedule': is_reschedule,
                'is_cancellation': not is_reschedule,
                'request_detail_url': request_detail_url,
                'my_lessons_url': my_lessons_url,
                'has_teacher_response': bool(cancellation_request.teacher_response),
            }

            # Different subject for reschedule vs cancellation
            subject = 'Reschedule Request Update' if is_reschedule else 'Cancellation Request Update'

            return StudentNotificationService.send_templated_email(
                template_path='private_teaching/emails/student_cancellation_rejected.txt',
                context=context,
                recipient_list=[email],
                default_subject=subject,
                fail_silently=False,
                log_description=f"Cancellation/reschedule rejected notification to student {cancellation_request.student.username}"
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation rejected notification to student: {str(e)}")
            return False


class TeacherPaymentNotificationService(BaseNotificationService):
    """Service for sending payment notifications to teachers"""

    @staticmethod
    def send_lesson_payment_notification(order, teacher):
        """Send notification to teacher when lessons are paid for"""
        try:
            # Validate teacher email
            is_valid, email = TeacherPaymentNotificationService.validate_email(teacher, 'Teacher')
            if not is_valid:
                return False

            # Get order items for this teacher
            from apps.private_teaching.models import OrderItem
            teacher_items = OrderItem.objects.filter(
                order=order,
                lesson__teacher=teacher
            ).select_related('lesson__subject', 'lesson__student')

            if not teacher_items:
                return False

            # Build URLs
            schedule_url = TeacherPaymentNotificationService.build_absolute_url(
                'private_teaching:teacher_schedule'
            )

            context = {
                'order': order,
                'teacher': teacher,
                'teacher_items': teacher_items,
                'schedule_url': schedule_url,
            }

            return TeacherPaymentNotificationService.send_templated_email(
                template_path='private_teaching/emails/teacher_payment_notification.txt',
                context=context,
                recipient_list=[email],
                default_subject='Lesson Payment Received',
                fail_silently=False,
                log_description=f"Payment notification to teacher {teacher.username} for order {order.id}"
            )

        except Exception as e:
            logger.error(f"Failed to send payment notification to teacher: {str(e)}")
            return False
