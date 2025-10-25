from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class InstructorRequiredMixin(UserPassesTestMixin):
    """Mixin to require instructor status for accessing views"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_instructor()
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        else:
            raise PermissionDenied("You must have instructor status to access this page.")


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to require superuser status for accessing admin views"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        else:
            raise PermissionDenied("You must be a superuser to access this page.")