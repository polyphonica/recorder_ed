from django.views.generic import TemplateView

from apps.private_teaching.mixins import TeacherProfileCompletedMixin


class TeacherAvailabilityEditorView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher availability calendar editor"""
    template_name = 'scheduling/teacher_availability_editor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # All data will be loaded via API, but we pass the user ID for API calls
        context['teacher_id'] = self.request.user.id
        return context
