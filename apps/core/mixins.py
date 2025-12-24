"""
Shared mixins for access control across apps
"""

from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
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


class ProfileCompletionMixin(LoginRequiredMixin):
    """
    Parameterized mixin for profile completion checks.

    Subclasses must define:
    - user_type: 'student' or 'teacher' (which profile type to check)
    - require_completed: True to require completed profile, False to require NOT completed
    - redirect_url: Where to redirect on failure
    - profile_attr: Optional - attribute name to check (defaults to 'is_student' or 'is_teacher')
    - completion_message: Optional - custom message for completed check
    - incomplete_message: Optional - custom message for incomplete check
    - wrong_type_message: Optional - custom message for wrong user type
    """

    # Required attributes (must be set by subclass)
    user_type = None  # 'student' or 'teacher'
    require_completed = None  # True = require completed, False = require NOT completed
    redirect_url = None  # Where to redirect on failure

    # Optional attributes (can be overridden)
    profile_attr = None  # Auto-set based on user_type if not provided
    completion_message = None
    incomplete_message = None
    wrong_type_message = None

    def dispatch(self, request, *args, **kwargs):
        """Check profile completion before allowing access"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Validate required attributes
        if self.user_type not in ['student', 'teacher']:
            raise ValueError("user_type must be 'student' or 'teacher'")
        if self.require_completed is None:
            raise ValueError("require_completed must be True or False")
        if not self.redirect_url:
            raise ValueError("redirect_url must be specified")

        # Determine profile attribute to check
        if not self.profile_attr:
            self.profile_attr = 'is_student' if self.user_type == 'student' else 'is_teacher'

        # Check if user has profile
        if not hasattr(request.user, 'profile'):
            if self.require_completed:
                msg = self.incomplete_message or f'Please complete your {self.user_type} profile.'
                messages.warning(request, msg)
                return redirect(self.redirect_url)
            # If profile doesn't exist and we require NOT completed, allow access
            return super().dispatch(request, *args, **kwargs)

        # Check user type
        # For students, also allow guardians (who manage child accounts)
        is_correct_type = getattr(request.user.profile, self.profile_attr, False)
        if self.user_type == 'student':
            is_guardian = getattr(request.user.profile, 'is_guardian', False)
            is_correct_type = is_correct_type or is_guardian

        if not is_correct_type:
            msg = self.wrong_type_message or f'This section is only available to {self.user_type}s.'
            messages.error(request, msg)
            return redirect(self.redirect_url)

        # Check completion status
        profile = request.user.profile
        is_completed = profile.profile_completed

        if self.require_completed and not is_completed:
            # User must have completed profile, but hasn't
            msg = self.incomplete_message or f'Please complete your {self.user_type} profile.'
            messages.warning(request, msg)
            return redirect(self.redirect_url)
        elif not self.require_completed and is_completed:
            # User must NOT have completed profile, but has
            msg = self.completion_message or f'Your {self.user_type} profile is already completed.'
            messages.info(request, msg)
            return redirect(self.redirect_url)

        # All checks passed
        return super().dispatch(request, *args, **kwargs)
