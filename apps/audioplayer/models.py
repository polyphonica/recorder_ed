from django.db import models
from django.core.exceptions import ValidationError


class Piece(models.Model):
    """
    A playalong piece with title and optional sheet music image.
    Reusable across multiple lessons.
    """
    title = models.CharField(max_length=200)
    svg_image = models.FileField(
        upload_to='audioplayer/svg_images/',
        null=True,
        blank=True,
        help_text="Sheet music or notation image (SVG/PNG/JPG)"
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
        help_text="MP3 audio file"
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
        return f'{self.piece.title} in {self.lesson.title}'
