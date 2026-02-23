from django.db import models
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
