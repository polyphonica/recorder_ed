"""
Admin Portal views.
"""
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from .decorators import admin_required


@admin_required
def dashboard(request):
    """
    Admin portal homepage showing key platform metrics.
    """
    from apps.accounts.models import User
    from apps.support.models import Ticket
    from apps.teacher_applications.models import TeacherApplication

    # Time periods
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    # User metrics
    new_users_7d = User.objects.filter(date_joined__gte=seven_days_ago).count()
    total_users = User.objects.count()

    # Support metrics
    open_tickets = Ticket.objects.filter(
        status__in=['open', 'in_progress']
    ).count()

    # Teacher application metrics
    pending_teacher_apps = TeacherApplication.objects.filter(status='pending').count()
    recent_applications = TeacherApplication.objects.select_related('user').order_by('-created_at')[:5]

    # Recent activity - support tickets
    recent_tickets = Ticket.objects.select_related('user').order_by('-created_at')[:10]

    # Status counts for tickets
    ticket_status_counts = Ticket.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    context = {
        # User metrics
        'new_users_7d': new_users_7d,
        'total_users': total_users,

        # Support
        'open_tickets': open_tickets,
        'pending_teacher_apps': pending_teacher_apps,
        'recent_applications': recent_applications,

        # Recent activity
        'recent_tickets': recent_tickets,
        'ticket_status_counts': ticket_status_counts,
    }

    return render(request, 'admin_portal/dashboard.html', context)
