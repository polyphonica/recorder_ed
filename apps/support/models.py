import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class Ticket(models.Model):
    """
    Support ticket for platform-level issues and inquiries.
    Can be created by authenticated users or anonymous visitors.
    """

    CATEGORY_CHOICES = [
        ('teacher_application', 'Teacher Application'),
        ('payment', 'Payment Issue'),
        ('technical', 'Technical Support'),
        ('general', 'General Inquiry'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_user', 'Waiting for User'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False, db_index=True)

    # User (nullable for anonymous tickets)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
        help_text="User who created the ticket (null for anonymous)"
    )

    # Anonymous user details (for public form)
    email = models.EmailField(help_text="Contact email")
    name = models.CharField(max_length=200, help_text="Full name")

    # Ticket details
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)

    subject = models.CharField(max_length=300)
    description = models.TextField()

    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        help_text="Staff member assigned to this ticket"
    )

    # SLA and response tracking
    first_response_at = models.DateTimeField(null=True, blank=True, help_text="When staff first replied")
    last_response_at = models.DateTimeField(null=True, blank=True, help_text="Last staff response time")
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):
        # Generate ticket number if not set
        if not self.ticket_number:
            # Get last ticket number
            last_ticket = Ticket.objects.order_by('-created_at').first()
            if last_ticket and last_ticket.ticket_number:
                # Extract number from last ticket (e.g., TICKET-001234)
                last_number = int(last_ticket.ticket_number.split('-')[1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.ticket_number = f"TICKET-{new_number:06d}"

        # Auto-fill email/name from user if authenticated
        if self.user and not self.email:
            self.email = self.user.email
        if self.user and not self.name:
            self.name = self.user.get_full_name() or self.user.username

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('support:ticket_detail', kwargs={'ticket_number': self.ticket_number})

    @property
    def time_to_first_response(self):
        """Calculate time from creation to first staff response"""
        if self.first_response_at:
            delta = self.first_response_at - self.created_at
            return delta
        return None

    @property
    def time_to_resolution(self):
        """Calculate time from creation to resolution"""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
            return delta
        return None

    @property
    def age(self):
        """How long since ticket was created"""
        return timezone.now() - self.created_at

    @property
    def is_overdue(self):
        """Check if ticket is overdue based on priority (simple SLA)"""
        if self.status in ['resolved', 'closed']:
            return False

        age_hours = self.age.total_seconds() / 3600

        # SLA thresholds in hours
        sla_thresholds = {
            'urgent': 4,    # 4 hours
            'high': 24,     # 1 day
            'normal': 48,   # 2 days
            'low': 72,      # 3 days
        }

        threshold = sla_thresholds.get(self.priority, 48)
        return age_hours > threshold


class TicketMessage(models.Model):
    """
    Message/reply within a support ticket.
    Can be from user or staff. Staff can also add internal notes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')

    # Author
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    author_email = models.EmailField(blank=True, help_text="For anonymous replies")
    author_name = models.CharField(max_length=200, blank=True, help_text="For anonymous replies")

    # Message content
    message = models.TextField()

    # Message type
    is_staff_reply = models.BooleanField(default=False)
    is_internal_note = models.BooleanField(
        default=False,
        help_text="Internal staff note (not visible to user)"
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        author = self.author.get_full_name() if self.author else self.author_name
        msg_type = "Internal Note" if self.is_internal_note else "Staff Reply" if self.is_staff_reply else "User Reply"
        return f"{self.ticket.ticket_number} - {msg_type} by {author}"

    def save(self, *args, **kwargs):
        # Update ticket's first/last response times if this is a staff reply
        if self.is_staff_reply and not self.is_internal_note:
            if not self.ticket.first_response_at:
                self.ticket.first_response_at = timezone.now()
            self.ticket.last_response_at = timezone.now()
            self.ticket.save()

        super().save(*args, **kwargs)


class TicketAttachment(models.Model):
    """File attachment for a ticket"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='support/attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.filename}"
