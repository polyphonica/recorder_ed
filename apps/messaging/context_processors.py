"""
Context processors for messaging app.
Provides global template variables for unread message counts.
"""

from django.db.models import Q, Count, OuterRef, Subquery, Exists
from .models import Conversation, Message, ConversationReadStatus


def unread_messages(request):
    """
    Add unified unread message count to all templates.
    Counts messages from both new messaging system and legacy course messages.

    Optimized to avoid N+1 queries by using aggregation.
    """
    if not request.user.is_authenticated:
        return {
            'unread_messaging_count': 0,
            'total_unread_messages': 0,
        }

    # Optimized approach using just 3 queries total instead of N queries

    # Get all conversations where user is a participant
    user_conversations = Conversation.objects.filter(
        Q(participant_1=request.user) | Q(participant_2=request.user)
    )

    # Get all conversation IDs that have been read by the user
    read_conversation_ids = ConversationReadStatus.objects.filter(
        user=request.user,
        conversation__in=user_conversations
    ).values_list('conversation_id', flat=True)

    # Count 1: Messages in never-read conversations (exclude user's own messages)
    never_read_count = Message.objects.filter(
        conversation__in=user_conversations
    ).exclude(
        conversation_id__in=read_conversation_ids
    ).exclude(
        sender=request.user
    ).count()

    # Count 2: Messages created after last_read_at in read conversations
    # Use a join to compare created_at with last_read_at efficiently
    unread_in_read_conversations = Message.objects.filter(
        conversation_id__in=read_conversation_ids,
        created_at__gt=Subquery(
            ConversationReadStatus.objects.filter(
                conversation_id=OuterRef('conversation_id'),
                user=request.user
            ).values('last_read_at')[:1]
        )
    ).exclude(
        sender=request.user
    ).count()

    messaging_unread = never_read_count + unread_in_read_conversations

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
