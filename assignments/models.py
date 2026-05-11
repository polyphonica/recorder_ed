from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field
import os
import uuid


class Tag(models.Model):
    """
    Flexible tagging system for categorizing assignments.
    Examples: 'Scales', 'Rhythm', 'Theory', 'Sight-reading', 'Intervals'
    """
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Assignment Tag'
        verbose_name_plural = 'Assignment Tags'

    def __str__(self):
        return self.name


class Assignment(models.Model):
    """
    Base assignment model - reusable across private lessons and courses
    Supports hybrid notation + written question assignments
    """
    GRADING_SCALE_CHOICES = [
        ('100', '0-100 Points'),
        ('10', '0-10 Points'),
        ('pass_fail', 'Pass/Fail'),
    ]

    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    instructions = models.TextField(help_text="Assignment instructions for students")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_assignments',
        help_text="Teacher who created this assignment"
    )

    # Grading configuration
    grading_scale = models.CharField(
        max_length=20,
        choices=GRADING_SCALE_CHOICES,
        default='100',
        help_text="Grading scale for this assignment"
    )

    # Assignment components
    has_notation_component = models.BooleanField(
        default=True,
        help_text="Whether this assignment includes a music notation component"
    )
    has_written_component = models.BooleanField(
        default=False,
        help_text="Whether this assignment includes a written response component"
    )
    has_attachment_component = models.BooleanField(
        default=False,
        help_text="Student will need to scan/photograph handwritten work and upload it"
    )

    # Categorization and difficulty
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        blank=True,
        help_text="Difficulty level"
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='assignments',
        help_text="Tags for categorization (e.g., Scales, Rhythm, Theory)"
    )

    is_public = models.BooleanField(
        default=False,
        help_text="If checked, assignment appears in library for browsing by other teachers"
    )

    # Optional reference notation (teacher's example/solution)
    reference_notation = models.JSONField(
        null=True,
        blank=True,
        help_text="VexFlow notation data for teacher's reference/example"
    )

    # Optional reference image (alternative to VexFlow notation)
    reference_image = models.ImageField(
        upload_to='assignment_references/',
        null=True,
        blank=True,
        help_text="Upload notation image from Sibelius, Finale, MuseScore, etc. (JPG, PNG, SVG)"
    )

    # Optional printable document (worksheet for students to print off)
    printable_document = models.FileField(
        upload_to='assignment_documents/',
        null=True,
        blank=True,
        help_text="Upload a worksheet or document for students to print and complete (PDF, JPG, PNG)"
    )

    # For future auto-grading
    expected_notation = models.JSONField(
        null=True,
        blank=True,
        help_text="Expected notation answer for auto-grading (future feature)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this assignment is available for assignment"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} (by {self.created_by.get_full_name() or self.created_by.username})"

    def get_max_grade(self):
        """Return the maximum grade value for this assignment's scale"""
        if self.grading_scale == '100':
            return 100
        elif self.grading_scale == '10':
            return 10
        elif self.grading_scale == 'pass_fail':
            return 1  # 1 = Pass, 0 = Fail
        return 100

    def format_grade(self, grade_value):
        """Format a grade value according to this assignment's scale"""
        if grade_value is None:
            return "Not graded"

        if self.grading_scale == 'pass_fail':
            return "Pass" if grade_value >= 1 else "Fail"
        elif self.grading_scale == '10':
            return f"{grade_value}/10"
        else:  # 100
            return f"{grade_value}/100"


class AssignmentSubmission(models.Model):
    """
    Student's submission for an assignment
    Reusable across private lessons and courses
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('feedback_given', 'Feedback Given'),
        ('graded', 'Graded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignment_submissions'
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )

    # Student's work
    notation_data = models.JSONField(
        null=True,
        blank=True,
        help_text="VexFlow notation data created by student"
    )
    written_response = CKEditor5Field(
        config_name='default',
        blank=True,
        null=True,
        help_text="Student's written response with rich text formatting"
    )
    # Deprecated - keeping for backwards compatibility during transition
    written_answers = models.JSONField(
        null=True,
        blank=True,
        help_text="DEPRECATED: Use written_response instead"
    )

    # Submission tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    draft_saved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time draft was saved"
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When student submitted the assignment"
    )

    # Grading
    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Grade out of 100"
    )
    feedback = models.TextField(
        blank=True,
        help_text="Teacher's feedback on the submission"
    )
    graded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When teacher graded the submission"
    )
    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['assignment', 'status']),
        ]
        unique_together = [['student', 'assignment']]

    def __str__(self):
        return f"{self.assignment.title} - {self.student.get_full_name() or self.student.username} ({self.status})"

    def submit(self):
        """Mark submission as submitted"""
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()

    def save_draft(self):
        """Save current work as draft"""
        self.status = 'draft'
        self.draft_saved_at = timezone.now()
        self.save()

    def grade_submission(self, grade, feedback, graded_by):
        """Grade the submission"""
        self.grade = grade
        self.feedback = feedback
        self.graded_by = graded_by
        self.graded_at = timezone.now()
        self.status = 'graded'
        self.save()

    def give_feedback(self, feedback_text, given_by):
        """Teacher gives interim feedback without grading; returns the FeedbackRound."""
        round_number = self.rounds.count() + 1
        feedback_round = FeedbackRound.objects.create(
            submission=self,
            round_number=round_number,
            teacher_feedback=feedback_text,
            given_by=given_by,
        )
        self.status = 'feedback_given'
        self.save()
        return feedback_round

    @property
    def current_round_number(self):
        """The round number for attachments being added right now."""
        return self.rounds.count() + 1

    def get_formatted_grade(self):
        """Get the formatted grade according to the assignment's scale"""
        return self.assignment.format_grade(self.grade)


class FeedbackRound(models.Model):
    """
    Records one round of teacher interim feedback before final grading.
    Round N is created when the teacher gives feedback after the student's Nth submission.
    """
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='rounds'
    )
    round_number = models.PositiveIntegerField()
    teacher_feedback = models.TextField(blank=True)
    given_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='given_feedback_rounds'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['round_number']
        unique_together = [['submission', 'round_number']]

    def __str__(self):
        return f"Round {self.round_number} feedback for {self.submission}"


def _submission_attachment_path(instance, filename):
    return f'submission_attachments/{instance.submission.pk}/{filename}'


class SubmissionAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=_submission_attachment_path)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submission_attachments'
    )
    round_number = models.PositiveIntegerField(default=1)
    label = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment by {self.uploaded_by.username} on {self.submission}"

    @property
    def is_image(self):
        return self.file.name.lower().endswith(('.jpg', '.jpeg', '.png'))

    @property
    def is_pdf(self):
        return self.file.name.lower().endswith('.pdf')

    @property
    def filename(self):
        return os.path.basename(self.file.name)
