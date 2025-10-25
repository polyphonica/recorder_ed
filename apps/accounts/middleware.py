from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser

class ProfileCompletionMiddleware:
    """
    Middleware to ensure users complete their profile after registration
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for unauthenticated users
        if isinstance(request.user, AnonymousUser):
            return self.get_response(request)
        
        # Skip for admin/staff users
        if request.user.is_staff or request.user.is_superuser:
            return self.get_response(request)
        
        # URLs that should be accessible even without profile completion
        allowed_urls = [
            reverse('accounts:profile_setup'),
            reverse('accounts:profile_edit'),
            reverse('logout'),
            reverse('admin:index'),
        ]
        
        # Allow static files and media files
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path.startswith('/admin/') or
            request.path in allowed_urls):
            return self.get_response(request)
        
        # Check if user has completed their profile
        if hasattr(request.user, 'profile') and not request.user.profile.profile_completed:
            if request.path != reverse('accounts:profile_setup'):
                return redirect('accounts:profile_setup')
        
        return self.get_response(request)