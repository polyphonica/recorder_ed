"""
Context processors for messaging app.
Provides global template variables for unread message counts.
"""

from django.db.models import Q
from .models import Conversation


def unread_messages(request):
    """
    Add unified unread message count to all templates.
    Counts messages from both new messaging system and legacy course messages.
    """
    if not request.user.is_authenticated:
        return {
            'unread_messaging_count': 0,
            'total_unread_messages': 0,
        }

    # Count unread messages in new messaging system
    conversations = Conversation.objects.filter(
        Q(participant_1=request.user) | Q(participant_2=request.user)
    )

    messaging_unread = 0
    for conv in conversations:
        messaging_unread += conv.get_unread_count(request.user)

    # Get course messages count (legacy system)
    from apps.courses.models import CourseMessage
    course_unread = CourseMessage.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).count()

    # Total across all messaging systems
    total_unread = messaging_unread + course_unread

    return {
        'unread_messaging_count': messaging_unread,  # New unified messaging system
        'unread_course_messages': course_unread,      # Legacy course messages
        'total_unread_messages': total_unread,        # Combined total
    }
