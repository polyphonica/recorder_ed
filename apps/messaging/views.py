from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q, Prefetch
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import Conversation, Message
from .notifications import MessageNotificationService
from apps.workshops.models import Workshop, WorkshopRegistration


@login_required
def inbox(request):
    """
    Unified inbox showing all conversations for the user.
    """
    user = request.user

    # Filter by domain if requested (must be done before prefetch)
    domain_filter = request.GET.get('domain')

    # Get all conversations where user is a participant
    conversations = Conversation.objects.filter(
        Q(participant_1=user) | Q(participant_2=user)
    )

    # Apply domain filter if specified
    if domain_filter:
        conversations = conversations.filter(domain=domain_filter)

    # Now add select_related (no prefetch to avoid slicing issues)
    conversations = conversations.select_related(
        'participant_1',
        'participant_2',
        'workshop',
        'child_profile'
    ).order_by('-updated_at')

    # Annotate with unread counts
    conversations_with_unread = []
    for conv in conversations:
        unread_count = conv.get_unread_count(user)
        # Get last message with a separate query (more reliable than prefetch slicing)
        last_message = Message.objects.filter(conversation=conv).order_by('-created_at').first()

        conversations_with_unread.append({
            'conversation': conv,
            'unread_count': unread_count,
            'last_message': last_message,
            'other_participant': conv.get_other_participant(user),
        })

    context = {
        'conversations': conversations_with_unread,
        'domain_filter': domain_filter,
        'total_unread': sum(c['unread_count'] for c in conversations_with_unread),
    }

    return render(request, 'messaging/inbox.html', context)


@login_required
def conversation_detail(request, conversation_id):
    """
    View a specific conversation and send messages.
    """
    user = request.user

    # Get conversation
    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Check permission - user must be a participant
    if user not in [conversation.participant_1, conversation.participant_2]:
        raise PermissionDenied("You don't have permission to view this conversation.")

    # Mark as read
    conversation.mark_as_read(user)

    # Get all messages
    messages_list = conversation.messages.select_related('sender').order_by('created_at')

    # Handle new message submission
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=content
            )
            # Send email notification to recipient
            MessageNotificationService.send_new_message_notification(message)

            django_messages.success(request, 'Message sent!')
            return redirect('messaging:conversation_detail', conversation_id=conversation.id)
        else:
            django_messages.error(request, 'Message cannot be empty.')

    context = {
        'conversation': conversation,
        'messages': messages_list,
        'other_participant': conversation.get_other_participant(user),
    }

    return render(request, 'messaging/conversation_detail.html', context)


@login_required
def start_workshop_conversation(request, workshop_id):
    """
    Start or continue a conversation about a workshop.
    Only registered participants can message the instructor.
    """
    user = request.user
    workshop = get_object_or_404(Workshop, id=workshop_id)

    # Check if user is registered for this workshop
    registration = WorkshopRegistration.objects.filter(
        session__workshop=workshop,
        student=user,
        status__in=['registered', 'promoted', 'attended']
    ).first()

    if not registration:
        django_messages.error(request, 'You must be registered for this workshop to contact the instructor.')
        return redirect('workshops:detail', slug=workshop.slug)

    # Get or create conversation with instructor
    instructor = workshop.instructor

    # Ensure consistent participant ordering
    p1, p2 = (user, instructor) if user.id < instructor.id else (instructor, user)

    conversation, created = Conversation.objects.get_or_create(
        domain='workshop',
        workshop=workshop,
        participant_1=p1,
        participant_2=p2
    )

    if created:
        django_messages.success(request, f'Started conversation with {instructor.get_full_name()}')

    return redirect('messaging:conversation_detail', conversation_id=conversation.id)
