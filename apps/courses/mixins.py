"""
Custom mixins for courses app.
"""

from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

from apps.core.mixins import InstructorRequiredMixin as BaseInstructorRequiredMixin


class InstructorRequiredMixin(BaseInstructorRequiredMixin):
    """
    Mixin to ensure user has teacher/instructor status.
    Uses the unified user.is_instructor() which checks profile.is_teacher.
    Redirects to courses list with error message on failure.
    """
    instructor_redirect_url = 'courses:list'


class CourseInstructorMixin(UserPassesTestMixin):
    """
    Mixin to ensure user is the instructor of the course they're trying to access.
    """

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        course = self.get_object()
        return course.is_owned_by(self.request.user)

    def handle_no_permission(self):
        messages.error(
            self.request,
            'You do not have permission to edit this course.'
        )
        return redirect('courses:instructor_dashboard')


class EnrollmentRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure user is enrolled in the course.
    """

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        from .models import CourseEnrollment

        # Get course slug from URL kwargs
        course_slug = self.kwargs.get('slug') or self.kwargs.get('course_slug')

        if not course_slug:
            return False

        # Check if enrollment exists
        return CourseEnrollment.objects.filter(
            course__slug=course_slug,
            student=self.request.user,
            is_active=True
        ).exists()

    def handle_no_permission(self):
        messages.warning(
            self.request,
            'You must be enrolled in this course to access this content.'
        )
        course_slug = self.kwargs.get('slug') or self.kwargs.get('course_slug')
        if course_slug:
            return redirect('courses:detail', slug=course_slug)
        return redirect('courses:list')
