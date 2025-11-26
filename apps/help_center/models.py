"""
Help Center models for knowledge base articles and categories.
"""

import uuid
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field


class Category(models.Model):
    """
    Help center category (e.g., Getting Started, Courses, Workshops).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Category name")
    slug = models.SlugField(unique=True, max_length=255)
    description = models.TextField(help_text="Brief description of this category")
    icon = models.CharField(
        max_length=100,
        default='fa-solid fa-book-open-reader',
        help_text='Font Awesome icon class (e.g., "fa-solid fa-graduation-cap")'
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    is_active = models.BooleanField(default=True, help_text="Show this category on the site")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('help_center:category', kwargs={'slug': self.slug})

    @property
    def article_count(self):
        """Count of published articles in this category"""
        return self.articles.filter(status='published').count()


class Article(models.Model):
    """
    Help center article with rich content.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='articles',
        help_text="Category this article belongs to"
    )

    title = models.CharField(max_length=300, help_text="Article title")
    slug = models.SlugField(unique=True, max_length=255)
    summary = models.TextField(
        blank=True,
        help_text="Short summary (optional, shown in listings)"
    )
    content = CKEditor5Field('content', config_name='default', help_text="Full article content")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_promoted = models.BooleanField(
        default=False,
        help_text="Show on help center homepage as promoted article"
    )

    # Metrics
    view_count = models.IntegerField(default=0, help_text="Number of times viewed")
    helpful_count = models.IntegerField(default=0, help_text="Number of 'helpful' votes")
    not_helpful_count = models.IntegerField(default=0, help_text="Number of 'not helpful' votes")

    # SEO
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text="SEO meta description (optional)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['is_promoted', 'status']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Auto-generate slug from title if not provided"""
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('help_center:article', kwargs={'slug': self.slug})

    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    @property
    def helpfulness_score(self):
        """Calculate helpfulness percentage"""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return None
        return round((self.helpful_count / total_votes) * 100, 1)
