from django.db import models
from django.contrib.auth.models import User
from django_ckeditor_5.fields import CKEditor5Field
import uuid


class Tag(models.Model):
    """
    Tags for categorizing lesson content templates.
    Examples: 'Scales', 'Theory', 'Notation', 'Rhythm', 'Sight-reading'
    """
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Lesson Template Tag'
        verbose_name_plural = 'Lesson Template Tags'

    def __str__(self):
        return self.name


class LessonContentTemplate(models.Model):
    """
    Reusable lesson content templates
    Teachers can create templates for common lesson types and reuse them across students
    """
    SYLLABUS_CHOICES = [
        ('abrsm', 'ABRSM'),
        ('trinity', 'Trinity College'),
        ('rcm', 'RCM'),
        ('custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Information
    title = models.CharField(
        max_length=200,
        help_text="Template title (e.g., 'ABRSM Grade 1 - Lesson 1: Introduction to Notation')"
    )
    content = CKEditor5Field(
        config_name='default',
        help_text="Lesson content with rich text formatting"
    )

    # Categorization
    subject = models.ForeignKey(
        'private_teaching.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Subject this template is for"
    )
    syllabus = models.CharField(
        max_length=50,
        choices=SYLLABUS_CHOICES,
        blank=True,
        help_text="Syllabus/examination board"
    )
    grade_level = models.CharField(
        max_length=10,
        blank=True,
        help_text="Grade level (e.g., '1', '2', 'Beginner', 'Intermediate')"
    )
    lesson_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Position in course sequence (1-12, etc.)"
    )

    # Tagging
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='templates',
        help_text="Tags for categorization (e.g., Scales, Rhythm, Theory)"
    )

    # Sharing
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_lesson_templates',
        help_text="Teacher who created this template"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="If checked, other teachers can browse and use this template"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    use_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )

    class Meta:
        ordering = ['syllabus', 'grade_level', 'lesson_number', 'title']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['syllabus', 'grade_level', 'lesson_number']),
            models.Index(fields=['is_public']),
        ]
        verbose_name = 'Lesson Content Template'
        verbose_name_plural = 'Lesson Content Templates'

    def __str__(self):
        parts = []
        if self.syllabus:
            parts.append(self.get_syllabus_display())
        if self.grade_level:
            parts.append(f"Grade {self.grade_level}")
        if self.lesson_number:
            parts.append(f"Lesson {self.lesson_number}")
        if parts:
            return f"{' - '.join(parts)}: {self.title}"
        return self.title

    def increment_use_count(self):
        """Increment the use count when template is used"""
        self.use_count += 1
        self.save(update_fields=['use_count'])
