import uuid
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class SightReadingExample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    grade_level = models.CharField(max_length=50, blank=True, help_text="e.g. '1', 'Beginner'")
    image = models.ImageField(upload_to='sight_reading/examples/')
    teacher_notes = models.TextField(blank=True, help_text='Private notes about this example (teacher only)')
    is_public = models.BooleanField(default=False, help_text='Visible to all teachers in the library')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sight_reading_examples')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'grade_level']),
            models.Index(fields=['is_public', 'grade_level']),
        ]

    def __str__(self):
        return self.title


class SightReadingSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    grade_level = models.CharField(max_length=50, blank=True)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sight_reading_sets')
    examples = models.ManyToManyField(SightReadingExample, through='SightReadingSetItem', related_name='sets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def example_count(self):
        return self.items.count()


class SightReadingSetItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    set = models.ForeignKey(SightReadingSet, on_delete=models.CASCADE, related_name='items')
    example = models.ForeignKey(SightReadingExample, on_delete=models.CASCADE, related_name='set_items')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ['set', 'example']
        indexes = [
            models.Index(fields=['set', 'order']),
        ]

    def __str__(self):
        return f'{self.set.name} – {self.example.title} (#{self.order})'


class SightReadingAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sight_reading_set = models.ForeignKey(SightReadingSet, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sight_reading_assignments_received')
    child_profile = models.ForeignKey(
        'accounts.ChildProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sight_reading_assignments',
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sight_reading_assignments_given')
    lesson = models.ForeignKey(
        'lessons.Lesson', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sight_reading_assignments',
    )
    is_unlocked = models.BooleanField(default=False)
    needs_repeat = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['teacher', 'needs_repeat']),
            models.Index(fields=['student', 'is_unlocked']),
        ]

    def __str__(self):
        return f'{self.sight_reading_set.name} → {self.student_display}'

    @property
    def student_display(self):
        if self.child_profile:
            return self.child_profile.full_name
        return self.student.get_full_name() or self.student.username

    @property
    def is_completed(self):
        return self.completed_at is not None


class SightReadingResult(models.Model):
    RESULT_CHOICES = [
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(SightReadingAssignment, on_delete=models.CASCADE, related_name='results')
    example = models.ForeignKey(SightReadingExample, on_delete=models.CASCADE, related_name='results')
    order = models.PositiveIntegerField()
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, null=True, blank=True)
    teacher_note = models.TextField(blank=True)
    played_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']
        unique_together = ['assignment', 'example']
        indexes = [
            models.Index(fields=['assignment', 'order']),
        ]

    def __str__(self):
        return f'{self.assignment} – {self.example.title} ({self.result or "ungraded"})'
