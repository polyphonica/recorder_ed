"""
Page Object Model for Cancellation Request Detail page.

Where teachers can review and respond to individual cancellation/reschedule requests.
Includes inline reschedule functionality.
"""
from playwright.sync_api import Page, expect


class CancellationRequestDetailPage:
    """Page object for cancellation request detail page (teacher view)."""

    def __init__(self, page: Page):
        self.page = page

        # Inline reschedule form elements
        self.reschedule_date_input = page.locator('input[name="lesson_date"]')
        self.reschedule_time_input = page.locator('input[name="lesson_time"]')
        self.update_datetime_button = page.locator('button:has-text("Update Date/Time")')

        # Teacher response form
        self.teacher_response_textarea = page.locator('textarea[name="teacher_response"]')
        self.approve_button = page.locator('button[name="action"][value="approve"]')
        self.reject_button = page.locator('button[name="action"][value="reject"]')

        # Info sections
        self.student_note_section = page.locator('text=Student\'s Note')
        self.proposed_datetime_section = page.locator('text=Proposed New Date & Time')

        # Messages
        self.success_message = page.locator('.alert-success, .toast-success')
        self.error_message = page.locator('.alert-error, .toast-error')
        self.conflict_message = page.locator('text=Scheduling conflict')

    def navigate_to_request(self, request_id: int):
        """
        Navigate to a specific cancellation request detail page.

        Args:
            request_id: ID of the cancellation request
        """
        self.page.goto(f'/private-teaching/cancellation-request/{request_id}/')

    def adjust_reschedule_datetime(self, date: str, time: str):
        """
        Adjust the proposed reschedule date/time using inline form.

        Args:
            date: New date in YYYY-MM-DD format
            time: New time in HH:MM format
        """
        self.reschedule_date_input.fill(date)
        self.reschedule_time_input.fill(time)
        self.update_datetime_button.click()

    def fill_teacher_response(self, response: str):
        """
        Fill in optional teacher response message.

        Args:
            response: Response message to student
        """
        self.teacher_response_textarea.fill(response)

    def approve_request(self, response_message: str = ""):
        """
        Approve the cancellation/reschedule request.

        Args:
            response_message: Optional message to include with approval
        """
        if response_message:
            self.fill_teacher_response(response_message)
        self.approve_button.click()

    def reject_request(self, response_message: str = ""):
        """
        Reject the cancellation/reschedule request.

        Args:
            response_message: Optional message explaining rejection
        """
        if response_message:
            self.fill_teacher_response(response_message)
        self.reject_button.click()

    def expect_reschedule_form_visible(self):
        """Assert that the inline reschedule form is visible."""
        expect(self.page.locator('text=Adjust Reschedule Date/Time')).to_be_visible()

    def expect_reschedule_form_not_visible(self):
        """Assert that the inline reschedule form is NOT visible (cancellation request)."""
        expect(self.page.locator('text=Adjust Reschedule Date/Time')).not_to_be_visible()

    def expect_datetime_updated_successfully(self):
        """Assert that date/time was updated without conflicts."""
        expect(self.success_message).to_be_visible(timeout=5000)
        expect(self.conflict_message).not_to_be_visible()

    def expect_scheduling_conflict(self):
        """Assert that a scheduling conflict was detected."""
        expect(self.error_message).to_be_visible(timeout=3000)
        expect(self.conflict_message).to_be_visible()

    def expect_approval_success(self, is_reschedule: bool = True):
        """
        Assert that approval was successful.

        Args:
            is_reschedule: Whether this was a reschedule (vs cancellation)
        """
        expect(self.success_message).to_be_visible(timeout=5000)
        if is_reschedule:
            expect(self.success_message).to_contain_text('rescheduled')

    def expect_rejection_success(self):
        """Assert that rejection was successful."""
        # Usually redirects back to list page
        expect(self.page).to_have_url('**/teacher/cancellation-requests/**', timeout=5000)

    def get_proposed_datetime(self) -> str:
        """
        Get the currently proposed date/time text.

        Returns:
            The proposed date/time text shown on the page
        """
        return self.proposed_datetime_section.locator('..').text_content()

    def has_student_note(self) -> bool:
        """
        Check if student provided an optional note.

        Returns:
            True if student note section is visible
        """
        return self.student_note_section.is_visible()
