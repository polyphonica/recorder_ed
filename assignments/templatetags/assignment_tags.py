from django import template
from assignments.models import AssignmentSubmission

register = template.Library()


@register.simple_tag
def get_submission(student, assignment):
    """Get the submission for a student and assignment"""
    try:
        return AssignmentSubmission.objects.get(
            student=student,
            assignment=assignment
        )
    except AssignmentSubmission.DoesNotExist:
        return None
