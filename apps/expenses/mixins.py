from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages


class TeacherOrAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that requires the user to be either:
    - A teacher (user.profile.is_teacher = True), OR
    - A staff/superuser (user.is_staff = True OR user.is_superuser = True)

    Used for expenses app views to restrict access to authorized users only.
    """

    def test_func(self):
        """Check if user is teacher, staff, or superuser"""
        user = self.request.user

        # Allow staff and superusers
        if user.is_staff or user.is_superuser:
            return True

        # Allow private teachers with completed profiles
        if hasattr(user, 'profile') and user.profile.is_teacher:
            return True

        return False

    def handle_no_permission(self):
        """Custom handling when user doesn't have permission"""
        if self.request.user.is_authenticated:
            messages.error(self.request, 'You do not have permission to access the expenses section. This area is only available to teachers and administrators.')
            return redirect('private_teaching:home')
        return super().handle_no_permission()
