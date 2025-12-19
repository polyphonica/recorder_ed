"""
E2E tests for the complete reschedule workflow.

Tests the end-to-end reschedule process from student request to teacher approval.
This is one of the most critical user journeys in the platform.
"""
import pytest
from datetime import datetime, timedelta
from playwright.sync_api import expect


@pytest.mark.django_db
class TestRescheduleWorkflow:
    """Test suite for the complete reschedule workflow."""

    def test_student_can_request_reschedule(
        self,
        authenticated_student_page,
        create_test_lesson,
        live_server
    ):
        """
        Test that a student can submit a reschedule request with proposed dates.

        User journey:
        1. Student has a lesson scheduled
        2. Student navigates to lesson and requests reschedule
        3. Student proposes new date/time
        4. Request is submitted successfully
        """
        # Arrange - Create a test lesson
        lesson = create_test_lesson(
            student_username='test_student',
            teacher_username='test_teacher'
        )

        # Navigate to cancellation request page
        authenticated_student_page.goto(
            f"{live_server.url}/private-teaching/lesson/{lesson.id}/cancel/"
        )

        # Act - Submit reschedule request
        from e2e_tests.pages.reschedule_page import ReschedulePage
        reschedule_page = ReschedulePage(authenticated_student_page)

        new_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        new_time = '15:00'

        reschedule_page.submit_reschedule_request(
            date=new_date,
            time=new_time,
            message="I have a conflict at the original time"
        )

        # Assert
        reschedule_page.expect_success('Reschedule request submitted')
        reschedule_page.expect_on_request_detail_page()

    def test_student_can_request_reschedule_without_message(
        self,
        authenticated_student_page,
        create_test_lesson,
        live_server
    ):
        """
        Test that student can submit reschedule without optional message.

        Verifies the privacy-focused approach where no reason is required.
        """
        # Arrange
        lesson = create_test_lesson(
            student_username='test_student',
            teacher_username='test_teacher'
        )

        authenticated_student_page.goto(
            f"{live_server.url}/private-teaching/lesson/{lesson.id}/cancel/"
        )

        # Act - Submit reschedule WITHOUT message (it's optional)
        from e2e_tests.pages.reschedule_page import ReschedulePage
        reschedule_page = ReschedulePage(authenticated_student_page)

        new_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        new_time = '16:30'

        reschedule_page.submit_reschedule_request(
            date=new_date,
            time=new_time
            # No message - testing that it's truly optional
        )

        # Assert - Should still succeed
        reschedule_page.expect_success()

    def test_teacher_sees_reschedule_request_in_list(
        self,
        authenticated_teacher_page,
        create_test_lesson,
        live_server,
        django_db_blocker
    ):
        """
        Test that teacher can see reschedule requests in their list.

        User journey:
        1. Student submits reschedule request
        2. Teacher navigates to cancellation requests
        3. Request appears with "Reschedule Lesson" button
        """
        # Arrange - Create lesson and reschedule request
        from apps.private_teaching.models import LessonCancellationRequest

        with django_db_blocker.unblock():
            lesson = create_test_lesson(
                student_username='test_student',
                teacher_username='test_teacher'
            )

            # Create reschedule request
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(username='test_student')
            teacher = User.objects.get(username='test_teacher')

            new_date = datetime.now().date() + timedelta(days=14)
            new_time = datetime.strptime('15:00', '%H:%M').time()

            LessonCancellationRequest.objects.create(
                lesson=lesson,
                student=student,
                teacher=teacher,
                request_type=LessonCancellationRequest.RESCHEDULE,
                student_message="",  # Optional - testing privacy approach
                proposed_new_date=new_date,
                proposed_new_time=new_time,
                status=LessonCancellationRequest.PENDING
            )

        # Act - Navigate to teacher's cancellation requests page
        from e2e_tests.pages.teacher_cancellation_requests_page import TeacherCancellationRequestsPage
        requests_page = TeacherCancellationRequestsPage(authenticated_teacher_page)
        requests_page.navigate()

        # Assert
        requests_page.expect_request_visible('Piano')
        requests_page.expect_reschedule_button_visible('Piano')

    def test_teacher_can_adjust_and_approve_reschedule(
        self,
        authenticated_teacher_page,
        create_test_lesson,
        live_server,
        django_db_blocker
    ):
        """
        Test complete teacher workflow: adjust proposed date and approve.

        User journey:
        1. Teacher views reschedule request
        2. Teacher adjusts the proposed date/time
        3. System checks for conflicts
        4. Teacher approves the reschedule
        5. Lesson is automatically updated
        """
        # Arrange - Create lesson and reschedule request
        from apps.private_teaching.models import LessonCancellationRequest
        from django.contrib.auth import get_user_model

        with django_db_blocker.unblock():
            lesson = create_test_lesson(
                student_username='test_student',
                teacher_username='test_teacher'
            )

            User = get_user_model()
            student = User.objects.get(username='test_student')
            teacher = User.objects.get(username='test_teacher')

            new_date = datetime.now().date() + timedelta(days=14)
            new_time = datetime.strptime('15:00', '%H:%M').time()

            request = LessonCancellationRequest.objects.create(
                lesson=lesson,
                student=student,
                teacher=teacher,
                request_type=LessonCancellationRequest.RESCHEDULE,
                proposed_new_date=new_date,
                proposed_new_time=new_time,
                status=LessonCancellationRequest.PENDING
            )

        # Act - Navigate to request detail and adjust/approve
        from e2e_tests.pages.cancellation_request_detail_page import CancellationRequestDetailPage
        detail_page = CancellationRequestDetailPage(authenticated_teacher_page)
        detail_page.navigate_to_request(request.id)

        # Verify reschedule form is visible
        detail_page.expect_reschedule_form_visible()

        # Adjust the proposed time
        adjusted_date = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
        adjusted_time = '14:00'
        detail_page.adjust_reschedule_datetime(adjusted_date, adjusted_time)

        # Verify no conflicts
        detail_page.expect_datetime_updated_successfully()

        # Approve the reschedule
        detail_page.approve_request("Looking forward to the rescheduled lesson!")

        # Assert
        detail_page.expect_approval_success(is_reschedule=True)

    def test_teacher_can_approve_reschedule_without_adjustment(
        self,
        authenticated_teacher_page,
        create_test_lesson,
        live_server,
        django_db_blocker
    ):
        """
        Test teacher approving reschedule without adjusting the proposed time.

        User journey:
        1. Teacher views reschedule request
        2. Student's proposed time works fine
        3. Teacher approves directly
        """
        # Arrange
        from apps.private_teaching.models import LessonCancellationRequest
        from django.contrib.auth import get_user_model

        with django_db_blocker.unblock():
            lesson = create_test_lesson(
                student_username='test_student',
                teacher_username='test_teacher'
            )

            User = get_user_model()
            student = User.objects.get(username='test_student')
            teacher = User.objects.get(username='test_teacher')

            new_date = datetime.now().date() + timedelta(days=14)
            new_time = datetime.strptime('15:00', '%H:%M').time()

            request = LessonCancellationRequest.objects.create(
                lesson=lesson,
                student=student,
                teacher=teacher,
                request_type=LessonCancellationRequest.RESCHEDULE,
                proposed_new_date=new_date,
                proposed_new_time=new_time,
                status=LessonCancellationRequest.PENDING
            )

        # Act - Approve without adjusting
        from e2e_tests.pages.cancellation_request_detail_page import CancellationRequestDetailPage
        detail_page = CancellationRequestDetailPage(authenticated_teacher_page)
        detail_page.navigate_to_request(request.id)

        # Approve directly
        detail_page.approve_request()

        # Assert
        detail_page.expect_approval_success(is_reschedule=True)

        # Verify lesson was updated in database
        with django_db_blocker.unblock():
            lesson.refresh_from_db()
            assert lesson.lesson_date == new_date
            assert lesson.lesson_time == new_time

    def test_conflict_detection_prevents_double_booking(
        self,
        authenticated_teacher_page,
        create_test_lesson,
        live_server,
        django_db_blocker
    ):
        """
        Test that conflict detection prevents teacher double-booking.

        User journey:
        1. Teacher has lesson at 14:00
        2. Student requests reschedule to 14:00 (conflict!)
        3. System detects conflict and shows error
        """
        # Arrange - Create TWO lessons, one at the conflict time
        from apps.private_teaching.models import LessonCancellationRequest
        from django.contrib.auth import get_user_model

        conflict_date = datetime.now().date() + timedelta(days=14)
        conflict_time = datetime.strptime('14:00', '%H:%M').time()

        with django_db_blocker.unblock():
            # Existing lesson at 14:00
            existing_lesson = create_test_lesson(
                student_username='test_student',
                teacher_username='test_teacher',
                lesson_date=conflict_date,
                lesson_time=conflict_time
            )

            # Lesson to be rescheduled (different time initially)
            lesson_to_reschedule = create_test_lesson(
                student_username='test_student',
                teacher_username='test_teacher',
                lesson_date=datetime.now().date() + timedelta(days=7),
                lesson_time=datetime.strptime('16:00', '%H:%M').time()
            )

            User = get_user_model()
            student = User.objects.get(username='test_student')
            teacher = User.objects.get(username='test_teacher')

            # Create reschedule request proposing conflict time
            request = LessonCancellationRequest.objects.create(
                lesson=lesson_to_reschedule,
                student=student,
                teacher=teacher,
                request_type=LessonCancellationRequest.RESCHEDULE,
                proposed_new_date=conflict_date,
                proposed_new_time=conflict_time,
                status=LessonCancellationRequest.PENDING
            )

        # Act - Try to approve (should detect conflict)
        from e2e_tests.pages.cancellation_request_detail_page import CancellationRequestDetailPage
        detail_page = CancellationRequestDetailPage(authenticated_teacher_page)
        detail_page.navigate_to_request(request.id)

        # Try to update to conflict time (should already be set, but let's be explicit)
        detail_page.adjust_reschedule_datetime(
            conflict_date.strftime('%Y-%m-%d'),
            '14:00'
        )

        # Assert - Should show conflict error
        detail_page.expect_scheduling_conflict()
