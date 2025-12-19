"""
Page Object Model for Teacher's Cancellation Requests page.

Where teachers view and respond to cancellation/reschedule requests.
"""
from playwright.sync_api import Page, expect, Locator


class TeacherCancellationRequestsPage:
    """Page object for teacher's cancellation requests list page."""

    def __init__(self, page: Page):
        self.page = page

        # Tab filters
        self.pending_tab = page.locator('a.tab:has-text("Pending")')
        self.approved_tab = page.locator('a.tab:has-text("Approved")')
        self.rejected_tab = page.locator('a.tab:has-text("Rejected")')
        self.completed_tab = page.locator('a.tab:has-text("Completed")')

        # Request cards
        self.request_cards = page.locator('.card')

        # Success/error messages
        self.success_message = page.locator('.alert-success, .toast-success')
        self.error_message = page.locator('.alert-error, .toast-error')

    def navigate(self):
        """Navigate to the teacher cancellation requests page."""
        self.page.goto('/private-teaching/teacher/cancellation-requests/')

    def click_pending_tab(self):
        """Filter to show only pending requests."""
        self.pending_tab.click()

    def click_approved_tab(self):
        """Filter to show only approved requests."""
        self.approved_tab.click()

    def click_rejected_tab(self):
        """Filter to show only rejected requests."""
        self.rejected_tab.click()

    def get_request_card_by_subject(self, subject: str) -> Locator:
        """
        Get a specific request card by lesson subject.

        Args:
            subject: Subject name to search for

        Returns:
            Locator for the matching card
        """
        return self.page.locator(f'.card:has-text("{subject}")').first

    def click_reschedule_lesson_button(self, subject: str = None):
        """
        Click the "Reschedule Lesson" button on a request card.

        Args:
            subject: Optional subject to filter which card to click
        """
        if subject:
            card = self.get_request_card_by_subject(subject)
            card.locator('a:has-text("Reschedule Lesson")').click()
        else:
            self.page.locator('a:has-text("Reschedule Lesson")').first.click()

    def click_view_details_button(self, subject: str = None):
        """
        Click the "View Details" button on a request card.

        Args:
            subject: Optional subject to filter which card to click
        """
        if subject:
            card = self.get_request_card_by_subject(subject)
            card.locator('a:has-text("View Details")').click()
        else:
            self.page.locator('a:has-text("View Details")').first.click()

    def quick_approve_request(self, subject: str = None):
        """
        Click the quick "Approve" button on a request card (for cancellations only).

        Args:
            subject: Optional subject to filter which card to click
        """
        if subject:
            card = self.get_request_card_by_subject(subject)
            card.locator('button[name="action"][value="approve"]').click()
        else:
            self.page.locator('button[name="action"][value="approve"]').first.click()

    def quick_reject_request(self, subject: str = None):
        """
        Click the quick "Reject" button on a request card.

        Args:
            subject: Optional subject to filter which card to click
        """
        if subject:
            card = self.get_request_card_by_subject(subject)
            card.locator('button[name="action"][value="reject"]').click()
        else:
            self.page.locator('button[name="action"][value="reject"]').first.click()

    def expect_request_visible(self, subject: str):
        """
        Assert that a request for the given subject is visible.

        Args:
            subject: Subject name to check for
        """
        card = self.get_request_card_by_subject(subject)
        expect(card).to_be_visible()

    def expect_reschedule_button_visible(self, subject: str):
        """
        Assert that "Reschedule Lesson" button is visible for a request.

        Args:
            subject: Subject name to check
        """
        card = self.get_request_card_by_subject(subject)
        expect(card.locator('a:has-text("Reschedule Lesson")')).to_be_visible()

    def expect_no_requests(self):
        """Assert that there are no requests visible (empty state)."""
        expect(self.page.locator('text=No Cancellation Requests')).to_be_visible()
