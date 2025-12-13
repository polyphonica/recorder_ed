"""
Context processors for admin portal templates.
"""

def admin_metrics(request):
    """
    Add admin metrics to template context.
    Only runs for admin portal pages.
    """
    # Only add metrics if we're in the admin portal
    if not request.path.startswith('/admin-portal/'):
        return {}

    # Only for staff users
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return {}

    from apps.support.models import Ticket
    from apps.teacher_applications.models import TeacherApplication

    # Calculate metrics
    open_tickets = Ticket.objects.filter(
        status__in=['open', 'in_progress']
    ).count()

    pending_teacher_apps = TeacherApplication.objects.filter(
        status='pending'
    ).count()

    return {
        'open_tickets': open_tickets,
        'pending_teacher_apps': pending_teacher_apps,
    }
