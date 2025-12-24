from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django_ckeditor_5.fields import CKEditor5Field
from apps.core.validators import (
    AUDIO_VALIDATORS,
    SHEET_MUSIC_IMAGE_VALIDATORS,
    SHEET_MUSIC_PDF_VALIDATORS,
)


class Composer(models.Model):
    """
    Normalized composer/artist entity to avoid duplication and enable filtering.
    """
    name = models.CharField(max_length=200, unique=True)
    dates = models.CharField(
        max_length=100,
        blank=True,
        help_text="Birth and death dates (e.g., '1685-1750' or 'c.1547 - c.1601')"
    )
    bio = CKEditor5Field(
        'biography',
        config_name='default',
        blank=True,
        help_text="Biographical information with formatting (paragraphs, lists, links, etc.)"
    )
    period = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., Baroque, Classical, Romantic, Traditional, Contemporary"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Composer'
        verbose_name_plural = 'Composers'

    def __str__(self):
        return self.name


class Tag(models.Model):
    """
    Flexible tagging system for categorizing pieces beyond standard fields.
    Examples: 'Christmas', 'Halloween', 'Duet', 'Fast Tempo', 'Solo'
    """
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Piece(models.Model):
    """
    A playalong piece with title, optional sheet music, and metadata for library organization.
    Reusable across multiple lessons.
    """

    GRADE_CHOICES = [
        ('N/A', 'N/A'),
        ('grade_1', 'Grade 1'),
        ('grade_2', 'Grade 2'),
        ('grade_3', 'Grade 3'),
        ('grade_4', 'Grade 4'),
        ('grade_5', 'Grade 5'),
        ('grade_6', 'Grade 6'),
        ('grade_7', 'Grade 7'),
        ('grade_8', 'Grade 8'),
    ]

    GENRE_CHOICES = [
        ('classical', 'Classical'),
        ('folk', 'Folk/Traditional'),
        ('pop', 'Popular'),
        ('jazz', 'Jazz'),
        ('baroque', 'Baroque'),
        ('renaissance', 'Renaissance'),
        ('contemporary', 'Contemporary'),
        ('other', 'Other'),
    ]

    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    # Basic fields
    title = models.CharField(max_length=200)
    svg_image = models.FileField(
        upload_to='audioplayer/svg_images/',
        null=True,
        blank=True,
        validators=SHEET_MUSIC_IMAGE_VALIDATORS,
        help_text="Sheet music or notation image (SVG/PNG/JPG) for on-screen display (max 5MB)"
    )

    pdf_score = models.FileField(
        upload_to='audioplayer/pdf_scores/',
        null=True,
        blank=True,
        validators=SHEET_MUSIC_PDF_VALIDATORS,
        help_text="Printable PDF version of the score (max 5MB)"
    )

    pdf_score_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descriptive title for the PDF score (e.g., 'Full Score with Piano Accompaniment')"
    )

    # Metadata fields (all optional to avoid errors with existing data)
    composer = models.ForeignKey(
        Composer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces',
        help_text="Composer or artist"
    )

    grade_level = models.CharField(
        max_length=20,
        choices=GRADE_CHOICES,
        blank=True,
        default='N/A',
        help_text="Associated exam grade level (optional)"
    )

    genre = models.CharField(
        max_length=50,
        choices=GENRE_CHOICES,
        blank=True,
        help_text="Musical genre or style"
    )

    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        blank=True,
        help_text="Difficulty level"
    )

    description = models.TextField(
        blank=True,
        help_text="Notes about the piece, performance tips, or context"
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='pieces',
        help_text="Additional categorization (e.g., Christmas, Duet, etc.)"
    )

    is_public = models.BooleanField(
        default=True,
        help_text="If checked, piece appears in library for all students to browse"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_pieces',
        help_text="Teacher who created this piece"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Playalong Piece'
        verbose_name_plural = 'Playalong Pieces'

    def __str__(self):
        return self.title


class Stem(models.Model):
    """
    Individual audio track (instrument) within a piece.
    Each piece can have multiple stems that play simultaneously.
    """
    piece = models.ForeignKey(
        Piece,
        related_name='stems',
        on_delete=models.CASCADE
    )
    instrument_name = models.CharField(
        max_length=100,
        help_text="e.g., Piano, Metronome, Backing Track, Recorder"
    )
    audio_file = models.FileField(
        upload_to='audioplayer/stems/',
        validators=AUDIO_VALIDATORS,
        help_text="MP3 or WAV audio file (max 10MB)"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'instrument_name']
        verbose_name = 'Audio Stem'
        verbose_name_plural = 'Audio Stems'

    def __str__(self):
        return f'{self.instrument_name} - {self.piece.title}'


class LessonPiece(models.Model):
    """
    Through model connecting course lessons to pieces with per-lesson customization.
    Allows the same piece to be used in multiple lessons with different settings.
    """
    lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.CASCADE,
        related_name='lesson_pieces'
    )
    piece = models.ForeignKey(
        Piece,
        on_delete=models.CASCADE,
        related_name='lesson_assignments'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order within this specific lesson"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Show/hide this piece in the lesson"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Custom instructions for this piece in this lesson"
    )
    is_optional = models.BooleanField(
        default=False,
        help_text="Mark as optional practice"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Lesson Piece Assignment'
        verbose_name_plural = 'Lesson Piece Assignments'

    def __str__(self):
        return f'{self.piece.title} in {self.lesson.lesson_title}'
