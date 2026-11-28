import datetime

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from apps.core.validators import (
    AUDIO_VALIDATORS,
    SHEET_MUSIC_IMAGE_VALIDATORS,
    SHEET_MUSIC_PDF_VALIDATORS,
)
from .storage import protected_storage


COPYRIGHT_HELP = (
    "Still in copyright: can only be given to your own students, "
    "never made public in the library."
)
COPYRIGHT_LOCK_MESSAGE = (
    "This can't be made public because it contains music still in copyright. "
    "Assign it to your students instead."
)


MISSING_MUSIC_SOURCE_MESSAGE = (
    "Music still in copyright can only be public with a \"Get the music\" source, "
    "so players know where to buy their copy."
)
NO_SCORE_IN_COPYRIGHT_MESSAGE = (
    "Sheet music can't be attached to music still in copyright. "
    "Players use their own copy instead."
)


def valid_permission_q(prefix=''):
    """Q for items whose audio permission is recorded and hasn't expired."""
    today = timezone.localdate()
    return (
        models.Q(**{f'{prefix}audio_permission': True}) &
        (models.Q(**{f'{prefix}permission_expires__isnull': True}) |
         models.Q(**{f'{prefix}permission_expires__gte': today}))
    )


def unique_slug(model, value, instance_pk=None, max_length=200):
    """A slug for value that no other row of model uses."""
    base = slugify(value)[:max_length].strip('-') or 'item'
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
        suffix = f'-{n}'
        slug = base[:max_length - len(suffix)] + suffix
        n += 1
    return slug


def make_copyright_items_private(pieces):
    """Make these pieces, and any public collection containing them without permission, private."""
    pieces.filter(is_public=True).update(is_public=False)
    PieceCollection.objects.filter(
        is_public=True, collection_memberships__piece__in=pieces
    ).exclude(valid_permission_q()).update(is_public=False)


class LibraryItemFields(models.Model):
    """
    Fields shared by pieces and collections for the public library:
    copyright permission, where to get the music, and edition details.
    """
    slug = models.SlugField(max_length=220, unique=True, blank=True,
                            help_text="Web address of the public page. Filled in automatically.")
    is_featured = models.BooleanField(
        default=False, help_text="Show on the Play-Along Library landing page"
    )

    # Permission to publish the audio of music still in copyright
    audio_permission = models.BooleanField(
        default=False,
        help_text="The copyright holder has given permission to publish the audio"
    )
    permission_granted_by = models.CharField(max_length=200, blank=True,
                                             help_text="e.g. Schott Music Ltd")
    permission_date = models.DateField(null=True, blank=True)
    permission_expires = models.DateField(
        null=True, blank=True,
        help_text="Leave blank if the permission doesn't expire. It goes private again after this date."
    )
    permission_notes = models.TextField(blank=True, help_text="Terms, contact, reference number")
    permission_document = models.FileField(
        upload_to='audioplayer/permissions/', storage=protected_storage, blank=True,
        help_text="The letter or email granting permission (private, only you can see it)"
    )

    # "Get the music" (music still in copyright)
    music_source_title = models.CharField(
        max_length=255, blank=True,
        help_text="The publication players need, e.g. \"Giesbert: Method for the Treble Recorder\""
    )
    music_publisher = models.CharField(max_length=200, blank=True, help_text="e.g. Schott Music")
    music_edition = models.CharField(max_length=100, blank=True, help_text="Edition or catalogue number, e.g. ED 2561")
    music_purchase_url = models.URLField(blank=True, help_text="Where to buy it (publisher or shop page)")

    # Recorder-ed Edition (public domain)
    edition_source = models.CharField(
        max_length=255, blank=True,
        help_text="The source your edition is made from, e.g. \"Op. 1, Amsterdam 1708 (facsimile)\""
    )
    edition_editor = models.CharField(max_length=200, blank=True,
                                      help_text="Leave blank to use your own name")
    edition_notes = models.TextField(blank=True, help_text="Short preface or editorial notes shown on the page")

    class Meta:
        abstract = True

    @property
    def has_valid_permission(self):
        if not self.audio_permission:
            return False
        return self.permission_expires is None or self.permission_expires >= timezone.localdate()

    @property
    def editor_name(self):
        if self.edition_editor:
            return self.edition_editor
        user = getattr(self, 'created_by', None)
        return (user.get_full_name() or user.username) if user else ''

    def _ensure_slug(self, value):
        if not self.slug:
            self.slug = unique_slug(type(self), value, self.pk)


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
    in_copyright = models.BooleanField(
        default=False,
        help_text=COPYRIGHT_HELP + " Applies to every piece by this composer."
    )
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Composer'
        verbose_name_plural = 'Composers'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Composer, self.name, self.pk)
        super().save(*args, **kwargs)
        if self.in_copyright:
            make_copyright_items_private(Piece.objects.filter(composer=self).copyright_locked())
            PieceCollection.objects.filter(composer=self, is_public=True).exclude(
                valid_permission_q()).update(is_public=False)

    def get_absolute_url(self):
        return reverse('playalongs:composer', kwargs={'slug': self.slug})


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


