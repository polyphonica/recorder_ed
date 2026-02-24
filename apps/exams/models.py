from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
import uuid

from apps.core.models import PayableModel
from simple_history.models import HistoricalRecords

User = get_user_model()


class ExamBoard(models.Model):
    """Examination boards that provide graded music exams"""

    ABRSM = 'abrsm'
    TRINITY = 'trinity'
    MTB = 'mtb'

    BOARD_CHOICES = [
        (ABRSM, 'ABRSM (Associated Board of the Royal Schools of Music)'),
        (TRINITY, 'Trinity College London'),
        (MTB, "Music Teachers' Board"),
    ]

    name = models.CharField(
        max_length=50,
        choices=BOARD_CHOICES,
        unique=True,
        help_text="Examination board name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the examination board"
    )
    website = models.URLField(
        blank=True,
        help_text="Official website URL"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this board is currently available for selection"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Examination Board'
        verbose_name_plural = 'Examination Boards'
        db_table = 'private_teaching_examboard'

    def __str__(self):
        return self.get_name_display()


class ExamRegistration(PayableModel):
    """
    Registration for a music examination.

    Supports both adult students and children (under 18).
    Inherits payment and child profile fields from PayableModel.
    """

    PRACTICAL = 'practical'
    PERFORMANCE = 'performance'
    THEORY = 'theory'

    GRADE_TYPE_CHOICES = [
        (PRACTICAL, 'Practical Grade'),
        (PERFORMANCE, 'Performance Grade'),
        (THEORY, 'Music Theory'),
    ]

    REGISTERED = 'registered'
    SUBMITTED = 'submitted'
    RESULTS_RECEIVED = 'results_received'

    STATUS_CHOICES = [
        (REGISTERED, 'Registered'),
        (SUBMITTED, 'Exam Submitted'),
        (RESULTS_RECEIVED, 'Results Received'),
    ]

    PASS = 'pass'
    MERIT = 'merit'
    DISTINCTION = 'distinction'
    FAIL = 'fail'

    GRADE_ACHIEVED_CHOICES = [
        (PASS, 'Pass'),
        (MERIT, 'Merit'),
        (DISTINCTION, 'Distinction'),
        (FAIL, 'Fail'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_registrations',
        help_text="For adults: the student. For children: the guardian/parent."
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_exam_registrations',
        help_text="Teacher registering the student for the exam"
    )
    subject = models.ForeignKey(
        'private_teaching.Subject',
        on_delete=models.CASCADE,
        related_name='exam_registrations',
        help_text="Subject/instrument for the exam"
    )
    exam_board = models.ForeignKey(
        ExamBoard,
        on_delete=models.PROTECT,
        related_name='exam_registrations',
        help_text="Examination board"
    )

    grade_type = models.CharField(
        max_length=20,
        choices=GRADE_TYPE_CHOICES,
        help_text="Type of exam (Practical, Performance, or Theory)"
    )
    grade_level = models.PositiveIntegerField(
        help_text="Grade level (1-8 for Practical/Performance, 1-6 for Theory)"
    )
    exam_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the exam"
    )
    submission_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for submitting recordings/videos"
    )
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Registration number from the exam board"
    )
    venue = models.CharField(
        max_length=200,
        blank=True,
        help_text="Exam venue or submission method"
    )
    scales = models.TextField(
        blank=True,
        help_text="Required scales"
    )
    arpeggios = models.TextField(
        blank=True,
        help_text="Required arpeggios"
    )
    sight_reading = models.TextField(
        blank=True,
        help_text="Sight reading requirements or notes"
    )
    aural_tests = models.TextField(
        blank=True,
        help_text="Aural test requirements or notes"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=REGISTERED,
        help_text="Current exam status"
    )
    mark_achieved = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Numerical mark achieved"
    )
    grade_achieved = models.CharField(
        max_length=20,
        choices=GRADE_ACHIEVED_CHOICES,
        blank=True,
        help_text="Grade achieved"
    )
    examiner_comments = models.TextField(
        blank=True,
        help_text="Comments from the examiner"
    )
    certificate_received_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when certificate was received"
    )
    teacher_notes = models.TextField(
        blank=True,
        help_text="Private teacher notes about this exam"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-exam_date', '-created_at']
        verbose_name = 'Exam Registration'
        verbose_name_plural = 'Exam Registrations'
        db_table = 'private_teaching_examregistration'
        indexes = [
            models.Index(fields=['teacher', 'exam_date']),
            models.Index(fields=['student', 'exam_date']),
            models.Index(fields=['exam_board', 'grade_type', 'grade_level']),
        ]

    def __str__(self):
        student_name = self.student_name
        grade_display = f"{self.get_grade_type_display()} Grade {self.grade_level}"
        return f"{student_name} - {self.exam_board} {grade_display}"

    def clean(self):
        super().clean()
        if self.grade_type == self.THEORY:
            if self.grade_level < 1 or self.grade_level > 6:
                raise ValidationError({'grade_level': 'Theory grades must be between 1 and 6'})
        else:
            if self.grade_level < 1 or self.grade_level > 8:
                raise ValidationError({'grade_level': 'Practical and Performance grades must be between 1 and 8'})

    def get_absolute_url(self):
        return reverse('exams:exam_detail', kwargs={'pk': self.id})

    @property
    def display_name(self):
        return f"{self.exam_board} {self.get_grade_type_display()} Grade {self.grade_level}"

    @property
    def has_results(self):
        return self.status == self.RESULTS_RECEIVED and (
            self.mark_achieved is not None or self.grade_achieved
        )


class ExamPiece(models.Model):
    """Individual piece selected for an exam."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_registration = models.ForeignKey(
        ExamRegistration,
        on_delete=models.CASCADE,
        related_name='pieces',
        help_text="Exam registration this piece belongs to"
    )
    piece_number = models.PositiveIntegerField(
        help_text="Piece number in the exam (1, 2, 3, 4, etc.)"
    )
    title = models.CharField(max_length=200, help_text="Title of the piece")
    composer = models.CharField(max_length=200, help_text="Composer name")
    syllabus_list = models.CharField(
        max_length=50,
        blank=True,
        help_text="Syllabus list (e.g., 'A', 'B', 'C', 'Own Choice')"
    )
    playalong_piece = models.ForeignKey(
        'audioplayer.Piece',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_pieces',
        help_text="Link to playalong piece for practice"
    )
    teacher_notes = models.TextField(
        blank=True,
        help_text="Teacher notes about practice progress or readiness"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['piece_number']
        verbose_name = 'Exam Piece'
        verbose_name_plural = 'Exam Pieces'
        db_table = 'private_teaching_exampiece'
        unique_together = ['exam_registration', 'piece_number']
        indexes = [
            models.Index(fields=['exam_registration', 'piece_number']),
        ]

    def __str__(self):
        return f"Piece {self.piece_number}: {self.title} by {self.composer}"
