"""
Teacher application models for managing instructor applications.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class TeacherApplication(models.Model):
    """
    Model for storing teacher/instructor applications with structured data.
    Replaces the old system of storing applications as support tickets.
    """

    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ]

    # DBS check status choices
    DBS_STATUS_CHOICES = [
        ('yes', 'Yes - I have a current DBS check'),
        ('in_progress', 'In progress - I am obtaining one'),
        ('no', 'No - I do not have one'),
        ('equivalent', 'I have an equivalent background check'),
    ]

    # Teaching format choices
    FORMAT_ONLINE = 'online'
    FORMAT_IN_PERSON = 'in_person'
    TEACHING_FORMAT_CHOICES = [
        (FORMAT_ONLINE, 'Online (via Zoom)'),
        (FORMAT_IN_PERSON, 'In-person (at my studio)'),
    ]

    # Core fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_applications',
        help_text='Linked user account if applicant was logged in'
    )
    name = models.CharField(max_length=200, help_text='Full name of applicant')
    email = models.EmailField(help_text='Contact email address')
    phone = models.CharField(max_length=20, blank=True, help_text='Optional phone number')

    # Teaching information
    teaching_biography = models.TextField(
        help_text='Teaching experience, musical background, and approach'
    )
    qualifications = models.TextField(
        help_text='Relevant qualifications, certifications, or professional memberships'
    )
    subjects = models.CharField(
        max_length=500,
        help_text='Instruments or subjects they teach (comma-separated)'
    )

    # Background checks
    dbs_check_status = models.CharField(
        max_length=20,
        choices=DBS_STATUS_CHOICES,
        help_text='DBS/background check status'
    )

    # Teaching preferences
    teaching_formats = models.CharField(
        max_length=100,
        help_text='Preferred teaching formats (comma-separated)'
    )
    availability = models.TextField(
        help_text='General availability for teaching'
    )

    # Terms agreement
    terms_agreed = models.BooleanField(
        default=False,
        help_text='Applicant agreed to platform terms'
    )
    terms_agreed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When terms were agreed to'
    )

    # Application status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text='Current status of the application'
    )

    # Admin fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications',
        help_text='Staff member who reviewed this application'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the application was reviewed'
    )
    admin_notes = models.TextField(
        blank=True,
        help_text='Internal notes from admin review (not visible to applicant)'
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text='Reason for rejection (sent to applicant if rejected)'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Teacher Application'
        verbose_name_plural = 'Teacher Applications'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d')})"

    def approve(self, reviewed_by_user):
        """
        Approve the application and grant teacher status to the user.
        """
        self.status = 'approved'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.save()

        # Grant teacher status to the user if they have an account
        if self.user and hasattr(self.user, 'profile'):
            self.user.profile.is_teacher = True
            self.user.profile.save()

    def reject(self, reviewed_by_user, reason=''):
        """
        Reject the application with an optional reason.
        """
        self.status = 'rejected'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def is_pending(self):
        """Check if application is pending review."""
        return self.status == 'pending'

    def get_teaching_formats_list(self):
        """Return teaching formats as a list."""
        if not self.teaching_formats:
            return []
        return [fmt.strip() for fmt in self.teaching_formats.split(',')]

    def get_subjects_list(self):
        """Return subjects as a list."""
        if not self.subjects:
            return []
        return [subj.strip() for subj in self.subjects.split(',')]
