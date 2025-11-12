"""
Shared mixins for access control across apps
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class InstructorRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require instructor status for accessing views.

    Uses the unified user.is_instructor() method which checks profile.is_teacher.

    Subclasses can customize behavior by overriding:
    - instructor_redirect_url: URL name to redirect to on permission failure
    - raise_exception: Set to True to raise PermissionDenied instead of redirecting
    """

    # URL to redirect to if not an instructor (can be overridden by subclass)
    instructor_redirect_url = None

    # If True, raise PermissionDenied instead of redirecting (can be overridden)
    raise_exception = False

    def test_func(self):
        """Check if user is authenticated and has instructor status"""
        return self.request.user.is_authenticated and self.request.user.is_instructor()

    def handle_no_permission(self):
        """Handle permission denial - either redirect or raise exception"""
        # If not authenticated, use default behavior (redirect to login)
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()

        # If raise_exception is True, raise PermissionDenied
        if self.raise_exception:
            raise PermissionDenied("You must have instructor status to access this page.")

        # Otherwise, show message and redirect
        messages.error(
            self.request,
            'You must have instructor status to access this page.'
        )

        # Use custom redirect URL if provided, otherwise use default behavior
        if self.instructor_redirect_url:
            return redirect(self.instructor_redirect_url)

        return super().handle_no_permission()


class SuperuserRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require superuser status for accessing admin views.

    Subclasses can customize behavior by overriding:
    - superuser_redirect_url: URL name to redirect to on permission failure
    - raise_exception: Set to True to raise PermissionDenied instead of redirecting
    """

    # URL to redirect to if not a superuser (can be overridden by subclass)
    superuser_redirect_url = None

    # If True, raise PermissionDenied instead of redirecting (can be overridden)
    raise_exception = False

    def test_func(self):
        """Check if user is authenticated and is a superuser"""
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        """Handle permission denial - either redirect or raise exception"""
        # If not authenticated, use default behavior (redirect to login)
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()

        # If raise_exception is True, raise PermissionDenied
        if self.raise_exception:
            raise PermissionDenied("You must be a superuser to access this page.")

        # Otherwise, show message and redirect
        messages.error(
            self.request,
            'You must be a superuser to access this page.'
        )

        # Use custom redirect URL if provided, otherwise use default behavior
        if self.superuser_redirect_url:
            return redirect(self.superuser_redirect_url)

        return super().handle_no_permission()
