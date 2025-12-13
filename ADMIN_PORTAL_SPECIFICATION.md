# Unified Admin Portal - Technical Specification

**Project:** Recorder-ed Educational Platform
**Document Version:** 1.0
**Date:** January 2025
**Status:** Specification - Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Solution](#proposed-solution)
4. [Architecture Overview](#architecture-overview)
5. [Teacher Application System](#teacher-application-system)
6. [Teacher Onboarding System](#teacher-onboarding-system)
7. [Admin Portal Modules](#admin-portal-modules)
8. [Database Schema](#database-schema)
9. [Implementation Phases](#implementation-phases)
10. [Technical Requirements](#technical-requirements)
11. [File Structure](#file-structure)
12. [API Endpoints](#api-endpoints)
13. [Security Considerations](#security-considerations)
14. [Testing Strategy](#testing-strategy)
15. [Deployment Plan](#deployment-plan)
16. [Success Metrics](#success-metrics)

---

## Executive Summary

### Problem Statement

Currently, the Recorder-ed platform has fragmented admin interfaces:
- Django admin (`/admin/`) for database management
- Support staff dashboard (`/support/staff/`) for ticket management only
- No dedicated interface for teacher application review
- Manual, multi-step process to convert student accounts to teacher accounts
- No unified admin experience for platform operations

### Proposed Solution

**Hybrid Unified Admin Portal** - A custom-built admin interface that consolidates all operational tasks while preserving Django admin for technical operations.

### Key Benefits

- **Operational Efficiency:** One-click teacher application approval (vs. current 5-step manual process)
- **Unified Experience:** Single portal for all admin tasks
- **Better UX:** Purpose-built interfaces for non-technical staff
- **Scalability:** Easy to add new admin features
- **Zero Disruption:** Public student/teacher pages completely unchanged

### Approach

**Option B: Enhanced System with Dedicated TeacherApplication Model**

- Create unified admin portal at `/admin-portal/`
- Build dedicated teacher application review system
- Implement automated teacher onboarding flow
- Preserve Django admin for superuser/technical operations
- Maintain 100% backwards compatibility with public site

---

## Current State Analysis

### Existing Admin Interfaces

#### 1. Django Admin (`/admin/`)
- **Purpose:** Database-level management
- **Users:** Superusers only
- **Pros:** Powerful, built-in
- **Cons:** Not user-friendly for non-technical staff, no custom workflows

#### 2. Support Staff Dashboard (`/support/staff/`)
- **Purpose:** Support ticket management
- **Users:** Staff members (`is_staff=True`)
- **Pros:** Custom-built for support workflow
- **Cons:** Limited to tickets only, isolated from other admin tasks

#### 3. No Dedicated Application Review
- **Current Process:** Teacher applications stored as generic support tickets
- **Review Workflow:** Manual, 5-step process:
  1. View application in support dashboard
  2. Navigate to Django admin
  3. Find user's UserProfile
  4. Manually check `is_teacher` checkbox
  5. Manually notify applicant

### Current Teacher Application Flow

```
User → /support/apply-to-teach/
  ↓
Fill TeacherApplicationForm
  ↓
Creates Support Ticket (category='teacher_application')
  ↓
Email to admin/superuser
  ↓
Admin reviews in /support/staff/
  ↓
Admin navigates to /admin/accounts/userprofile/
  ↓
Admin manually checks is_teacher checkbox
  ↓
Admin manually emails applicant (often forgotten)
  ↓
User becomes teacher (no onboarding)
```

### Pain Points

1. **Disconnected Workflow:** Admin must switch between multiple interfaces
2. **Manual Data Entry:** Application data in ticket description, not structured
3. **No State Tracking:** Can't distinguish pending vs reviewed applications
4. **Missed Notifications:** Applicants not notified when approved/rejected
5. **No Onboarding:** Teachers thrown into dashboard with no guidance
6. **Poor Analytics:** Can't track approval rates, time-to-review, etc.

---

## Proposed Solution

### Architecture: Hybrid Admin Portal

```
┌─────────────────────────────────────────────────────────────────┐
│                        PUBLIC SITE                               │
│                     (Unchanged - 100%)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Students                    Teachers                           │
│  ├─ /courses/               ├─ /teacher/courses/                │
│  ├─ /workshops/             ├─ /teacher/workshops/              │
│  ├─ /private-teaching/      ├─ /teacher/students/               │
│  ├─ /my-courses/            └─ /teacher/dashboard/              │
│  └─ /my-workshops/                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN PORTAL (NEW)                            │
│                   /admin-portal/                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Staff/Admin Dashboard                                          │
│  ├─ /admin-portal/              (Dashboard homepage)            │
│  ├─ /admin-portal/support/      (Support tickets)               │
│  ├─ /admin-portal/applications/ (Teacher applications) ⭐ NEW   │
│  ├─ /admin-portal/users/        (User management)               │
│  ├─ /admin-portal/content/      (Content moderation)            │
│  ├─ /admin-portal/payments/     (Financial oversight)           │
│  ├─ /admin-portal/analytics/    (Platform analytics)            │
│  └─ /admin-portal/settings/     (Platform settings)             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  DJANGO ADMIN (Preserved)                        │
│                  /django-admin/                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Superuser Only                                                 │
│  ├─ Database management                                         │
│  ├─ Technical configuration                                     │
│  └─ Developer tools                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**
   - Public site: Student/teacher learning experience
   - Admin portal: Operational tasks and management
   - Django admin: Technical database operations

2. **Role-Based Access**
   - Students: Public site only
   - Teachers: Public site + teacher dashboard
   - Staff: Admin portal + public site (for context)
   - Superusers: Everything

3. **Zero Breaking Changes**
   - All existing URLs preserved
   - Public functionality unchanged
   - Backwards compatible redirects

4. **User-Friendly Workflows**
   - Task-oriented interfaces (not CRUD)
   - One-click common actions
   - Context-aware navigation
   - Clear status indicators

---

## Teacher Application System

### Overview

Replace the current support ticket-based application system with a dedicated, structured teacher application workflow.

### New Teacher Application Model

```python
# apps/teaching/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
import uuid

User = get_user_model()

class TeacherApplication(models.Model):
    """
    Structured teacher application separate from support tickets.
    Tracks application lifecycle from submission to approval/rejection.
    """

    # Status workflow
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('more_info_needed', 'More Information Needed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # DBS Check status
    DBS_CHOICES = [
        ('current', 'Yes - Current DBS Check'),
        ('in_progress', 'In Progress'),
        ('equivalent', 'Equivalent Background Check'),
        ('none', 'No'),
    ]

    # Teaching format preferences
    FORMAT_CHOICES = [
        ('online', 'Online (via Zoom)'),
        ('in_person', 'In-Person (at studio)'),
    ]

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Application number (user-friendly)
    application_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated application reference (e.g., APP-2025-001)"
    )

    # Applicant
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_applications',
        help_text="User who submitted the application"
    )

    # Application status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Contact information (may differ from user account)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    # Teaching background
    teaching_experience = models.TextField(
        help_text="Teaching biography and experience"
    )
    qualifications = models.TextField(
        help_text="Relevant qualifications, degrees, certifications"
    )
    subjects = models.CharField(
        max_length=500,
        help_text="Subjects/instruments you teach"
    )

    # Safeguarding
    dbs_check_status = models.CharField(
        max_length=20,
        choices=DBS_CHOICES,
        verbose_name="DBS/Background Check Status"
    )

    # Teaching preferences
    preferred_formats = models.JSONField(
        default=list,
        help_text="List of preferred teaching formats (online/in-person)"
    )
    availability = models.TextField(
        help_text="General availability description"
    )

    # Terms agreement
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # Review information
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications',
        help_text="Staff member who reviewed the application"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes for admin review (not visible to applicant)"
    )

    # Approval/Rejection
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (sent to applicant)"
    )

    # Additional info request
    info_requested = models.TextField(
        blank=True,
        help_text="Additional information requested from applicant"
    )
    info_requested_at = models.DateTimeField(null=True, blank=True)
    info_provided = models.TextField(
        blank=True,
        help_text="Applicant's response to info request"
    )
    info_provided_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['user', '-submitted_at']),
            models.Index(fields=['-submitted_at']),
        ]
        verbose_name = "Teacher Application"
        verbose_name_plural = "Teacher Applications"

    def __str__(self):
        return f"{self.application_number} - {self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Auto-generate application number
        if not self.application_number:
            year = timezone.now().year
            # Get count of applications this year
            count = TeacherApplication.objects.filter(
                application_number__startswith=f'APP-{year}-'
            ).count() + 1
            self.application_number = f'APP-{year}-{count:04d}'

        # Set timestamps based on status changes
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()
        elif self.status == 'rejected' and not self.rejected_at:
            self.rejected_at = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('admin_portal:application_detail', kwargs={'pk': self.pk})

    @property
    def days_pending(self):
        """Number of days since submission"""
        if self.status in ['approved', 'rejected']:
            return None
        return (timezone.now() - self.submitted_at).days

    @property
    def is_overdue(self):
        """Check if application review is overdue (>5 business days)"""
        if self.status not in ['pending', 'under_review']:
            return False
        return self.days_pending and self.days_pending > 5

    def approve(self, reviewed_by):
        """
        Approve application and convert user to teacher.
        Returns: tuple (success: bool, message: str)
        """
        if self.status == 'approved':
            return False, "Application already approved"

        # Update application
        self.status = 'approved'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.approved_at = timezone.now()
        self.save()

        # Convert user to teacher
        profile = self.user.profile
        profile.is_teacher = True

        # Copy application data to profile
        profile.bio = self.teaching_experience
        profile.qualifications = self.qualifications
        profile.dbs_check_status = self.dbs_check_status
        profile.instruments_taught = self.subjects

        # Set phone if provided and not already set
        if self.phone and not profile.phone:
            profile.phone = self.phone

        profile.save()

        # Send approval notification
        from .notifications import send_application_approved_email
        send_application_approved_email(self)

        return True, f"Application approved. {self.user.get_full_name()} is now a teacher."

    def reject(self, reviewed_by, reason):
        """
        Reject application with reason.
        Returns: tuple (success: bool, message: str)
        """
        if self.status == 'rejected':
            return False, "Application already rejected"

        # Update application
        self.status = 'rejected'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()

        # Send rejection notification
        from .notifications import send_application_rejected_email
        send_application_rejected_email(self)

        return True, f"Application rejected. Notification sent to {self.user.email}"

    def request_info(self, reviewed_by, info_request):
        """
        Request additional information from applicant.
        Returns: tuple (success: bool, message: str)
        """
        self.status = 'more_info_needed'
        self.reviewed_by = reviewed_by
        self.info_requested = info_request
        self.info_requested_at = timezone.now()
        self.save()

        # Send info request email
        from .notifications import send_info_request_email
        send_info_request_email(self)

        return True, f"Information request sent to {self.user.email}"


class TeacherApplicationAttachment(models.Model):
    """
    File attachments for teacher applications (CV, certificates, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        TeacherApplication,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='teacher_applications/%Y/%m/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.filename} - {self.application.application_number}"
```

### Application Form (Modified)

Update the existing `/support/apply-to-teach/` form to save to TeacherApplication model instead of Ticket.

```python
# apps/teaching/forms.py

from django import forms
from .models import TeacherApplication

class TeacherApplicationForm(forms.ModelForm):
    """
    Teacher application form - replaces current support ticket form
    """

    # Terms agreement checkbox
    terms_agreement = forms.BooleanField(
        required=True,
        label="I understand and agree to the platform requirements",
        help_text="Please read the terms before submitting"
    )

    class Meta:
        model = TeacherApplication
        fields = [
            'name',
            'email',
            'phone',
            'teaching_experience',
            'qualifications',
            'subjects',
            'dbs_check_status',
            'preferred_formats',
            'availability',
        ]
        widgets = {
            'teaching_experience': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Tell us about your teaching experience...'
            }),
            'qualifications': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'List your relevant qualifications...'
            }),
            'subjects': forms.TextInput(attrs={
                'placeholder': 'e.g., Recorder (Beginner to Grade 8), Music Theory'
            }),
            'availability': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g., Weekday evenings, Saturday mornings'
            }),
            'preferred_formats': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill from user profile if logged in
        if self.user and self.user.is_authenticated:
            self.fields['name'].initial = self.user.get_full_name()
            self.fields['email'].initial = self.user.email
            if hasattr(self.user, 'profile'):
                self.fields['phone'].initial = self.user.profile.phone

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Check if user already has pending/approved application
        if self.user and self.user.is_authenticated:
            existing = TeacherApplication.objects.filter(
                user=self.user,
                status__in=['pending', 'under_review', 'approved']
            ).first()

            if existing:
                if existing.status == 'approved':
                    raise forms.ValidationError(
                        "You already have an approved teacher application."
                    )
                else:
                    raise forms.ValidationError(
                        f"You already have a pending application ({existing.application_number}). "
                        f"Please wait for review before submitting a new one."
                    )

        return email

    def save(self, commit=True):
        application = super().save(commit=False)

        # Set user if logged in
        if self.user and self.user.is_authenticated:
            application.user = self.user

        # Set terms accepted
        application.terms_accepted = self.cleaned_data.get('terms_agreement', False)
        if application.terms_accepted:
            from django.utils import timezone
            application.terms_accepted_at = timezone.now()

        if commit:
            application.save()

            # Send confirmation email to applicant
            from .notifications import send_application_received_email
            send_application_received_email(application)

            # Notify admins of new application
            from .notifications import send_new_application_alert
            send_new_application_alert(application)

        return application
```

### Application Submission View

```python
# apps/teaching/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import TeacherApplicationForm

@login_required
def apply_to_teach(request):
    """
    Teacher application form submission.
    Replaces /support/apply-to-teach/
    """

    # Check if user already is a teacher
    if hasattr(request.user, 'profile') and request.user.profile.is_teacher:
        messages.info(request, "You're already registered as a teacher!")
        return redirect('teacher:dashboard')

    # Check for pending application
    pending_app = TeacherApplication.objects.filter(
        user=request.user,
        status__in=['pending', 'under_review', 'more_info_needed']
    ).first()

    if pending_app:
        messages.info(
            request,
            f"You have a pending application ({pending_app.application_number}). "
            f"We'll review it within 3-5 business days."
        )
        return redirect('teaching:application_status', pk=pending_app.pk)

    if request.method == 'POST':
        form = TeacherApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            application = form.save()
            messages.success(
                request,
                f"Application submitted successfully! Your application number is {application.application_number}. "
                f"We'll review your application within 3-5 business days."
            )
            return redirect('teaching:application_status', pk=application.pk)
    else:
        form = TeacherApplicationForm(user=request.user)

    context = {
        'form': form,
    }
    return render(request, 'teaching/apply_to_teach.html', context)
```

### Admin Application Review Interface

```python
# apps/admin_portal/views/applications.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from apps.teaching.models import TeacherApplication
from ..decorators import admin_required

@admin_required
def application_list(request):
    """
    List all teacher applications with filtering
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-submitted_at')

    # Base queryset
    applications = TeacherApplication.objects.select_related('user', 'reviewed_by')

    # Apply filters
    if status_filter and status_filter != 'all':
        applications = applications.filter(status=status_filter)

    if search_query:
        applications = applications.filter(
            Q(application_number__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Apply sorting
    applications = applications.order_by(sort_by)

    # Get counts for status tabs
    status_counts = TeacherApplication.objects.values('status').annotate(
        count=Count('id')
    )
    counts_dict = {item['status']: item['count'] for item in status_counts}

    context = {
        'applications': applications,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'status_counts': counts_dict,
        'total_pending': counts_dict.get('pending', 0) + counts_dict.get('under_review', 0),
    }

    return render(request, 'admin_portal/applications/list.html', context)


@admin_required
def application_detail(request, pk):
    """
    View full application details with approve/reject actions
    """
    application = get_object_or_404(
        TeacherApplication.objects.select_related('user', 'user__profile', 'reviewed_by'),
        pk=pk
    )

    # Get user's other applications (if any)
    previous_applications = TeacherApplication.objects.filter(
        user=application.user
    ).exclude(pk=pk).order_by('-submitted_at')

    context = {
        'application': application,
        'previous_applications': previous_applications,
        'user_profile': application.user.profile if hasattr(application.user, 'profile') else None,
    }

    return render(request, 'admin_portal/applications/detail.html', context)


@admin_required
def approve_application(request, pk):
    """
    Approve teacher application and convert user to teacher
    """
    if request.method != 'POST':
        return redirect('admin_portal:application_detail', pk=pk)

    application = get_object_or_404(TeacherApplication, pk=pk)

    success, message = application.approve(reviewed_by=request.user)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('admin_portal:application_detail', pk=pk)


@admin_required
def reject_application(request, pk):
    """
    Reject teacher application with reason
    """
    if request.method != 'POST':
        return redirect('admin_portal:application_detail', pk=pk)

    application = get_object_or_404(TeacherApplication, pk=pk)
    rejection_reason = request.POST.get('rejection_reason', '').strip()

    if not rejection_reason:
        messages.error(request, "Please provide a reason for rejection.")
        return redirect('admin_portal:application_detail', pk=pk)

    success, message = application.reject(
        reviewed_by=request.user,
        reason=rejection_reason
    )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('admin_portal:application_detail', pk=pk)


@admin_required
def request_info(request, pk):
    """
    Request additional information from applicant
    """
    if request.method != 'POST':
        return redirect('admin_portal:application_detail', pk=pk)

    application = get_object_or_404(TeacherApplication, pk=pk)
    info_request = request.POST.get('info_request', '').strip()

    if not info_request:
        messages.error(request, "Please specify what information is needed.")
        return redirect('admin_portal:application_detail', pk=pk)

    success, message = application.request_info(
        reviewed_by=request.user,
        info_request=info_request
    )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('admin_portal:application_detail', pk=pk)
```

### Email Notifications

```python
# apps/teaching/notifications.py

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def send_application_received_email(application):
    """Send confirmation email to applicant"""
    subject = f"Application Received - {application.application_number}"

    context = {
        'application': application,
        'user': application.user,
    }

    html_message = render_to_string(
        'teaching/emails/application_received.html',
        context
    )

    send_mail(
        subject=subject,
        message='',  # Plain text version
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message,
    )


def send_new_application_alert(application):
    """Alert admin/superusers of new application"""
    # Get admin emails
    admin_emails = User.objects.filter(
        is_superuser=True,
        is_active=True
    ).values_list('email', flat=True)

    if not admin_emails:
        admin_emails = User.objects.filter(
            is_staff=True,
            is_active=True
        ).values_list('email', flat=True)

    if not admin_emails:
        return

    subject = f"New Teacher Application - {application.application_number}"

    context = {
        'application': application,
        'review_url': f"{settings.SITE_URL}/admin-portal/applications/{application.pk}/",
    }

    html_message = render_to_string(
        'teaching/emails/new_application_alert.html',
        context
    )

    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=list(admin_emails),
        html_message=html_message,
    )


def send_application_approved_email(application):
    """Send approval notification with onboarding link"""
    subject = "Welcome to Recorder-ed Teaching Community!"

    context = {
        'application': application,
        'user': application.user,
        'onboarding_url': f"{settings.SITE_URL}/teaching/onboarding/",
        'dashboard_url': f"{settings.SITE_URL}/teacher/dashboard/",
    }

    html_message = render_to_string(
        'teaching/emails/application_approved.html',
        context
    )

    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message,
    )


def send_application_rejected_email(application):
    """Send rejection notification with reason"""
    subject = "Teacher Application Update"

    context = {
        'application': application,
        'user': application.user,
        'rejection_reason': application.rejection_reason,
    }

    html_message = render_to_string(
        'teaching/emails/application_rejected.html',
        context
    )

    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message,
    )


def send_info_request_email(application):
    """Request additional information from applicant"""
    subject = f"Additional Information Needed - {application.application_number}"

    context = {
        'application': application,
        'user': application.user,
        'info_request': application.info_requested,
        'response_url': f"{settings.SITE_URL}/teaching/application/{application.pk}/",
    }

    html_message = render_to_string(
        'teaching/emails/info_request.html',
        context
    )

    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message,
    )
```

---

## Teacher Onboarding System

### Overview

After application approval, guide new teachers through a structured onboarding process to ensure they:
1. Complete their teacher profile
2. Understand platform features
3. Set up their teaching preferences
4. Create their first content (optional)
5. Know how to get support

### Onboarding Model

```python
# apps/teaching/models.py (continued)

class TeacherOnboarding(models.Model):
    """
    Track teacher onboarding progress after application approval.
    """

    STEP_CHOICES = [
        ('welcome', 'Welcome'),
        ('profile', 'Complete Profile'),
        ('preferences', 'Teaching Preferences'),
        ('content', 'Create First Content'),
        ('dashboard_tour', 'Dashboard Tour'),
        ('completed', 'Onboarding Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_onboarding'
    )
    application = models.OneToOneField(
        TeacherApplication,
        on_delete=models.SET_NULL,
        null=True,
        related_name='onboarding'
    )

    # Progress tracking
    current_step = models.CharField(
        max_length=20,
        choices=STEP_CHOICES,
        default='welcome'
    )

    # Step completion flags
    welcome_completed = models.BooleanField(default=False)
    welcome_completed_at = models.DateTimeField(null=True, blank=True)

    profile_completed = models.BooleanField(default=False)
    profile_completed_at = models.DateTimeField(null=True, blank=True)

    preferences_completed = models.BooleanField(default=False)
    preferences_completed_at = models.DateTimeField(null=True, blank=True)

    content_created = models.BooleanField(default=False)
    content_created_at = models.DateTimeField(null=True, blank=True)
    content_skipped = models.BooleanField(default=False)

    dashboard_tour_completed = models.BooleanField(default=False)
    dashboard_tour_completed_at = models.DateTimeField(null=True, blank=True)

    # Overall completion
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Teacher Onboarding"
        verbose_name_plural = "Teacher Onboardings"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_current_step_display()}"

    @property
    def progress_percentage(self):
        """Calculate onboarding completion percentage"""
        total_steps = 5  # welcome, profile, preferences, content, dashboard
        completed_steps = sum([
            self.welcome_completed,
            self.profile_completed,
            self.preferences_completed,
            self.content_created or self.content_skipped,
            self.dashboard_tour_completed,
        ])
        return int((completed_steps / total_steps) * 100)

    def mark_step_complete(self, step_name):
        """Mark a specific step as complete and advance to next"""
        from django.utils import timezone

        if step_name == 'welcome':
            self.welcome_completed = True
            self.welcome_completed_at = timezone.now()
            self.current_step = 'profile'

        elif step_name == 'profile':
            self.profile_completed = True
            self.profile_completed_at = timezone.now()
            self.current_step = 'preferences'

        elif step_name == 'preferences':
            self.preferences_completed = True
            self.preferences_completed_at = timezone.now()
            self.current_step = 'content'

        elif step_name == 'content':
            self.content_created = True
            self.content_created_at = timezone.now()
            self.current_step = 'dashboard_tour'

        elif step_name == 'dashboard_tour':
            self.dashboard_tour_completed = True
            self.dashboard_tour_completed_at = timezone.now()
            self.current_step = 'completed'
            self.completed = True
            self.completed_at = timezone.now()

        self.save()

    def skip_content_creation(self):
        """Allow skipping content creation step"""
        self.content_skipped = True
        self.current_step = 'dashboard_tour'
        self.save()

    def get_next_step_url(self):
        """Get URL for next onboarding step"""
        from django.urls import reverse

        step_urls = {
            'welcome': reverse('teaching:onboarding_welcome'),
            'profile': reverse('teaching:onboarding_profile'),
            'preferences': reverse('teaching:onboarding_preferences'),
            'content': reverse('teaching:onboarding_content'),
            'dashboard_tour': reverse('teaching:onboarding_tour'),
            'completed': reverse('teacher:dashboard'),
        }

        return step_urls.get(self.current_step, reverse('teacher:dashboard'))
```

### Onboarding Views

```python
# apps/teaching/views/onboarding.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import TeacherOnboarding
from ..decorators import teacher_required

@teacher_required
def onboarding_check(request):
    """
    Check if teacher needs onboarding, redirect to appropriate step.
    Called after login or from dashboard.
    """
    # Get or create onboarding record
    onboarding, created = TeacherOnboarding.objects.get_or_create(
        user=request.user
    )

    # If already completed, go to dashboard
    if onboarding.completed:
        return redirect('teacher:dashboard')

    # Redirect to current step
    return redirect(onboarding.get_next_step_url())


@teacher_required
def onboarding_welcome(request):
    """
    Step 1: Welcome and overview
    """
    onboarding = get_object_or_404(TeacherOnboarding, user=request.user)

    if request.method == 'POST':
        onboarding.mark_step_complete('welcome')
        return redirect(onboarding.get_next_step_url())

    context = {
        'onboarding': onboarding,
    }
    return render(request, 'teaching/onboarding/welcome.html', context)


@teacher_required
def onboarding_profile(request):
    """
    Step 2: Complete teacher profile
    """
    onboarding = get_object_or_404(TeacherOnboarding, user=request.user)
    profile = request.user.profile

    if request.method == 'POST':
        # Profile form handling (reuse existing profile form)
        from apps.accounts.forms import TeacherProfileForm
        form = TeacherProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            form.save()
            onboarding.mark_step_complete('profile')
            messages.success(request, "Profile completed!")
            return redirect(onboarding.get_next_step_url())
    else:
        from apps.accounts.forms import TeacherProfileForm
        form = TeacherProfileForm(instance=profile)

    context = {
        'onboarding': onboarding,
        'form': form,
        'profile': profile,
    }
    return render(request, 'teaching/onboarding/profile.html', context)


@teacher_required
def onboarding_preferences(request):
    """
    Step 3: Set teaching preferences (formats, availability, etc.)
    """
    onboarding = get_object_or_404(TeacherOnboarding, user=request.user)
    profile = request.user.profile

    if request.method == 'POST':
        # Teaching preferences form
        # Fields: teaching formats, availability, max students, etc.

        # Update profile with preferences
        profile.accepting_new_private_students = request.POST.get('accepting_students') == 'on'
        profile.max_private_students = request.POST.get('max_students', 10)
        profile.default_zoom_link = request.POST.get('zoom_link', '')
        profile.save()

        onboarding.mark_step_complete('preferences')
        messages.success(request, "Preferences saved!")
        return redirect(onboarding.get_next_step_url())

    context = {
        'onboarding': onboarding,
        'profile': profile,
    }
    return render(request, 'teaching/onboarding/preferences.html', context)


@teacher_required
def onboarding_content(request):
    """
    Step 4: Create first content (course/workshop) - OPTIONAL
    """
    onboarding = get_object_or_404(TeacherOnboarding, user=request.user)

    # Check if teacher already has content
    from apps.courses.models import Course
    from apps.workshops.models import Workshop

    has_courses = Course.objects.filter(instructor=request.user).exists()
    has_workshops = Workshop.objects.filter(instructor=request.user).exists()

    if has_courses or has_workshops:
        onboarding.mark_step_complete('content')
        return redirect(onboarding.get_next_step_url())

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'skip':
            onboarding.skip_content_creation()
            messages.info(request, "You can create content anytime from your dashboard.")
            return redirect(onboarding.get_next_step_url())

        elif action == 'create_course':
            return redirect('courses:instructor_create')

        elif action == 'create_workshop':
            return redirect('workshops:instructor_create')

    context = {
        'onboarding': onboarding,
    }
    return render(request, 'teaching/onboarding/content.html', context)


@teacher_required
def onboarding_tour(request):
    """
    Step 5: Dashboard tour (interactive guide)
    """
    onboarding = get_object_or_404(TeacherOnboarding, user=request.user)

    if request.method == 'POST':
        onboarding.mark_step_complete('dashboard_tour')
        messages.success(request, "🎉 Onboarding completed! Welcome to Recorder-ed!")
        return redirect('teacher:dashboard')

    context = {
        'onboarding': onboarding,
    }
    return render(request, 'teaching/onboarding/tour.html', context)
```

### Onboarding Templates

#### Welcome Screen

```html
<!-- templates/teaching/onboarding/welcome.html -->
{% extends 'base.html' %}

{% block content %}
<div class="min-h-screen bg-gradient-to-br from-primary to-secondary flex items-center justify-center p-4">
    <div class="max-w-3xl bg-base-100 rounded-2xl shadow-2xl p-8">
        <!-- Progress Bar -->
        <div class="mb-8">
            <div class="flex justify-between text-sm mb-2">
                <span class="font-semibold">Welcome</span>
                <span class="text-base-content/60">Step 1 of 5</span>
            </div>
            <progress class="progress progress-primary w-full" value="20" max="100"></progress>
        </div>

        <!-- Welcome Content -->
        <div class="text-center mb-8">
            <div class="text-6xl mb-4">🎉</div>
            <h1 class="text-4xl font-bold mb-4">Welcome to Recorder-ed!</h1>
            <p class="text-xl text-base-content/80 mb-6">
                Your application has been approved. Let's get you set up to start teaching!
            </p>
        </div>

        <!-- What to Expect -->
        <div class="card bg-base-200 mb-8">
            <div class="card-body">
                <h2 class="card-title text-2xl mb-4">What to expect:</h2>
                <div class="space-y-4">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-primary text-primary-content rounded-full flex items-center justify-center font-bold">
                                1
                            </div>
                        </div>
                        <div>
                            <h3 class="font-semibold">Complete Your Profile</h3>
                            <p class="text-sm text-base-content/70">Add your photo, bio, and teaching credentials</p>
                        </div>
                    </div>

                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-primary text-primary-content rounded-full flex items-center justify-center font-bold">
                                2
                            </div>
                        </div>
                        <div>
                            <h3 class="font-semibold">Set Your Preferences</h3>
                            <p class="text-sm text-base-content/70">Choose teaching formats, availability, and student limits</p>
                        </div>
                    </div>

                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-primary text-primary-content rounded-full flex items-center justify-center font-bold">
                                3
                            </div>
                        </div>
                        <div>
                            <h3 class="font-semibold">Create Your First Content</h3>
                            <p class="text-sm text-base-content/70">Start with a course or workshop (you can skip this step)</p>
                        </div>
                    </div>

                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-primary text-primary-content rounded-full flex items-center justify-center font-bold">
                                4
                            </div>
                        </div>
                        <div>
                            <h3 class="font-semibold">Dashboard Tour</h3>
                            <p class="text-sm text-base-content/70">Learn how to manage your teaching on the platform</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Platform Benefits -->
        <div class="grid md:grid-cols-3 gap-4 mb-8">
            <div class="card bg-base-200">
                <div class="card-body items-center text-center">
                    <div class="text-3xl mb-2">🎓</div>
                    <h3 class="font-semibold">Teach Your Way</h3>
                    <p class="text-sm text-base-content/70">Online, in-person, or both</p>
                </div>
            </div>

            <div class="card bg-base-200">
                <div class="card-body items-center text-center">
                    <div class="text-3xl mb-2">💰</div>
                    <h3 class="font-semibold">Set Your Rates</h3>
                    <p class="text-sm text-base-content/70">You control your pricing</p>
                </div>
            </div>

            <div class="card bg-base-200">
                <div class="card-body items-center text-center">
                    <div class="text-3xl mb-2">📊</div>
                    <h3 class="font-semibold">Track Progress</h3>
                    <p class="text-sm text-base-content/70">Analytics and insights</p>
                </div>
            </div>
        </div>

        <!-- Estimated Time -->
        <div class="alert alert-info mb-8">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>This setup takes about <strong>5-10 minutes</strong> to complete.</span>
        </div>

        <!-- Action Buttons -->
        <form method="post" class="flex gap-4">
            {% csrf_token %}
            <button type="submit" class="btn btn-primary btn-lg flex-1">
                Let's Get Started
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
            </button>
        </form>

        <div class="text-center mt-4">
            <a href="{% url 'teacher:dashboard' %}" class="link link-hover text-sm">
                Skip onboarding and go to dashboard →
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

### Onboarding Checklist Widget

Display onboarding progress in teacher dashboard until completed.

```html
<!-- templates/teaching/onboarding/checklist_widget.html -->
{% if user.teacher_onboarding and not user.teacher_onboarding.completed %}
<div class="card bg-gradient-to-r from-primary/10 to-secondary/10 border-2 border-primary/20 mb-6">
    <div class="card-body">
        <div class="flex justify-between items-center mb-4">
            <h3 class="card-title">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Complete Your Teacher Setup
            </h3>
            <span class="badge badge-primary badge-lg">{{ user.teacher_onboarding.progress_percentage }}%</span>
        </div>

        <progress class="progress progress-primary w-full mb-4" value="{{ user.teacher_onboarding.progress_percentage }}" max="100"></progress>

        <div class="space-y-2">
            <!-- Welcome Step -->
            <div class="flex items-center gap-3">
                {% if user.teacher_onboarding.welcome_completed %}
                <svg class="w-5 h-5 text-success" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="line-through text-base-content/60">Welcome & Overview</span>
                {% else %}
                <svg class="w-5 h-5 text-base-content/30" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clip-rule="evenodd"/>
                </svg>
                <a href="{% url 'teaching:onboarding_welcome' %}" class="link link-primary">Welcome & Overview</a>
                {% endif %}
            </div>

            <!-- Profile Step -->
            <div class="flex items-center gap-3">
                {% if user.teacher_onboarding.profile_completed %}
                <svg class="w-5 h-5 text-success" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="line-through text-base-content/60">Complete Profile</span>
                {% else %}
                <svg class="w-5 h-5 text-base-content/30" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clip-rule="evenodd"/>
                </svg>
                <a href="{% url 'teaching:onboarding_profile' %}" class="link link-primary">Complete Profile</a>
                {% endif %}
            </div>

            <!-- Preferences Step -->
            <div class="flex items-center gap-3">
                {% if user.teacher_onboarding.preferences_completed %}
                <svg class="w-5 h-5 text-success" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="line-through text-base-content/60">Set Preferences</span>
                {% else %}
                <svg class="w-5 h-5 text-base-content/30" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clip-rule="evenodd"/>
                </svg>
                <a href="{% url 'teaching:onboarding_preferences' %}" class="link link-primary">Set Preferences</a>
                {% endif %}
            </div>

            <!-- Content Step -->
            <div class="flex items-center gap-3">
                {% if user.teacher_onboarding.content_created or user.teacher_onboarding.content_skipped %}
                <svg class="w-5 h-5 text-success" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="line-through text-base-content/60">Create Content (Optional)</span>
                {% else %}
                <svg class="w-5 h-5 text-base-content/30" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clip-rule="evenodd"/>
                </svg>
                <a href="{% url 'teaching:onboarding_content' %}" class="link link-primary">Create Content (Optional)</a>
                {% endif %}
            </div>

            <!-- Dashboard Tour Step -->
            <div class="flex items-center gap-3">
                {% if user.teacher_onboarding.dashboard_tour_completed %}
                <svg class="w-5 h-5 text-success" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="line-through text-base-content/60">Dashboard Tour</span>
                {% else %}
                <svg class="w-5 h-5 text-base-content/30" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clip-rule="evenodd"/>
                </svg>
                <a href="{% url 'teaching:onboarding_tour' %}" class="link link-primary">Dashboard Tour</a>
                {% endif %}
            </div>
        </div>

        <div class="card-actions justify-end mt-4">
            <a href="{{ user.teacher_onboarding.get_next_step_url }}" class="btn btn-primary btn-sm">
                Continue Setup →
            </a>
        </div>
    </div>
</div>
{% endif %}
```

### Automatic Onboarding Creation

Create onboarding record automatically when teacher application is approved.

```python
# Update apps/teaching/models.py - TeacherApplication.approve() method

def approve(self, reviewed_by):
    """
    Approve application and convert user to teacher.
    Returns: tuple (success: bool, message: str)
    """
    if self.status == 'approved':
        return False, "Application already approved"

    # Update application
    self.status = 'approved'
    self.reviewed_by = reviewed_by
    self.reviewed_at = timezone.now()
    self.approved_at = timezone.now()
    self.save()

    # Convert user to teacher
    profile = self.user.profile
    profile.is_teacher = True

    # Copy application data to profile
    profile.bio = self.teaching_experience
    profile.qualifications = self.qualifications
    profile.dbs_check_status = self.dbs_check_status
    profile.instruments_taught = self.subjects

    if self.phone and not profile.phone:
        profile.phone = self.phone

    profile.save()

    # Create onboarding record
    TeacherOnboarding.objects.get_or_create(
        user=self.user,
        defaults={'application': self}
    )

    # Send approval notification
    from .notifications import send_application_approved_email
    send_application_approved_email(self)

    return True, f"Application approved. {self.user.get_full_name()} is now a teacher."
```

---

## Admin Portal Modules

### Module 1: Dashboard

**URL:** `/admin-portal/`

**Purpose:** Overview of platform health and quick access to common tasks

**Features:**
- Quick stats (new users, pending applications, revenue, etc.)
- Alerts/notifications (overdue tickets, flagged content)
- Recent activity feed
- Quick actions (approve application, respond to ticket)

**View Code:**
```python
# apps/admin_portal/views.py

from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from .decorators import admin_required
from apps.teaching.models import TeacherApplication
from apps.support.models import Ticket
from apps.accounts.models import User
from apps.courses.models import Course, Enrollment
from apps.workshops.models import Workshop, WorkshopRegistration

@admin_required
def dashboard(request):
    """Admin portal homepage with key metrics"""

    # Time periods
    now = timezone.now()
    today = now.date()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # User metrics
    new_users_7d = User.objects.filter(date_joined__gte=seven_days_ago).count()
    total_students = User.objects.filter(profile__is_student=True).count()
    total_teachers = User.objects.filter(profile__is_teacher=True).count()

    # Application metrics
    pending_applications = TeacherApplication.objects.filter(
        status__in=['pending', 'under_review']
    ).count()
    overdue_applications = TeacherApplication.objects.filter(
        status__in=['pending', 'under_review'],
        submitted_at__lt=now - timedelta(days=5)
    ).count()

    # Support metrics
    open_tickets = Ticket.objects.filter(status__in=['open', 'in_progress']).count()
    overdue_tickets = Ticket.objects.filter(
        status__in=['open', 'in_progress'],
        # SLA logic here
    ).count()
    unassigned_tickets = Ticket.objects.filter(
        status='open',
        assigned_to__isnull=True
    ).count()

    # Content metrics
    new_courses_7d = Course.objects.filter(created_at__gte=seven_days_ago).count()
    new_workshops_7d = Workshop.objects.filter(created_at__gte=seven_days_ago).count()

    # Enrollment metrics
    enrollments_today = Enrollment.objects.filter(enrolled_at__date=today).count()
    enrollments_7d = Enrollment.objects.filter(enrolled_at__gte=seven_days_ago).count()
    workshop_registrations_7d = WorkshopRegistration.objects.filter(
        registered_at__gte=seven_days_ago
    ).count()

    # Revenue metrics (if payments app exists)
    try:
        from apps.payments.models import Payment
        monthly_revenue = Payment.objects.filter(
            status='succeeded',
            created_at__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_revenue = monthly_revenue / 100  # Convert pence to pounds
    except ImportError:
        monthly_revenue = 0

    # Recent activity
    recent_applications = TeacherApplication.objects.filter(
        status='pending'
    ).select_related('user').order_by('-submitted_at')[:5]

    recent_tickets = Ticket.objects.filter(
        status='open'
    ).select_related('user').order_by('-created_at')[:5]

    recent_enrollments = Enrollment.objects.select_related(
        'user', 'course'
    ).order_by('-enrolled_at')[:10]

    context = {
        # User metrics
        'new_users_7d': new_users_7d,
        'total_students': total_students,
        'total_teachers': total_teachers,

        # Applications
        'pending_applications': pending_applications,
        'overdue_applications': overdue_applications,

        # Support
        'open_tickets': open_tickets,
        'overdue_tickets': overdue_tickets,
        'unassigned_tickets': unassigned_tickets,

        # Content
        'new_courses_7d': new_courses_7d,
        'new_workshops_7d': new_workshops_7d,

        # Enrollments
        'enrollments_today': enrollments_today,
        'enrollments_7d': enrollments_7d,
        'workshop_registrations_7d': workshop_registrations_7d,

        # Revenue
        'monthly_revenue': monthly_revenue,

        # Recent activity
        'recent_applications': recent_applications,
        'recent_tickets': recent_tickets,
        'recent_enrollments': recent_enrollments,
    }

    return render(request, 'admin_portal/dashboard.html', context)
```

### Module 2: Support Management

**URL:** `/admin-portal/support/`

**Purpose:** Manage support tickets (migrated from `/support/staff/`)

**Features:**
- Ticket list with filtering (status, category, priority, assignment)
- Ticket detail view
- Respond to tickets
- Update status/priority/assignment
- Internal notes
- SLA tracking

**Implementation:**
- Reuse existing support views from `apps/support/views.py`
- Update templates to extend `admin_portal/base.html`
- Update URLs to nest under `/admin-portal/support/`

### Module 3: Teacher Applications

**URL:** `/admin-portal/applications/`

**Purpose:** Review and manage teacher applications

**Features:**
- Application list with status tabs (pending, under review, approved, rejected)
- Application detail view showing full information
- One-click approve/reject buttons
- Request additional information
- View applicant's user profile
- Application analytics

**Implementation:** See "Teacher Application System" section above

### Module 4: User Management

**URL:** `/admin-portal/users/`

**Purpose:** Search, view, and manage user accounts

**Features:**
- User search (by name, email, ID)
- User list with filters (role, status, registration date)
- User detail view:
  - Profile information
  - Enrollments/registrations
  - Purchase history
  - Activity log
- Actions:
  - Flag/suspend account
  - Manually change role (student ↔ teacher)
  - Password reset
  - Send email

**View Skeleton:**
```python
@admin_required
def user_list(request):
    """List all users with search and filters"""
    # Search, filter, paginate
    pass

@admin_required
def user_detail(request, user_id):
    """View full user details and activity"""
    # Show profile, enrollments, purchases, activity
    pass

@admin_required
def user_action(request, user_id):
    """Perform actions on user account"""
    # Suspend, change role, reset password, etc.
    pass
```

### Module 5: Content Moderation

**URL:** `/admin-portal/content/`

**Purpose:** Review and moderate courses, workshops, and user-generated content

**Features:**
- Flagged content queue
- Course/workshop approval workflow (if required)
- Featured content selection
- Content quality checks
- Unpublish/remove content

**View Skeleton:**
```python
@admin_required
def content_list(request):
    """List content requiring moderation"""
    pass

@admin_required
def content_review(request, content_type, content_id):
    """Review specific content item"""
    pass
```

### Module 6: Financial/Payments

**URL:** `/admin-portal/payments/`

**Purpose:** Monitor revenue, payments, and teacher payouts

**Features:**
- Revenue dashboard (daily/weekly/monthly)
- Payment transaction log
- Refund management
- Teacher payout tracking
- Stripe integration health check

**Permissions:** Superuser only

### Module 7: Platform Analytics

**URL:** `/admin-portal/analytics/`

**Purpose:** Platform-wide analytics and reporting

**Features:**
- User growth charts
- Revenue trends
- Course/workshop performance
- Teacher metrics
- Conversion funnels
- Export reports (CSV, PDF)
- Google Analytics integration

**Permissions:** Staff + Analytics permission

### Module 8: Settings

**URL:** `/admin-portal/settings/`

**Purpose:** Configure platform settings

**Features:**
- Email templates
- Payment configuration (Stripe keys, commission rates)
- Feature flags
- SLA thresholds
- Platform announcements
- Maintenance mode

**Permissions:** Superuser only

---

## Database Schema

### New Tables

#### teaching_teacherapplication
```sql
CREATE TABLE teaching_teacherapplication (
    id UUID PRIMARY KEY,
    application_number VARCHAR(20) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- Contact
    name VARCHAR(200) NOT NULL,
    email VARCHAR(254) NOT NULL,
    phone VARCHAR(20),

    -- Teaching info
    teaching_experience TEXT NOT NULL,
    qualifications TEXT NOT NULL,
    subjects VARCHAR(500) NOT NULL,
    dbs_check_status VARCHAR(20) NOT NULL,
    preferred_formats JSONB DEFAULT '[]',
    availability TEXT NOT NULL,

    -- Terms
    terms_accepted BOOLEAN DEFAULT FALSE,
    terms_accepted_at TIMESTAMP WITH TIME ZONE,

    -- Review
    reviewed_by_id INTEGER REFERENCES auth_user(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    admin_notes TEXT,

    -- Approval/Rejection
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Info requests
    info_requested TEXT,
    info_requested_at TIMESTAMP WITH TIME ZONE,
    info_provided TEXT,
    info_provided_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_teacherapplication_status ON teaching_teacherapplication(status, submitted_at DESC);
CREATE INDEX idx_teacherapplication_user ON teaching_teacherapplication(user_id, submitted_at DESC);
```

#### teaching_teacherapplicationattachment
```sql
CREATE TABLE teaching_teacherapplicationattachment (
    id UUID PRIMARY KEY,
    application_id UUID NOT NULL REFERENCES teaching_teacherapplication(id) ON DELETE CASCADE,
    file VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### teaching_teacheronboarding
```sql
CREATE TABLE teaching_teacheronboarding (
    id UUID PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES auth_user(id),
    application_id UUID REFERENCES teaching_teacherapplication(id) ON DELETE SET NULL,

    current_step VARCHAR(20) NOT NULL DEFAULT 'welcome',

    -- Step completion
    welcome_completed BOOLEAN DEFAULT FALSE,
    welcome_completed_at TIMESTAMP WITH TIME ZONE,

    profile_completed BOOLEAN DEFAULT FALSE,
    profile_completed_at TIMESTAMP WITH TIME ZONE,

    preferences_completed BOOLEAN DEFAULT FALSE,
    preferences_completed_at TIMESTAMP WITH TIME ZONE,

    content_created BOOLEAN DEFAULT FALSE,
    content_created_at TIMESTAMP WITH TIME ZONE,
    content_skipped BOOLEAN DEFAULT FALSE,

    dashboard_tour_completed BOOLEAN DEFAULT FALSE,
    dashboard_tour_completed_at TIMESTAMP WITH TIME ZONE,

    -- Overall
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### Modified Tables

#### accounts_userprofile
No schema changes required. Existing fields used:
- `is_teacher` (set to `TRUE` on approval)
- `bio`, `qualifications`, `dbs_check_status` (populated from application)

---

## Implementation Phases

### Phase 1: Foundation (Days 1-2)

**Goal:** Create admin portal structure and base functionality

**Tasks:**
1. Create `apps/admin_portal/` app
2. Build base layout and navigation
3. Create admin dashboard homepage
4. Implement `@admin_required` decorator
5. Update login redirect logic
6. Test admin portal access

**Deliverables:**
- `/admin-portal/` accessible to staff users
- Dashboard showing basic metrics
- Navigation sidebar with module placeholders

**Files Created:**
```
apps/admin_portal/
├── __init__.py
├── urls.py
├── views.py
├── decorators.py
├── templates/
│   └── admin_portal/
│       ├── base.html
│       └── dashboard.html
└── static/admin_portal/
    ├── css/admin.css
    └── js/admin.js
```

### Phase 2: Support Migration (Day 2)

**Goal:** Move support dashboard into admin portal

**Tasks:**
1. Create `/admin-portal/support/` URLs
2. Update support views to use admin portal base template
3. Add redirect from old `/support/staff/` to new location
4. Test support ticket workflow in new portal

**Deliverables:**
- Support management accessible at `/admin-portal/support/`
- Old URL redirects to new location
- All support features working in new portal

### Phase 3: Teacher Application System (Days 3-4)

**Goal:** Implement dedicated teacher application system

**Tasks:**
1. Create `apps/teaching/` app
2. Create `TeacherApplication` model
3. Run migrations
4. Create application form (update existing `/support/apply-to-teach/`)
5. Build application review interface
6. Implement approve/reject actions
7. Create email notifications
8. Test full application workflow

**Deliverables:**
- Teacher applications at `/admin-portal/applications/`
- One-click approve/reject functionality
- Automated email notifications
- Application status tracking

**Files Created:**
```
apps/teaching/
├── __init__.py
├── models.py (TeacherApplication, TeacherApplicationAttachment)
├── forms.py (TeacherApplicationForm)
├── views.py (apply_to_teach, application_status)
├── notifications.py
├── urls.py
├── admin.py
└── templates/teaching/
    ├── apply_to_teach.html
    ├── application_status.html
    └── emails/
        ├── application_received.html
        ├── application_approved.html
        ├── application_rejected.html
        └── info_request.html
```

### Phase 4: Teacher Onboarding (Day 5)

**Goal:** Build teacher onboarding flow

**Tasks:**
1. Create `TeacherOnboarding` model
2. Build onboarding views (welcome, profile, preferences, content, tour)
3. Create onboarding templates
4. Implement progress tracking
5. Create onboarding checklist widget
6. Integrate with dashboard
7. Test onboarding flow

**Deliverables:**
- 5-step onboarding wizard at `/teaching/onboarding/`
- Progress tracking
- Onboarding checklist in teacher dashboard
- Auto-creation on application approval

**Files Created:**
```
apps/teaching/
├── models.py (TeacherOnboarding - add to existing file)
├── views/
│   └── onboarding.py
└── templates/teaching/onboarding/
    ├── welcome.html
    ├── profile.html
    ├── preferences.html
    ├── content.html
    ├── tour.html
    └── checklist_widget.html
```

### Phase 5: Additional Admin Modules (Days 6-10, as needed)

**Goal:** Build remaining admin portal modules

**Priority Order:**
1. User Management (1-2 days)
2. Content Moderation (1-2 days)
3. Analytics Dashboard (2-3 days)
4. Financial/Payments (1-2 days)
5. Settings (1 day)

**Implementation:** Incremental, based on business needs

---

## Technical Requirements

### Backend Requirements

**Framework:** Django 5.2.7 (existing)

**Python Packages (already installed):**
- django
- django-allauth (authentication)
- django-ckeditor-5 (rich text)
- pillow (image handling)
- stripe (payments)

**New Dependencies:** None required

### Frontend Requirements

**CSS Framework:** Tailwind CSS + DaisyUI (existing)

**JavaScript:** Alpine.js (existing) + vanilla JS for interactive features

**Icons:** Font Awesome (existing) or Heroicons

### Database Requirements

**PostgreSQL** (production) / SQLite (development)

**Migrations:**
- Create `teaching_teacherapplication` table
- Create `teaching_teacherapplicationattachment` table
- Create `teaching_teacheronboarding` table

### Email Requirements

**Service:** SendGrid / Mailgun / SMTP (existing configuration)

**Templates Needed:**
- Application received confirmation
- New application alert (to admins)
- Application approved notification
- Application rejected notification
- Info request notification
- Onboarding welcome email

### Hosting Requirements

**No changes** - works with existing infrastructure

---

## File Structure

```
recorder_ed/
├── apps/
│   ├── admin_portal/              # NEW
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── decorators.py
│   │   ├── urls.py
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py
│   │   │   ├── applications.py
│   │   │   ├── users.py
│   │   │   ├── content.py
│   │   │   ├── payments.py
│   │   │   ├── analytics.py
│   │   │   └── settings.py
│   │   ├── templates/
│   │   │   └── admin_portal/
│   │   │       ├── base.html
│   │   │       ├── dashboard.html
│   │   │       ├── applications/
│   │   │       │   ├── list.html
│   │   │       │   └── detail.html
│   │   │       ├── support/
│   │   │       │   └── (migrated support templates)
│   │   │       ├── users/
│   │   │       ├── content/
│   │   │       ├── payments/
│   │   │       ├── analytics/
│   │   │       └── settings/
│   │   └── static/admin_portal/
│   │       ├── css/
│   │       │   └── admin.css
│   │       └── js/
│   │           └── admin.js
│   │
│   ├── teaching/                   # NEW
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   │   ├── TeacherApplication
│   │   │   ├── TeacherApplicationAttachment
│   │   │   └── TeacherOnboarding
│   │   ├── forms.py
│   │   │   └── TeacherApplicationForm
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── application.py
│   │   │   └── onboarding.py
│   │   ├── notifications.py
│   │   ├── decorators.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   ├── templates/teaching/
│   │   │   ├── apply_to_teach.html
│   │   │   ├── application_status.html
│   │   │   ├── onboarding/
│   │   │   │   ├── welcome.html
│   │   │   │   ├── profile.html
│   │   │   │   ├── preferences.html
│   │   │   │   ├── content.html
│   │   │   │   ├── tour.html
│   │   │   │   └── checklist_widget.html
│   │   │   └── emails/
│   │   │       ├── application_received.html
│   │   │       ├── new_application_alert.html
│   │   │       ├── application_approved.html
│   │   │       ├── application_rejected.html
│   │   │       └── info_request.html
│   │   └── static/teaching/
│   │
│   ├── accounts/                   # MODIFIED
│   │   └── views.py                # Update login redirect
│   │
│   ├── support/                    # MODIFIED
│   │   ├── urls.py                 # Add redirect from old dashboard
│   │   └── templates/support/
│   │       └── (update to extend admin_portal/base.html)
│   │
│   └── (other existing apps...)
│
├── recordered/
│   ├── settings.py                 # Add admin_portal, teaching to INSTALLED_APPS
│   └── urls.py                     # Add admin portal URLs
│
└── templates/
    └── (existing templates)
```

---

## API Endpoints

### Public Endpoints

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| GET/POST | `/teaching/apply/` | Teacher application form | Login required |
| GET | `/teaching/application/<uuid>/` | View application status | Own application only |

### Admin Portal Endpoints

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| GET | `/admin-portal/` | Dashboard | @admin_required |
| GET | `/admin-portal/support/` | Support ticket list | @admin_required |
| GET | `/admin-portal/support/<uuid>/` | Ticket detail | @admin_required |
| POST | `/admin-portal/support/<uuid>/update/` | Update ticket | @admin_required |
| GET | `/admin-portal/applications/` | Application list | @admin_required |
| GET | `/admin-portal/applications/<uuid>/` | Application detail | @admin_required |
| POST | `/admin-portal/applications/<uuid>/approve/` | Approve application | @admin_required |
| POST | `/admin-portal/applications/<uuid>/reject/` | Reject application | @admin_required |
| POST | `/admin-portal/applications/<uuid>/request-info/` | Request additional info | @admin_required |
| GET | `/admin-portal/users/` | User list | @admin_required |
| GET | `/admin-portal/users/<id>/` | User detail | @admin_required |
| GET | `/admin-portal/content/` | Content moderation | @admin_required |
| GET | `/admin-portal/payments/` | Financial dashboard | Superuser only |
| GET | `/admin-portal/analytics/` | Platform analytics | @admin_required |
| GET | `/admin-portal/settings/` | Platform settings | Superuser only |

### Teacher Onboarding Endpoints

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| GET | `/teaching/onboarding/` | Check/redirect to current step | @teacher_required |
| GET/POST | `/teaching/onboarding/welcome/` | Welcome step | @teacher_required |
| GET/POST | `/teaching/onboarding/profile/` | Profile completion | @teacher_required |
| GET/POST | `/teaching/onboarding/preferences/` | Set preferences | @teacher_required |
| GET/POST | `/teaching/onboarding/content/` | Create content (optional) | @teacher_required |
| GET/POST | `/teaching/onboarding/tour/` | Dashboard tour | @teacher_required |

---

## Security Considerations

### Access Control

**Admin Portal:**
- Required: `is_staff=True` OR `is_superuser=True`
- Decorator: `@admin_required`
- Redirects to login if unauthenticated
- Shows error message if not authorized

**Teacher Onboarding:**
- Required: `profile.is_teacher=True`
- Decorator: `@teacher_required`

**Superuser-Only Sections:**
- Payments module
- Settings module
- Django admin

### Data Privacy

**Teacher Applications:**
- Only admins can view all applications
- Applicants can only view their own applications
- Sensitive data (DBS status) encrypted at rest
- Audit log of who approved/rejected

**User Data:**
- Admin portal users can view user data for support purposes
- No bulk data export without superuser permission
- User consent required for data processing (GDPR compliance)

### Rate Limiting

**Application Submissions:**
- Max 1 application per user per 30 days
- Prevent spam applications

**Admin Actions:**
- Rate limit approve/reject actions to prevent accidental bulk operations

### CSRF Protection

All POST requests require CSRF token (Django default)

### Input Validation

- All forms validated server-side
- Sanitize user input (especially in rejection reasons, admin notes)
- File upload validation (type, size limits)

---

## Testing Strategy

### Unit Tests

**Models:**
```python
# tests/test_teaching_models.py

def test_teacher_application_creation():
    """Test creating teacher application"""

def test_application_approval():
    """Test approve() method converts user to teacher"""

def test_application_rejection():
    """Test reject() method updates status"""

def test_onboarding_progress():
    """Test onboarding progress calculation"""
```

**Views:**
```python
# tests/test_admin_portal_views.py

def test_admin_dashboard_access():
    """Test only staff can access admin portal"""

def test_approve_application():
    """Test application approval workflow"""

def test_reject_application():
    """Test application rejection workflow"""
```

### Integration Tests

**Application Workflow:**
```python
def test_full_application_workflow():
    """
    Test complete workflow:
    1. User submits application
    2. Email sent to admins
    3. Admin approves
    4. User converted to teacher
    5. Onboarding created
    6. Approval email sent
    """
```

**Onboarding Workflow:**
```python
def test_onboarding_completion():
    """
    Test teacher can complete all onboarding steps
    """
```

### Manual Testing Checklist

**Admin Portal:**
- [ ] Staff user can log in and see admin portal
- [ ] Student cannot access admin portal
- [ ] Dashboard shows correct metrics
- [ ] Navigation works between modules

**Teacher Applications:**
- [ ] Public user can submit application
- [ ] Confirmation email received
- [ ] Admin receives notification email
- [ ] Admin can view application details
- [ ] Approve button works, converts user to teacher
- [ ] Rejection sends email with reason
- [ ] Request info updates status

**Teacher Onboarding:**
- [ ] Onboarding created on approval
- [ ] Welcome screen displays correctly
- [ ] Each step can be completed
- [ ] Progress tracking accurate
- [ ] Can skip content creation
- [ ] Checklist widget shows in dashboard
- [ ] Completion redirects to dashboard

### Performance Testing

**Database Queries:**
- Use `select_related()` and `prefetch_related()` to minimize queries
- Test dashboard with 1000+ applications
- Ensure application list pagination works

**Email Sending:**
- Test email queuing for bulk notifications
- Ensure emails sent asynchronously (Celery or similar)

---

## Deployment Plan

### Pre-Deployment

1. **Code Review:**
   - Review all new code
   - Security audit
   - Performance review

2. **Database Backup:**
   - Full backup of production database
   - Test restore procedure

3. **Test on Staging:**
   - Deploy to staging environment
   - Run full test suite
   - Manual testing of all workflows

### Deployment Steps

**Zero-Downtime Deployment:**

1. **Deploy Code (Phase 1):**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   python manage.py collectstatic --noinput
   ```

2. **Run Migrations:**
   ```bash
   python manage.py migrate teaching
   ```
   - Creates new tables, doesn't modify existing

3. **Restart Application:**
   ```bash
   systemctl restart gunicorn
   ```

4. **Verify:**
   - Public site still works
   - Admin portal accessible at `/admin-portal/`
   - Old support dashboard redirects correctly

5. **Monitor:**
   - Check error logs
   - Monitor database performance
   - Verify emails sending

### Post-Deployment

1. **Create Test Data:**
   - Create sample teacher application
   - Test approval workflow
   - Verify onboarding

2. **Staff Training:**
   - Train support staff on new admin portal
   - Document approval procedures
   - Provide troubleshooting guide

3. **Monitor Metrics:**
   - Application submission rate
   - Approval time (should decrease)
   - Support ticket volume
   - Teacher onboarding completion rate

### Rollback Plan

If critical issues occur:

1. **Quick Rollback (< 5 minutes):**
   ```bash
   git checkout <previous-commit>
   systemctl restart gunicorn
   ```
   - Login redirect goes back to old support dashboard
   - Public site unaffected

2. **Database Rollback (if needed):**
   ```bash
   python manage.py migrate teaching zero
   ```
   - Removes new tables
   - Does not affect existing data

---

## Success Metrics

### Operational Efficiency

**Application Processing:**
- **Current:** 5-10 minutes per application (manual process)
- **Target:** < 2 minutes per application (one-click approval)
- **Measure:** Time from submission to approval

**Admin Workflow:**
- **Current:** Staff use 3+ different interfaces
- **Target:** Single admin portal for all tasks
- **Measure:** Clicks required to complete common tasks

### User Experience

**Teacher Onboarding:**
- **Target:** 80%+ teachers complete onboarding within 7 days
- **Measure:** `TeacherOnboarding.completed_at - TeacherOnboarding.started_at`

**Application Transparency:**
- **Target:** Applicants can track status in real-time
- **Measure:** Support tickets asking "what's my application status" (should decrease)

### Platform Health

**Application Approval Rate:**
- Track monthly approval vs. rejection rate
- Identify trends in application quality

**Teacher Activation:**
- **Target:** 60%+ approved teachers create content within 30 days
- **Measure:** Teachers with ≥1 course/workshop vs. total approved

**Support Ticket Volume:**
- **Target:** Decrease application-related tickets by 80%
- **Measure:** Tickets tagged "teacher application"

### Technical Performance

**Dashboard Load Time:**
- **Target:** < 1 second for admin dashboard
- **Measure:** Server response time

**Email Delivery:**
- **Target:** 99%+ emails delivered within 5 minutes
- **Measure:** Email service logs

---

## Appendix

### A. Admin Portal Wireframes

*(Placeholder for UI mockups)*

### B. Email Templates

*(Placeholder for email template designs)*

### C. User Flow Diagrams

#### Teacher Application Flow

```
Public User
    ↓
Login / Sign Up
    ↓
Visit /teaching/apply/
    ↓
Fill Application Form
    ↓
Submit
    ↓
Confirmation Email Sent
    ↓
Application Status: Pending
    ↓
Admin Receives Alert
    ↓
Admin Reviews in /admin-portal/applications/
    ↓
┌──────────────────────┐
│ Admin Decision       │
├──────────────────────┤
│                      │
│ Approve  │  Reject  │  Request Info
│    ↓     │     ↓    │       ↓
│ is_teacher=True      │  Status: More Info Needed
│ Onboarding Created   │  Email: Rejection
│ Email: Approval      │       ↓
│    ↓                 │  Applicant Responds
│ /teaching/onboarding/│       ↓
│    ↓                 │  Admin Reviews Again
│ Complete 5 Steps     │
│    ↓                 │
│ Teacher Dashboard    │
└──────────────────────┘
```

#### Teacher Onboarding Flow

```
Teacher Application Approved
    ↓
TeacherOnboarding Created
    ↓
Email: Welcome + Onboarding Link
    ↓
Teacher Logs In
    ↓
Redirected to /teaching/onboarding/welcome/
    ↓
Step 1: Welcome (overview, platform benefits)
    ↓
Step 2: Complete Profile (photo, bio, credentials)
    ↓
Step 3: Set Preferences (formats, availability, limits)
    ↓
Step 4: Create Content (optional - can skip)
    ├─ Create Course
    ├─ Create Workshop
    └─ Skip
    ↓
Step 5: Dashboard Tour (interactive guide)
    ↓
Onboarding Complete
    ↓
Redirected to Teacher Dashboard
    ↓
Checklist Widget Hidden
```

### D. Database Schema Diagram

```
┌─────────────────────────────┐
│ auth_user                   │
├─────────────────────────────┤
│ id (PK)                     │
│ username                    │
│ email                       │
│ password                    │
│ is_staff                    │ ──┐
│ is_superuser                │   │
└─────────────────────────────┘   │
        │                          │
        │ 1:1                      │
        ↓                          │
┌─────────────────────────────┐   │
│ accounts_userprofile        │   │
├─────────────────────────────┤   │
│ user_id (FK)                │   │
│ is_student                  │   │
│ is_teacher ◄────────────────┼───┼─── Set TRUE on approval
│ bio                         │   │
│ qualifications              │   │
│ dbs_check_status            │   │
│ ...                         │   │
└─────────────────────────────┘   │
                                   │
┌─────────────────────────────┐   │ reviewed_by
│ teaching_teacherapplication │   │
├─────────────────────────────┤   │
│ id (PK, UUID)               │   │
│ application_number          │   │
│ user_id (FK) ───────────────┼───┘
│ status                      │
│ name                        │
│ email                       │
│ teaching_experience         │
│ qualifications              │
│ dbs_check_status            │
│ reviewed_by_id (FK) ────────┼───┘
│ approved_at                 │
│ ...                         │
└─────────────────────────────┘
        │
        │ 1:1
        ↓
┌─────────────────────────────┐
│ teaching_teacheronboarding  │
├─────────────────────────────┤
│ id (PK, UUID)               │
│ user_id (FK, unique)        │
│ application_id (FK)         │
│ current_step                │
│ welcome_completed           │
│ profile_completed           │
│ preferences_completed       │
│ content_created             │
│ dashboard_tour_completed    │
│ completed                   │
│ ...                         │
└─────────────────────────────┘
```

### E. Permissions Matrix

| Role | Admin Portal | Applications | Users | Content | Payments | Settings | Django Admin |
|------|-------------|--------------|-------|---------|----------|----------|--------------|
| Student | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Teacher | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Staff (Support) | ✅ | ✅ View | ✅ View | ❌ | ❌ | ❌ | ❌ |
| Staff (Moderator) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Superuser | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### F. URL Reference

**Public Site:**
- `/` - Homepage
- `/courses/` - Course catalog
- `/workshops/` - Workshop listing
- `/private-teaching/` - Find teachers
- `/teaching/apply/` - Teacher application form
- `/teaching/application/<uuid>/` - Application status
- `/teaching/onboarding/` - Onboarding wizard

**Teacher Area:**
- `/teacher/dashboard/` - Teacher dashboard
- `/teacher/courses/` - Manage courses
- `/teacher/workshops/` - Manage workshops
- `/teacher/students/` - Student management

**Admin Portal:**
- `/admin-portal/` - Dashboard
- `/admin-portal/support/` - Support tickets
- `/admin-portal/applications/` - Teacher applications
- `/admin-portal/users/` - User management
- `/admin-portal/content/` - Content moderation
- `/admin-portal/payments/` - Financial dashboard
- `/admin-portal/analytics/` - Platform analytics
- `/admin-portal/settings/` - Platform settings

**Django Admin:**
- `/django-admin/` - Technical admin (superuser only)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-XX | Initial | Complete specification document |

---

## Approval

This specification document requires approval before implementation begins.

**Approvers:**
- [ ] Product Owner
- [ ] Lead Developer
- [ ] Platform Manager

**Approved Date:** _______________

---

**END OF SPECIFICATION**
