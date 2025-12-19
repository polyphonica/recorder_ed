"""
Page Object Model for the Reschedule/Cancellation Request page.

Handles both cancellation and reschedule requests.
"""
from playwright.sync_api import Page, expect


class ReschedulePage:
    """Page object for lesson cancellation/reschedule request page."""

    def __init__(self, page: Page):
        self.page = page

        # Request type radio buttons
        self.cancel_radio = page.locator('input[name="request_type"][value="cancel_refund"]')
        self.reschedule_radio = page.locator('input[name="request_type"][value="reschedule"]')

        # Reschedule fields (shown conditionally)
        self.proposed_date_input = page.locator('input[name="proposed_new_date"]')
        self.proposed_time_input = page.locator('input[name="proposed_new_time"]')

        # Message field (now optional)
        self.message_textarea = page.locator('textarea[name="student_message"]')

        # Submit button
        self.submit_button = page.locator('button[type="submit"]:has-text("Submit Request")')

        # Success/error messages
        self.success_message = page.locator('.alert-success, .toast-success')
        self.error_message = page.locator('.alert-error, .toast-error')

    def navigate_to_lesson_cancellation(self, lesson_id: str):
        """
        Navigate to the cancellation request page for a specific lesson.

        Args:
            lesson_id: UUID of the lesson to cancel/reschedule
        """
        self.page.goto(f'/private-teaching/lesson/{lesson_id}/cancel/')

    def select_cancellation(self):
        """Select cancellation request type."""
        self.cancel_radio.click()

    def select_reschedule(self):
        """Select reschedule request type."""
        self.reschedule_radio.click()

    def fill_proposed_date_time(self, date: str, time: str):
        """
        Fill in proposed new date and time for reschedule.

        Args:
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
        """
        self.proposed_date_input.fill(date)
        self.proposed_time_input.fill(time)

    def fill_message(self, message: str):
        """
        Fill in optional message to teacher.

        Args:
            message: Message text (optional)
        """
        if message:
            self.message_textarea.fill(message)

    def submit_request(self):
        """Click the submit button to send the request."""
        self.submit_button.click()

    def submit_reschedule_request(self, date: str, time: str, message: str = ""):
        """
        Complete workflow: select reschedule, fill details, and submit.

        Args:
            date: Proposed date in YYYY-MM-DD format
            time: Proposed time in HH:MM format
            message: Optional message to teacher
        """
        self.select_reschedule()
        self.fill_proposed_date_time(date, time)
        if message:
            self.fill_message(message)
        self.submit_request()

    def submit_cancellation_request(self, message: str = ""):
        """
        Complete workflow: select cancellation, fill message, and submit.

        Args:
            message: Optional message to teacher
        """
        self.select_cancellation()
        if message:
            self.fill_message(message)
        self.submit_request()

    def expect_success(self, message_text: str = None):
        """
        Assert that the request was submitted successfully.

        Args:
            message_text: Optional specific success message to check for
        """
        expect(self.success_message).to_be_visible(timeout=5000)
        if message_text:
            expect(self.success_message).to_contain_text(message_text)

    def expect_error(self, error_text: str = None):
        """
        Assert that there was an error submitting the request.

        Args:
            error_text: Optional specific error message to check for
        """
        expect(self.error_message).to_be_visible(timeout=3000)
        if error_text:
            expect(self.error_message).to_contain_text(error_text)

    def expect_on_request_detail_page(self):
        """Assert that we were redirected to the request detail page."""
        expect(self.page).to_have_url('**/cancellation-request/**', timeout=5000)
