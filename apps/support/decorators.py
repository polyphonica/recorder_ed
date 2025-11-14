from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def staff_required(view_func):
    """
    Decorator to require user to be staff member.
    Staff members can view and manage all support tickets.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You must be a staff member to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper
