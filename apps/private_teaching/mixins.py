from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class PrivateTeachingLoginRequiredMixin(LoginRequiredMixin):
    """
    Custom LoginRequiredMixin that redirects to private teaching login page
    """
    login_url = 'private_teaching:login'


class StudentProfileNotCompletedMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that allows access only to users whose profile is NOT completed.
    Used for profile completion views to prevent completed users from accessing them.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if hasattr(request.user, 'profile') and request.user.profile.profile_completed:
            messages.info(request, 'Your profile is already completed.')
            return redirect('private_teaching:home')
        
        return super().dispatch(request, *args, **kwargs)


class StudentProfileCompletedMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that requires the user's profile to be completed.
    Used for main private teaching views to enforce profile completion.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'profile'):
            messages.warning(request, 'Please complete your profile to access private teaching.')
            return redirect('private_teaching:profile_complete')
        
        if not request.user.profile.profile_completed:
            messages.warning(request, 'Please complete your profile to access private teaching.')
            return redirect('private_teaching:profile_complete')
        
        return super().dispatch(request, *args, **kwargs)


class StudentOnlyMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that allows access only to users marked as students.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'profile') or not request.user.profile.is_student:
            messages.error(request, 'This section is only available to students.')
            return redirect('private_teaching:home')
        
        return super().dispatch(request, *args, **kwargs)


class TeacherProfileNotCompletedMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that allows access only to teachers whose profile is NOT completed.
    Used for teacher profile completion views.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'profile') or not request.user.profile.is_private_teacher:
            messages.error(request, 'This section is only available to teachers.')
            return redirect('private_teaching:home')
            
        if request.user.profile.profile_completed:
            messages.info(request, 'Your teacher profile is already completed.')
            return redirect('private_teaching:teacher_dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class TeacherProfileCompletedMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that requires the teacher's profile to be completed.
    Used for main teacher views to enforce profile completion.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'profile') or not request.user.profile.is_private_teacher:
            messages.error(request, 'This section is only available to teachers.')
            return redirect('private_teaching:home')
            
        if not request.user.profile.profile_completed:
            messages.warning(request, 'Please complete your teacher profile to access teacher features.')
            return redirect('private_teaching:teacher_profile_complete')
        
        return super().dispatch(request, *args, **kwargs)


class TeacherOnlyMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that allows access only to users marked as private teachers.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'profile') or not request.user.profile.is_private_teacher:
            messages.error(request, 'This section is only available to teachers.')
            return redirect('private_teaching:home')
        
        return super().dispatch(request, *args, **kwargs)