"""
Access control decorators for admin portal.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator to require user to be staff or superuser.
    Redirects to login if unauthenticated, shows error if unauthorized.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'You do not have permission to access the admin portal.')
            return redirect('domain_selector')

        return view_func(request, *args, **kwargs)

    return wrapper
