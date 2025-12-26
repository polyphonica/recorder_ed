from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Assignment(models.Model):
    """
    Base assignment model - reusable across private lessons and courses
    Supports hybrid notation + written question assignments
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    instructions = models.TextField(help_text="Assignment instructions for students")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_assignments',
        help_text="Teacher who created this assignment"
    )

    # Assignment components
    has_notation_component = models.BooleanField(
        default=True,
        help_text="Whether this assignment includes a music notation component"
    )
    has_written_component = models.BooleanField(
        default=False,
        help_text="Whether this assignment includes written questions"
    )
    written_questions = models.JSONField(
        null=True,
        blank=True,
        help_text="Array of written questions: [{question: 'text', type: 'short'|'long'}]"
    )

    # Optional reference notation (teacher's example/solution)
    reference_notation = models.JSONField(
        null=True,
        blank=True,
        help_text="VexFlow notation data for teacher's reference/example"
    )

    # For future auto-grading
    expected_notation = models.JSONField(
        null=True,
        blank=True,
        help_text="Expected notation answer for auto-grading (future feature)"
    )
    expected_written_answers = models.JSONField(
        null=True,
        blank=True,
        help_text="Expected written answers for auto-grading (future feature)"
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


class AssignmentSubmission(models.Model):
    """
    Student's submission for an assignment
    Reusable across private lessons and courses
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
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
    written_answers = models.JSONField(
        null=True,
        blank=True,
        help_text="Student's written answers: [{question_index: 0, answer: 'text'}]"
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
