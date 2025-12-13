"""
Template tags for private teaching app
"""
from django import template
from django.contrib.auth.models import User

register = template.Library()


@register.simple_tag
def is_accepted_private_student(user):
    """
    Check if user is an accepted private teaching student.
    Returns True if user has any accepted applications with teachers.
    """
    if not user or not user.is_authenticated:
        return False

    from apps.private_teaching.models import TeacherStudentApplication

    # Check if user has any accepted applications as applicant
    has_accepted = TeacherStudentApplication.objects.filter(
        applicant=user,
        status='accepted'
    ).exists()

    if has_accepted:
        return True

    # Check if user has any accepted applications for their child profiles
    try:
        from apps.accounts.models import ChildProfile
        child_profiles = ChildProfile.objects.filter(guardian=user)
        has_child_accepted = TeacherStudentApplication.objects.filter(
            child_profile__in=child_profiles,
            status='accepted'
        ).exists()
        return has_child_accepted
    except:
        return False


@register.simple_tag
def private_teaching_nav_url(user):
    """
    Returns the appropriate Private Teaching URL for the user:
    - Teachers: teacher_dashboard
    - Accepted students: student_dashboard
    - Others: home (landing page)
    """
    if not user or not user.is_authenticated:
        return 'private_teaching:home'

    # Check if user is a teacher by checking profile
    try:
        if hasattr(user, 'profile') and user.profile.is_teacher:
            return 'private_teaching:teacher_dashboard'
    except:
        pass

    # Check if user is accepted student
    if is_accepted_private_student(user):
        return 'private_teaching:student_dashboard'

    # Default to landing page
    return 'private_teaching:home'