class PieceCollection(LibraryItemFields):
    """
    A collection of related pieces (e.g., "Syncopation Exercises", "Scale Patterns").
    Allows grouping multiple pieces together for easier assignment and organization.
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

    title = models.CharField(
        max_length=200,
        help_text="Collection title (e.g., 'Syncopation Exercises Grade 2')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the collection, learning objectives, etc."
    )

    # Full score PDF for download (shared across all pieces in collection)
    pdf_score = models.FileField(
        upload_to='audioplayer/collection_pdfs/',
        storage=protected_storage,
        null=True,
        blank=True,
        validators=SHEET_MUSIC_PDF_VALIDATORS,
        help_text="Full score PDF containing all exercises (max 5MB)"
    )
    pdf_score_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Title for the PDF download (e.g., 'Complete Worksheet')"
    )

    # Metadata
    composer = models.ForeignKey(
        Composer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collections',
        help_text="Composer or arranger (if applicable)"
    )
    grade_level = models.CharField(
        max_length=20,
        choices=GRADE_CHOICES,
        blank=True,
        default='N/A',
        help_text="Associated exam grade level"
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
        help_text="Overall difficulty level"
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='collections',
        help_text="Tags for categorization"
    )

    is_public = models.BooleanField(
        default=True,
        help_text="If checked, collection appears in library for all students"
    )
    in_copyright = models.BooleanField(
        default=False,
        help_text=COPYRIGHT_HELP + " Use for a modern arrangement or book, even when the composers aren't."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_collections',
        help_text="Teacher who created this collection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Piece Collection'
        verbose_name_plural = 'Piece Collections'

    def __str__(self):
        return self.title

    @property
    def piece_count(self):
        return self.collection_memberships.count()

    def _member_pieces(self):
        # A form that is about to change the pieces sets _pending_piece_ids,
        # so the checks use the pieces being saved rather than the old ones
        pending = getattr(self, '_pending_piece_ids', None)
        if pending is not None:
            return Piece.objects.filter(pk__in=pending)
        if not self.pk:
            return Piece.objects.none()
        return Piece.objects.filter(collection_memberships__collection=self)

    @property
    def is_in_copyright(self):
        """The collection itself, its composer, or any piece in it is in copyright."""
        if self.in_copyright or (self.composer_id and self.composer.in_copyright):
            return True
        return self._member_pieces().in_copyright().exists()

    @property
    def is_copyright_locked(self):
        """In copyright without permission, so it can't be public."""
        if self.has_valid_permission:
            return False
        if self.in_copyright or (self.composer_id and self.composer.in_copyright):
            return True
        return self._member_pieces().copyright_locked().exists()

    @property
    def copyright_status(self):
        """'public_domain', 'permitted' or 'students_only'."""
        if not self.is_in_copyright:
            return 'public_domain'
        return 'students_only' if self.is_copyright_locked else 'permitted'

    def clean(self):
        super().clean()
        errors = {}
        in_copyright = self.is_in_copyright
        if self.is_public and self.is_copyright_locked:
            errors['is_public'] = COPYRIGHT_LOCK_MESSAGE
        elif self.is_public and in_copyright and not self.music_source_title:
            errors['music_source_title'] = MISSING_MUSIC_SOURCE_MESSAGE
        if in_copyright and self.pdf_score:
            errors['pdf_score'] = NO_SCORE_IN_COPYRIGHT_MESSAGE
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self._ensure_slug(self.title)
        if self.is_public and self.is_copyright_locked:
            self.is_public = False
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('playalongs:collection', kwargs={'slug': self.slug})


class CollectionPiece(models.Model):
    """
    Through model linking pieces to collections.
    A piece can be in multiple collections.
    """
    collection = models.ForeignKey(
        'PieceCollection',
        on_delete=models.CASCADE,
        related_name='collection_memberships'
    )
    piece = models.ForeignKey(
        'Piece',
        on_delete=models.CASCADE,
        related_name='collection_memberships'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the collection"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['collection', 'piece']
        verbose_name = 'Collection Piece'
        verbose_name_plural = 'Collection Pieces'

    def __str__(self):
        return f'{self.piece.title} in {self.collection.title}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Adding a piece in copyright without permission makes a public collection private
        if self.piece.is_copyright_locked:
            PieceCollection.objects.filter(pk=self.collection_id, is_public=True).exclude(
                valid_permission_q()).update(is_public=False)


class PieceQuerySet(models.QuerySet):
    def in_copyright(self):
        return self.filter(models.Q(in_copyright=True) | models.Q(composer__in_copyright=True))

    def cleared(self):
        """Pieces with audio permission of their own or through a collection."""
        permitted_collections = PieceCollection.objects.filter(valid_permission_q())
        through_collection = CollectionPiece.objects.filter(
            collection__in=permitted_collections).values('piece_id')
        return self.filter(valid_permission_q() | models.Q(pk__in=through_collection))

    def copyright_locked(self):
        """In copyright and without permission."""
        return self.in_copyright().exclude(pk__in=self.cleared().values('pk'))


class Piece(LibraryItemFields):
    """
    A playalong piece with title, optional sheet music, and metadata for library organization.
    Reusable across multiple lessons. Can be standalone or part of a collection.
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
        storage=protected_storage,
        null=True,
        blank=True,
        validators=SHEET_MUSIC_IMAGE_VALIDATORS,
        help_text="Sheet music or notation image (SVG/PNG/JPG) for on-screen display (max 5MB)"
    )

    pdf_score = models.FileField(
        upload_to='audioplayer/pdf_scores/',
        storage=protected_storage,
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

    show_in_library = models.BooleanField(
        default=True,
        help_text="If unchecked, piece won't appear individually in library (useful for pieces only accessed via collections)"
    )

    in_copyright = models.BooleanField(
        default=False,
        help_text=COPYRIGHT_HELP + " Use for a modern arrangement or edition even when the composer isn't."
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

    objects = PieceQuerySet.as_manager()

    def __str__(self):
        return self.title

    @property
    def is_in_copyright(self):
        return self.in_copyright or bool(self.composer_id and self.composer.in_copyright)

    @property
    def permitted_collections(self):
        if not self.pk:
            return PieceCollection.objects.none()
        return PieceCollection.objects.filter(
            valid_permission_q(), collection_memberships__piece=self)

    @property
    def is_cleared(self):
        return self.has_valid_permission or self.permitted_collections.exists()

    @property
    def is_copyright_locked(self):
        """In copyright without permission, so it can't be public."""
        return self.is_in_copyright and not self.is_cleared

    @property
    def copyright_status(self):
        """'public_domain', 'permitted' or 'students_only'."""
        if not self.is_in_copyright:
            return 'public_domain'
        return 'students_only' if self.is_copyright_locked else 'permitted'

    def music_source(self, collection=None):
        """
        The item whose "Get the music" details apply: the piece's own, else the
        collection it is being played in, else any collection with details.
        """
        if self.music_source_title:
            return self
        if collection is not None and collection.music_source_title:
            return collection
        if not self.pk:
            return None
        return PieceCollection.objects.filter(
            collection_memberships__piece=self).exclude(music_source_title='').first()

    def permission_source(self, collection=None):
        """The item whose recorded permission covers this piece, if any."""
        if self.has_valid_permission:
            return self
        if collection is not None and collection.has_valid_permission:
            return collection
        return self.permitted_collections.first()

    def clean(self):
        super().clean()
        errors = {}
        in_copyright = self.is_in_copyright
        if self.is_public and self.is_copyright_locked:
            errors['is_public'] = COPYRIGHT_LOCK_MESSAGE
        elif self.is_public and in_copyright and not self.music_source():
            errors['music_source_title'] = MISSING_MUSIC_SOURCE_MESSAGE
        if in_copyright and self.pdf_score:
            errors['pdf_score'] = NO_SCORE_IN_COPYRIGHT_MESSAGE
        if in_copyright and self.svg_image:
            errors['svg_image'] = NO_SCORE_IN_COPYRIGHT_MESSAGE
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        composer = self.composer.name if self.composer_id else ''
        self._ensure_slug(f'{composer} {self.title}' if composer else self.title)
        if self.is_public and self.is_copyright_locked:
            self.is_public = False
        super().save(*args, **kwargs)
        if self.pk and self.is_copyright_locked:
            make_copyright_items_private(Piece.objects.filter(pk=self.pk))

    def get_absolute_url(self):
        return reverse('playalongs:piece', kwargs={'slug': self.slug})

    @property
    def collections(self):
        """Returns all collections this piece belongs to"""
        return PieceCollection.objects.filter(collection_memberships__piece=self)

    @property
    def is_in_collection(self):
        """Returns True if this piece is part of at least one collection"""
        return self.collection_memberships.exists()


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
        storage=protected_storage,
        validators=AUDIO_VALIDATORS,
        help_text="MP3 or WAV audio file (max 15MB)"
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


class LessonCollection(models.Model):
    """
    Through model connecting course lessons to piece collections.
    Assigning a collection gives students access to all pieces within it.
    """
    lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.CASCADE,
        related_name='lesson_collections'
    )
    collection = models.ForeignKey(
        PieceCollection,
        on_delete=models.CASCADE,
        related_name='lesson_assignments'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order within this specific lesson"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Show/hide this collection in the lesson"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Custom instructions for this collection in this lesson"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Lesson Collection Assignment'
        verbose_name_plural = 'Lesson Collection Assignments'

    def __str__(self):
        return f'{self.collection.title} in {self.lesson.lesson_title}'
