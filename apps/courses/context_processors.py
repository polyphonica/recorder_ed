"""
Context processors for courses app.
Provides global template variables.
"""

from .models import CourseMessage


def unread_messages(request):
    """
    Add unread message count to all templates.
    """
    if request.user.is_authenticated:
        unread_count = CourseMessage.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()

        return {
            'unread_course_messages': unread_count
        }

    return {
        'unread_course_messages': 0
    }
