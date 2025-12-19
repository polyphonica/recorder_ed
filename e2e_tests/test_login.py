"""
E2E tests for login functionality.

Tests authentication flows for both students and teachers.
"""
import pytest
from playwright.sync_api import Page


@pytest.mark.django_db
class TestLogin:
    """Test suite for login functionality."""

    def test_student_can_login_successfully(self, login_page, live_server):
        """Test that a student can log in with valid credentials."""
        # Act
        login_page.login('test_student', 'TestPass123!')

        # Assert
        login_page.expect_login_success()
        assert login_page.is_logged_in()

    def test_teacher_can_login_successfully(self, login_page, live_server):
        """Test that a teacher can log in with valid credentials."""
        # Act
        login_page.login('test_teacher', 'TestPass123!')

        # Assert
        login_page.expect_login_success()
        assert login_page.is_logged_in()

    def test_login_fails_with_wrong_password(self, login_page, live_server):
        """Test that login fails with incorrect password."""
        # Act
        login_page.login('test_student', 'WrongPassword123')

        # Assert - should still be on login page with error
        login_page.expect_login_error()
        assert '/login' in login_page.page.url

    def test_login_fails_with_nonexistent_user(self, login_page, live_server):
        """Test that login fails with non-existent username."""
        # Act
        login_page.login('nonexistent_user', 'TestPass123!')

        # Assert
        login_page.expect_login_error()

    def test_login_fails_with_empty_credentials(self, login_page, live_server):
        """Test that login fails when credentials are empty."""
        # Act
        login_page.login('', '')

        # Assert - form validation should prevent submission or show error
        # The page should still be on login page
        assert '/login' in login_page.page.url

    def test_student_redirected_to_dashboard_after_login(self, login_page, live_server):
        """Test that student is redirected appropriately after login."""
        # Act
        login_page.login('test_student', 'TestPass123!')

        # Assert - should be redirected away from login page
        login_page.page.wait_for_url('**/private-teaching/**', timeout=5000)
        assert '/login' not in login_page.page.url

    def test_teacher_redirected_to_dashboard_after_login(self, login_page, live_server):
        """Test that teacher is redirected appropriately after login."""
        # Act
        login_page.login('test_teacher', 'TestPass123!')

        # Assert - should be redirected away from login page
        login_page.page.wait_for_url('**/private-teaching/**', timeout=5000)
        assert '/login' not in login_page.page.url
