import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class PracticeEntry(models.Model):
    """
    Practice diary entries for private lesson students.
    Helps students track practice and teachers monitor progress.
    Especially valuable for exam preparation and recital preparation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='practice_entries',
        help_text="Student who practiced (adult or guardian for child)"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='practice_entries',
        help_text="If practicing for a child's lessons"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_practice_entries',
        help_text="Teacher who can view this practice entry"
    )
    lesson_request = models.ForeignKey(
        'private_teaching.LessonRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='practice_entries',
        help_text="Associated lesson request/relationship"
    )

    # Practice Details
    practice_date = models.DateField(
        help_text="Date of practice session"
    )
    duration_minutes = models.PositiveIntegerField(
        help_text="How long practiced (in minutes)"
    )

    # What was practiced
    pieces_practiced = models.TextField(
        blank=True,
        help_text="Pieces/songs worked on (e.g., 'Sonata in F, Scales: G Major, A Minor')"
    )
    exercises_practiced = models.TextField(
        blank=True,
        help_text="Technical exercises (e.g., 'Long tones, Tonguing exercises')"
    )

    # Reflections
    focus_areas = models.TextField(
        blank=True,
        help_text="What you focused on (e.g., 'Worked on tricky section bars 12-16')"
    )
    struggles = models.TextField(
        blank=True,
        help_text="Difficulties encountered (optional)"
    )
    achievements = models.TextField(
        blank=True,
        help_text="Breakthroughs or improvements (optional)"
    )

    # Optional ratings
    enjoyment_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, '1 - Not enjoyable'), (2, '2'), (3, '3'), (4, '4'), (5, '5 - Very enjoyable')],
        help_text="How enjoyable was this practice session?"
    )

    # Exam/Performance preparation flag
    preparing_for_exam = models.BooleanField(
        default=False,
        help_text="Check if practicing for an upcoming exam"
    )
    preparing_for_performance = models.BooleanField(
        default=False,
        help_text="Check if practicing for a recital or performance"
    )

    # Teacher interaction
    teacher_comment = models.TextField(
        blank=True,
        help_text="Teacher's comment on this practice session (optional)"
    )
    teacher_viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When teacher viewed this entry"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-practice_date', '-created_at']
        verbose_name = 'Practice Entry'
        verbose_name_plural = 'Practice Entries'
        db_table = 'private_teaching_practiceentry'
        indexes = [
            models.Index(fields=['student', '-practice_date'], name='private_tea_student_11a599_idx'),
            models.Index(fields=['teacher', '-practice_date'], name='private_tea_teacher_1cef4c_idx'),
        ]

    def __str__(self):
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        return f"{student_name} - {self.practice_date} ({self.duration_minutes} min)"

    @property
    def practicing_student_name(self):
        """Return the name of who actually practiced"""
        if self.child_profile:
            return self.child_profile.full_name
        return self.student.get_full_name() or self.student.username

    @property
    def has_reflections(self):
        """Check if student added any reflections"""
        return bool(self.focus_areas or self.struggles or self.achievements)

    @property
    def preparation_type(self):
        """Return what this practice is preparing for"""
        types = []
        if self.preparing_for_exam:
            types.append('Exam')
        if self.preparing_for_performance:
            types.append('Performance')
        return ', '.join(types) if types else None


# ---------------------------------------------------------------------------
# Practice clips: short recordings a student shares for teacher feedback
# ---------------------------------------------------------------------------

class PrivateMediaStorage(FileSystemStorage):
    """Files that must never be publicly served (outside MEDIA_ROOT).

    Reads PRIVATE_MEDIA_ROOT each time, so it follows settings overrides.
    No public URL: files are served by permission-checked views only.
    """

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise NotImplementedError("Private files have no public URL")


def private_storage():
    """A callable so migrations don't capture the server's path."""
    return PrivateMediaStorage()


def clip_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()[:6] or '.bin'
    owner = instance.uploaded_by_id or 'unknown'
    return f'practice_clips/{owner}/{uuid.uuid4()}{ext}'


def reply_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()[:6] or '.bin'
    return f'practice_clip_replies/{instance.clip_id}/{uuid.uuid4()}{ext}'


class AudioStatus(models.TextChoices):
    NONE = 'none', 'No audio'
    PROCESSING = 'processing', 'Processing'
    READY = 'ready', 'Ready'
    FAILED = 'failed', 'Failed'


class PracticeClip(models.Model):
    """A short recording attached to a practice entry, for teacher feedback.

    While a student is still filling in Log practice, the clip has no entry
    yet ("pending") and belongs to `uploaded_by`.
    """

    class Kind(models.TextChoices):
        PIECE = 'piece', 'Piece'
        SCALE = 'scale', 'Scale'
        EXERCISE = 'exercise', 'Exercise'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(
        PracticeEntry, on_delete=models.CASCADE, related_name='clips',
        null=True, blank=True,
        help_text="Empty while pending (uploaded on Log practice, entry not yet saved)",
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='practice_clips',
    )

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PIECE)
    title = models.CharField(max_length=200)
    note = models.TextField(blank=True, help_text="What the student wants help with")

    original_file = models.FileField(storage=private_storage, upload_to=clip_upload_path, blank=True)
    audio_file = models.FileField(storage=private_storage, upload_to=clip_upload_path, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=AudioStatus.choices, default=AudioStatus.PROCESSING)
    failure_reason = models.CharField(max_length=200, blank=True)

    teacher_listened_at = models.DateTimeField(null=True, blank=True)
    teacher_notified_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True, help_text="Teacher replied or marked done")
    keep = models.BooleanField(default=False, help_text="Exempt from automatic deletion")
    last_activity_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['resolved_at', 'created_at']),
            models.Index(fields=['keep', 'last_activity_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_pending(self):
        return self.entry_id is None


class PracticeClipReply(models.Model):
    """A message in a clip's thread: a teacher reply or a student follow-up."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clip = models.ForeignKey(PracticeClip, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='practice_clip_replies')
    from_teacher = models.BooleanField(default=True)
    text = models.TextField(blank=True)

    original_file = models.FileField(storage=private_storage, upload_to=reply_upload_path, blank=True)
    audio_file = models.FileField(storage=private_storage, upload_to=reply_upload_path, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=AudioStatus.choices, default=AudioStatus.NONE)
    failure_reason = models.CharField(max_length=200, blank=True)

    read_at = models.DateTimeField(null=True, blank=True, help_text="When the other party opened it")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.CheckConstraint(
                # Text, or audio (processing, ready, or failed and shown as such)
                condition=~models.Q(text='') | ~models.Q(status='none'),
                name='practice_clip_reply_has_content',
            ),
        ]

    def __str__(self):
        return f"Reply to {self.clip}"

    @property
    def is_visible(self):
        """Text replies show at once; audio replies once processed (text still shows)."""
        return bool(self.text) or self.status == AudioStatus.READY
