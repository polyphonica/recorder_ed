"""
Middleware to enforce profile completion and email verification after signup.

This ensures all users complete their profile and verify their email before accessing
certain parts of the platform (courses, workshops, private lessons).
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class ProfileCompletionMiddleware:
    """
    Middleware to redirect users with incomplete profiles to profile setup.

    Applies to all authenticated users except:
    - Superusers (admins)
    - Users already on the profile setup page
    - Users accessing exempt paths (logout, static files, etc.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Paths that don't require profile completion or verification
        self.exempt_paths = [
            '/accounts/login/',
            '/accounts/signup/',
            '/accounts/signup/complete/',
            '/accounts/profile/setup/',
            '/accounts/profile/edit/',
            '/accounts/logout/',
            '/accounts/verify-email/',
            '/accounts/resend-verification/',
            '/logout/',
            '/static/',
            '/media/',
            '/admin/',
        ]

        # Paths that require email verification (booking/payment actions)
        self.verification_required_paths = [
            '/workshops/enroll/',
            '/workshops/register/',
            '/courses/enroll/',
            '/private-teaching/request/',
            '/payments/',
        ]

    def __call__(self, request):
        # Skip middleware for non-authenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip middleware for superusers
        if request.user.is_superuser:
            return self.get_response(request)

        # Skip middleware for exempt paths
        path = request.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return self.get_response(request)

        # Check if user has profile and if it's completed
        try:
            profile = request.user.profile
            if not profile.profile_completed:
                # User needs to complete profile
                profile_setup_url = reverse('accounts:profile_setup')

                # Don't redirect if already on profile setup page
                if path != profile_setup_url:
                    return redirect(profile_setup_url)
        except:
            # No profile exists (shouldn't happen due to signal, but handle it)
            profile_setup_url = reverse('accounts:profile_setup')
            if path != profile_setup_url:
                return redirect(profile_setup_url)

        # Check if email verification is required for this path
        if any(path.startswith(required) for required in self.verification_required_paths):
            profile = request.user.profile
            if not profile.email_verified:
                messages.warning(
                    request,
                    'Please verify your email address before making bookings or purchases. '
                    'Check your inbox for the verification link.'
                )
                return redirect('accounts:resend_verification')

        # Profile is completed or user is on setup page - continue
        response = self.get_response(request)
        return response
