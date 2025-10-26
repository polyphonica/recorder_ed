"""
Custom mixins for courses app.
"""

from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


class InstructorRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure user has instructor/teacher status.
    Checks both is_teacher (accounts) and is_instructor (workshops) flags.
    """

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        # Check if user has teacher status in either profile
        try:
            has_teacher_status = (
                hasattr(self.request.user, 'profile') and
                self.request.user.profile.is_teacher
            )
        except:
            has_teacher_status = False

        try:
            has_instructor_status = (
                hasattr(self.request.user, 'instructor_profile') and
                self.request.user.instructor_profile.is_instructor
            )
        except:
            has_instructor_status = False

        return has_teacher_status or has_instructor_status

    def handle_no_permission(self):
        messages.error(
            self.request,
            'You must have instructor status to access this page.'
        )
        return redirect('courses:list')


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
