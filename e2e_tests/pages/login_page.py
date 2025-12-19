"""
Page Object Model for the Login page.

Encapsulates all interactions with the login page.
"""
from playwright.sync_api import Page, expect


class LoginPage:
    """Page object for private teaching login page."""

    def __init__(self, page: Page):
        self.page = page

        # Locators
        self.username_input = page.locator('input[name="username"]')
        self.password_input = page.locator('input[name="password"]')
        self.login_button = page.locator('button[type="submit"]:has-text("Login")')
        self.error_message = page.locator('.alert-error, .error, .invalid-feedback')

    def login(self, username: str, password: str):
        """
        Perform login with provided credentials.

        Args:
            username: Username to log in with
            password: Password to log in with
        """
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def expect_login_success(self):
        """Assert that login was successful (redirected away from login page)."""
        # Should redirect to dashboard or home after successful login
        expect(self.page).not_to_have_url('**/login/**', timeout=5000)

    def expect_login_error(self, error_text: str = None):
        """
        Assert that login failed with an error message.

        Args:
            error_text: Optional specific error text to check for
        """
        expect(self.error_message).to_be_visible(timeout=3000)
        if error_text:
            expect(self.error_message).to_contain_text(error_text)

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in (not on login page)."""
        return '/login' not in self.page.url
