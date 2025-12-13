from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

from apps.core.mixins import ProfileCompletionMixin


class PrivateTeachingLoginRequiredMixin(LoginRequiredMixin):
    """
    Custom LoginRequiredMixin that redirects to private teaching login page
    """
    login_url = 'private_teaching:login'


class StudentProfileNotCompletedMixin(ProfileCompletionMixin):
    """
    Mixin that allows access only to users whose profile is NOT completed.
    Used for profile completion views to prevent completed users from accessing them.
    """
    login_url = 'private_teaching:login'
    user_type = 'student'
    require_completed = False
    redirect_url = 'private_teaching:home'


class StudentProfileCompletedMixin(ProfileCompletionMixin):
    """
    Mixin that requires the user's profile to be completed.
    Used for main private teaching views to enforce profile completion.
    """
    login_url = 'private_teaching:login'
    user_type = 'student'
    require_completed = True
    redirect_url = 'private_teaching:profile_complete'
    incomplete_message = 'Please complete your profile to access private teaching.'


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


class TeacherProfileNotCompletedMixin(ProfileCompletionMixin):
    """
    Mixin that allows access only to teachers whose profile is NOT completed.
    Used for teacher profile completion views.
    """
    login_url = 'private_teaching:login'
    user_type = 'teacher'
    require_completed = False
    redirect_url = 'private_teaching:teacher_dashboard'
    completion_message = 'Your teacher profile is already completed.'
    wrong_type_message = 'This section is only available to teachers.'


class TeacherProfileCompletedMixin(ProfileCompletionMixin):
    """
    Mixin that requires the teacher's profile to be completed.
    Used for main teacher views to enforce profile completion.
    """
    login_url = 'private_teaching:login'
    user_type = 'teacher'
    require_completed = True
    redirect_url = 'private_teaching:teacher_profile_complete'
    incomplete_message = 'Please complete your teacher profile to access teacher features.'
    wrong_type_message = 'This section is only available to teachers.'


class TeacherOnlyMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that allows access only to users marked as private teachers.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
            messages.error(request, 'This section is only available to teachers.')
            return redirect('private_teaching:home')

        return super().dispatch(request, *args, **kwargs)


class AcceptedStudentRequiredMixin(PrivateTeachingLoginRequiredMixin):
    """
    Mixin that requires the student to have been accepted by at least one teacher
    before they can request lessons.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Check if student has at least one accepted application
        from apps.private_teaching.models import TeacherStudentApplication

        has_accepted_application = TeacherStudentApplication.objects.filter(
            applicant=request.user,
            status='accepted'
        ).exists()

        if not has_accepted_application:
            messages.warning(
                request,
                'You must be accepted by a teacher before you can request lessons. '
                'Please apply to study with a teacher first.'
            )
            return redirect('private_teaching:home')

        return super().dispatch(request, *args, **kwargs)