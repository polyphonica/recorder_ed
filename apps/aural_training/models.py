from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class StudentIntervalProgress(models.Model):
    """
    Tracks progress for each interval for a student.
    """
    INTERVAL_CHOICES = [
        ('m2', 'Minor 2nd'),
        ('M2', 'Major 2nd'),
        ('m3', 'Minor 3rd'),
        ('M3', 'Major 3rd'),
        ('P4', 'Perfect 4th'),
        ('P5', 'Perfect 5th'),
        ('m6', 'Minor 6th'),
        ('M6', 'Major 6th'),
        ('m7', 'Minor 7th'),
        ('M7', 'Major 7th'),
        ('P8', 'Octave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='interval_progress',
        help_text="Student tracking progress"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interval_progress',
        help_text="If progress is for a child"
    )

    interval = models.CharField(
        max_length=3,
        choices=INTERVAL_CHOICES,
        help_text="The interval being tracked"
    )

    attempts = models.PositiveIntegerField(default=0)
    correct = models.PositiveIntegerField(default=0)
    unlocked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def accuracy(self):
        """Calculate accuracy percentage"""
        if self.attempts == 0:
            return 0
        return round((self.correct / self.attempts) * 100)

    @property
    def is_mastered(self):
        """Check if interval is mastered (80%+ with 5+ attempts)"""
        return self.accuracy >= 80 and self.attempts >= 5

    class Meta:
        verbose_name = 'Student Interval Progress'
        verbose_name_plural = 'Student Interval Progress'
        unique_together = ['student', 'child_profile', 'interval']
        indexes = [
            models.Index(fields=['student', 'interval']),
            models.Index(fields=['child_profile', 'interval']),
        ]

    def __str__(self):
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        return f"{student_name} - {self.get_interval_display()} ({self.accuracy}%)"


class AuralTrainingSession(models.Model):
    """
    Records individual training sessions.
    Allows teachers to see when students practiced and their performance.
    """
    MODE_CHOICES = [
        ('training', 'Training Mode'),
        ('drill', 'Drill Mode'),
        ('explore', 'Explore Mode'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='aural_training_sessions',
        help_text="Student who completed the session"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aural_training_sessions',
        help_text="If session is for a child"
    )

    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default='training'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    questions_attempted = models.PositiveIntegerField(default=0)
    questions_correct = models.PositiveIntegerField(default=0)
    highest_streak = models.PositiveIntegerField(default=0)
    current_level = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(7)]
    )

    @property
    def duration_minutes(self):
        """Calculate session duration in minutes"""
        if not self.ended_at:
            return None
        delta = self.ended_at - self.started_at
        return round(delta.total_seconds() / 60)

    @property
    def accuracy(self):
        """Calculate session accuracy percentage"""
        if self.questions_attempted == 0:
            return 0
        return round((self.questions_correct / self.questions_attempted) * 100)

    class Meta:
        verbose_name = 'Aural Training Session'
        verbose_name_plural = 'Aural Training Sessions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student', '-started_at']),
            models.Index(fields=['child_profile', '-started_at']),
        ]

    def __str__(self):
        student_name = self.child_profile.full_name if self.child_profile else self.student.get_full_name()
        return f"{student_name} - {self.get_mode_display()} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
