"""
Views for teacher application management in the admin portal.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from apps.admin_portal.decorators import admin_required
from .models import TeacherApplication, TeacherOnboarding
from .notifications import send_approval_email


@admin_required
def application_list(request):
    """List all teacher applications with filters."""
    applications = TeacherApplication.objects.select_related('user', 'reviewed_by').all()

    # Apply filters
    status_filter = request.GET.get('status', 'needs_review')
    if status_filter == 'needs_review':
        # Show both pending and on_hold applications (those needing attention)
        applications = applications.filter(status__in=['pending', 'on_hold'])
    elif status_filter and status_filter != 'all':
        applications = applications.filter(status=status_filter)

    # Search
    search_query = request.GET.get('q')
    if search_query:
        applications = applications.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(subjects__icontains=search_query)
        )

    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    applications = applications.order_by(sort_by)

    # Get statistics
    stats = {
        'total_pending': TeacherApplication.objects.filter(status='pending').count(),
        'total_approved': TeacherApplication.objects.filter(status='approved').count(),
        'total_rejected': TeacherApplication.objects.filter(status='rejected').count(),
        'total_on_hold': TeacherApplication.objects.filter(status='on_hold').count(),
    }

    context = {
        'applications': applications,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'stats': stats,
    }

    return render(request, 'teacher_applications/application_list.html', context)


@admin_required
def application_detail(request, application_id):
    """View detailed information about a teacher application."""
    application = get_object_or_404(
        TeacherApplication.objects.select_related('user', 'reviewed_by'),
        id=application_id
    )

    context = {
        'application': application,
    }

    return render(request, 'teacher_applications/application_detail.html', context)


@admin_required
def approve_application(request, application_id):
    """Approve a teacher application and grant teacher status."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_portal:applications_detail', application_id=application_id)

    application = get_object_or_404(TeacherApplication, id=application_id)

    # Allow approving from any status
    # Approve the application
    application.approve(reviewed_by_user=request.user)

    # Create onboarding record if user has an account
    if application.user:
        TeacherOnboarding.objects.get_or_create(
            user=application.user,
            defaults={'application': application}
        )
        messages.success(
            request,
            f'Application from {application.name} has been approved! '
            f'Teacher status has been granted and onboarding created.'
        )
    else:
        # Send approval email with signup link for applicants without accounts
        email_sent = send_approval_email(request, application)
        if email_sent:
            messages.success(
                request,
                f'Application from {application.name} has been approved! '
                f'Approval email with signup instructions has been sent to {application.email}.'
            )
        else:
            messages.warning(
                request,
                f'Application from {application.name} has been approved, but there was an error sending the email. '
                f'Please contact them manually at {application.email}.'
            )

    return redirect('admin_portal:applications_list')


@admin_required
def reject_application(request, application_id):
    """Reject a teacher application with a reason."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_portal:applications_detail', application_id=application_id)

    application = get_object_or_404(TeacherApplication, id=application_id)

    # Allow rejecting from any status
    # Get rejection reason from form
    rejection_reason = request.POST.get('rejection_reason', '').strip()

    if not rejection_reason:
        messages.error(request, 'Please provide a reason for rejection.')
        return redirect('admin_portal:applications_detail', application_id=application_id)

    # Reject the application
    application.reject(reviewed_by_user=request.user, reason=rejection_reason)

    # TODO: Send rejection email to applicant

    messages.success(
        request,
        f'Application from {application.name} has been rejected. '
        f'Rejection email will be sent to {application.email}.'
    )

    return redirect('admin_portal:applications_list')


@admin_required
def update_application_notes(request, application_id):
    """Update admin notes for an application."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_portal:applications_detail', application_id=application_id)

    application = get_object_or_404(TeacherApplication, id=application_id)

    admin_notes = request.POST.get('admin_notes', '').strip()
    application.admin_notes = admin_notes
    application.save(update_fields=['admin_notes', 'updated_at'])

    messages.success(request, 'Admin notes updated successfully.')

    return redirect('admin_portal:applications_detail', application_id=application_id)


@admin_required
def set_application_on_hold(request, application_id):
    """Set an application status to on hold."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_portal:applications_detail', application_id=application_id)

    application = get_object_or_404(TeacherApplication, id=application_id)

    if application.status != 'pending':
        messages.warning(request, f'Application has already been {application.get_status_display().lower()}.')
        return redirect('admin_portal:applications_detail', application_id=application_id)

    application.status = 'on_hold'
    application.save(update_fields=['status', 'updated_at'])

    messages.success(request, f'Application from {application.name} has been placed on hold.')

    return redirect('admin_portal:applications_detail', application_id=application_id)


