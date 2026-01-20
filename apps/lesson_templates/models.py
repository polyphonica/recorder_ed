from django.db import models
from django.contrib.auth.models import User
from django_ckeditor_5.fields import CKEditor5Field
import uuid


class TemplateCategory(models.Model):
    """
    Categories for organizing lesson templates into independent series/courses.
    Each category has its own lesson numbering scope.
    Examples: "Rhythm Fundamentals", "ABRSM Grade 1 Theory", "Repertoire Notes"
    """
    SYLLABUS_CHOICES = [
        ('abrsm', 'ABRSM'),
        ('trinity', 'Trinity College'),
        ('rcm', 'RCM'),
        ('mtb', 'Music Teachers Board'),
        ('custom', 'Custom'),
    ]

    # Color choices for UI badges
    COLOR_CHOICES = [
        ('#6366f1', 'Indigo'),
        ('#8b5cf6', 'Purple'),
        ('#ec4899', 'Pink'),
        ('#ef4444', 'Red'),
        ('#f97316', 'Orange'),
        ('#eab308', 'Yellow'),
        ('#22c55e', 'Green'),
        ('#14b8a6', 'Teal'),
        ('#3b82f6', 'Blue'),
        ('#64748b', 'Slate'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Information
    name = models.CharField(
        max_length=100,
        help_text="Category name (e.g., 'Rhythm Fundamentals', 'ABRSM Grade 1 Theory')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of what this category covers"
    )

    # Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_categories',
        help_text="Teacher who created this category"
    )

    # Optional categorization - can be left blank for generic categories
    subject = models.ForeignKey(
        'private_teaching.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional: Link to a specific subject/instrument"
    )
    syllabus = models.CharField(
        max_length=50,
        choices=SYLLABUS_CHOICES,
        blank=True,
        help_text="Optional: Examination board or syllabus"
    )
    grade_level = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional: Grade level (e.g., '1', '2', 'Beginner')"
    )

    # Display
    color = models.CharField(
        max_length=7,
        choices=COLOR_CHOICES,
        default='#6366f1',
        help_text="Color for category badge in UI"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order in which categories are displayed (lower numbers first)"
    )

    # Sharing
    is_public = models.BooleanField(
        default=False,
        help_text="If checked, other teachers can see this category (templates have independent visibility)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Template Category'
        verbose_name_plural = 'Template Categories'
        indexes = [
            models.Index(fields=['created_by', 'display_order']),
            models.Index(fields=['is_public']),
        ]

    def __str__(self):
        return self.name

    @property
    def template_count(self):
        """Number of templates in this category"""
        return self.templates.count()


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
        ('mtb', 'Music Teachers Board'),
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

    # Category - allows independent numbering per category
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        help_text="Category/series this template belongs to (lesson numbers are scoped within category)"
    )

    # Categorization (kept for backward compatibility and standalone templates)
    subject = models.ForeignKey(
        'private_teaching.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Subject this template is for (can also be set on category)"
    )
    syllabus = models.CharField(
        max_length=50,
        choices=SYLLABUS_CHOICES,
        blank=True,
        help_text="Syllabus/examination board (can also be set on category)"
    )
    grade_level = models.CharField(
        max_length=10,
        blank=True,
        help_text="Grade level (e.g., '1', '2', 'Beginner', 'Intermediate')"
    )
    lesson_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Position in course sequence within this category (1, 2, 3, etc.)"
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
        ordering = ['category', 'lesson_number', 'syllabus', 'grade_level', 'title']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['syllabus', 'grade_level', 'lesson_number']),
            models.Index(fields=['is_public']),
            models.Index(fields=['category', 'lesson_number']),
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
