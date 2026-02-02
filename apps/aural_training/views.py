from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.private_teaching.mixins import StudentProfileCompletedMixin


class StudentTrainingView(StudentProfileCompletedMixin, TemplateView):
    """
    Main aural training interface for students.
    Serves the adapted POC as a Django template.
    """
    template_name = 'aural_training/student_training.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Pass API base URL for JS
        context['api_base_url'] = '/aural-training/api/'

        # For child profile selection if user is a guardian
        if hasattr(self.request.user, 'profile') and self.request.user.profile.is_guardian:
            from apps.accounts.models import ChildProfile
            context['child_profiles'] = ChildProfile.objects.filter(
                guardian=self.request.user
            )

        return context


class StudentProgressView(LoginRequiredMixin, TemplateView):
    """
    Shows student's aural training progress summary.
    """
    template_name = 'aural_training/student_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import StudentIntervalProgress, AuralTrainingSession

        # Get progress data
        context['interval_progress'] = StudentIntervalProgress.objects.filter(
            student=self.request.user
        ).order_by('interval')

        # Get recent sessions
        context['recent_sessions'] = AuralTrainingSession.objects.filter(
            student=self.request.user
        ).order_by('-started_at')[:10]

        return context
