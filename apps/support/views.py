from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Ticket, TicketMessage, TicketAttachment
from .forms import (
    PublicTicketForm, AuthenticatedTicketForm, TicketReplyForm,
    StaffReplyForm, TicketUpdateForm, TicketAttachmentForm
)
from .decorators import staff_required
from .notifications import TicketNotificationService


def public_contact(request):
    """Public contact form for anonymous users"""
    if request.method == 'POST':
        form = PublicTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            # Link to user if authenticated
            if request.user.is_authenticated:
                ticket.user = request.user
            ticket.save()

            # Send notifications
            TicketNotificationService.send_ticket_created_notification(ticket)
            TicketNotificationService.send_new_ticket_alert_to_staff(ticket)

            django_messages.success(
                request,
                f'Your ticket {ticket.ticket_number} has been created. We will respond to {ticket.email} shortly.'
            )
            return redirect('support:ticket_detail', ticket_number=ticket.ticket_number)
    else:
        # Pre-fill if user is authenticated
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
        form = PublicTicketForm(initial=initial_data)

    return render(request, 'support/public_contact.html', {'form': form})


@login_required
def create_ticket(request):
    """Authenticated users can create tickets"""
    if request.method == 'POST':
        form = AuthenticatedTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()

            # Send notifications
            TicketNotificationService.send_ticket_created_notification(ticket)
            TicketNotificationService.send_new_ticket_alert_to_staff(ticket)

            django_messages.success(
                request,
                f'Your ticket {ticket.ticket_number} has been created.'
            )
            return redirect('support:ticket_detail', ticket_number=ticket.ticket_number)
    else:
        form = AuthenticatedTicketForm()

    return render(request, 'support/create_ticket.html', {'form': form})


@login_required
def my_tickets(request):
    """List of user's own tickets"""
    tickets = Ticket.objects.filter(
        Q(user=request.user) | Q(email=request.user.email)
    ).select_related('assigned_to').order_by('-created_at')

    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    category_filter = request.GET.get('category')
    if category_filter:
        tickets = tickets.filter(category=category_filter)

    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'category_filter': category_filter,
    }
    return render(request, 'support/my_tickets.html', context)


def ticket_detail(request, ticket_number):
    """View ticket details and conversation thread"""
    ticket = get_object_or_404(Ticket, ticket_number=ticket_number)

    # Permission check: owner or staff
    if not request.user.is_staff:
        # Must be the ticket owner
        if request.user.is_authenticated:
            if ticket.user != request.user and ticket.email != request.user.email:
                django_messages.error(request, 'You do not have permission to view this ticket.')
                return redirect('support:my_tickets')
        else:
            # Anonymous users need to match email (in real app, you'd verify via email link)
            django_messages.error(request, 'Please log in to view your tickets.')
            return redirect('support:public_contact')

    # Get messages (exclude internal notes for non-staff)
    if request.user.is_staff:
        messages_list = ticket.messages.select_related('author').all()
    else:
        messages_list = ticket.messages.filter(is_internal_note=False).select_related('author').all()

    # Handle reply submission
    if request.method == 'POST':
        if request.user.is_staff:
            form = StaffReplyForm(request.POST)
        else:
            form = TicketReplyForm(request.POST)

        if form.is_valid():
            message = form.save(commit=False)
            message.ticket = ticket
            message.author = request.user if request.user.is_authenticated else None

            if request.user.is_staff:
                message.is_staff_reply = True
                message.is_internal_note = form.cleaned_data.get('is_internal_note', False)
            else:
                message.is_staff_reply = False
                # Auto-set status to 'in_progress' if user replies
                if ticket.status == 'waiting_user':
                    ticket.status = 'open'
                    ticket.save()

            message.save()

            # Send notification if staff replied (and not internal note)
            if request.user.is_staff:
                TicketNotificationService.send_staff_reply_notification(ticket, message)

            django_messages.success(request, 'Reply added successfully.')
            return redirect('support:ticket_detail', ticket_number=ticket.ticket_number)
    else:
        if request.user.is_staff:
            form = StaffReplyForm()
        else:
            form = TicketReplyForm()

    context = {
        'ticket': ticket,
        'messages': messages_list,
        'form': form,
        'staff_members': User.objects.filter(is_staff=True),
    }
    return render(request, 'support/ticket_detail.html', context)


@staff_required
def staff_dashboard(request):
    """Staff dashboard with all tickets and filters"""
    tickets = Ticket.objects.select_related('user', 'assigned_to').all()

    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    else:
        # Default: show non-closed tickets
        tickets = tickets.exclude(status='closed')

    category_filter = request.GET.get('category')
    if category_filter:
        tickets = tickets.filter(category=category_filter)

    priority_filter = request.GET.get('priority')
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)

    assigned_filter = request.GET.get('assigned')
    if assigned_filter == 'me':
        tickets = tickets.filter(assigned_to=request.user)
    elif assigned_filter == 'unassigned':
        tickets = tickets.filter(assigned_to__isnull=True)

    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    tickets = tickets.order_by(sort_by)

    # Calculate stats
    total_open = Ticket.objects.filter(status='open').count()
    total_in_progress = Ticket.objects.filter(status='in_progress').count()

    # Calculate overdue tickets more efficiently
    try:
        active_tickets = Ticket.objects.exclude(status__in=['resolved', 'closed'])
        total_overdue = sum(1 for t in active_tickets if t.is_overdue)
    except Exception as e:
        # Fallback if there's an issue with is_overdue calculation
        total_overdue = 0

    my_assigned = Ticket.objects.filter(assigned_to=request.user).exclude(status__in=['resolved', 'closed']).count()

    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'priority_filter': priority_filter,
        'assigned_filter': assigned_filter,
        'sort_by': sort_by,
        'stats': {
            'total_open': total_open,
            'total_in_progress': total_in_progress,
            'total_overdue': total_overdue,
            'my_assigned': my_assigned,
        },
        'staff_members': User.objects.filter(is_staff=True),
    }
    return render(request, 'support/staff_dashboard.html', context)


@staff_required
def update_ticket(request, ticket_number):
    """Staff can update ticket status, priority, assignment via AJAX"""
    ticket = get_object_or_404(Ticket, ticket_number=ticket_number)

    if request.method == 'POST':
        old_status = ticket.status

        # Update status
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = new_status
            if new_status == 'resolved':
                ticket.resolved_at = timezone.now()
            elif new_status == 'closed':
                ticket.closed_at = timezone.now()

        # Update priority
        new_priority = request.POST.get('priority')
        if new_priority and new_priority in dict(Ticket.PRIORITY_CHOICES):
            ticket.priority = new_priority

        # Update assignment
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            if assigned_to_id == 'unassign':
                ticket.assigned_to = None
            else:
                try:
                    staff_member = User.objects.get(id=assigned_to_id, is_staff=True)
                    ticket.assigned_to = staff_member
                except User.DoesNotExist:
                    pass

        ticket.save()

        # Send notification if status changed
        if new_status and new_status != old_status:
            TicketNotificationService.send_status_changed_notification(ticket, old_status, new_status)

        django_messages.success(request, f'Ticket {ticket.ticket_number} updated successfully.')

    return redirect('support:ticket_detail', ticket_number=ticket.ticket_number)
