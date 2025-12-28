import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import PayableModel, BaseAttachment


class ProductCategory(models.Model):
    """
    Category for digital products (Sheet Music, Practice Materials, etc.)
    Similar to WorkshopCategory pattern.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="CSS icon class or emoji (e.g., 🎼, 📄)"
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Hex color code for UI display"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Product Categories'
        indexes = [
            models.Index(fields=['is_active', 'order']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class DigitalProduct(models.Model):
    """
    Digital product model for downloadable content.
    Follows Workshop/Course pattern with status workflow.
    """

    PRODUCT_TYPE_CHOICES = [
        ('sheet_music', 'Sheet Music (PDF)'),
        ('practice_materials', 'Practice Materials (PDF)'),
        ('video', 'Video Recording'),
        ('audio', 'Audio File'),
        ('research', 'Research Article/Paper (PDF)'),
        ('bundle', 'Bundle (Multiple Files)'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    # UUID primary key (follows platform pattern)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Information
    slug = models.SlugField(unique=True, max_length=255)
    title = models.CharField(max_length=200)
    description = CKEditor5Field('description', config_name='default')
    short_description = models.CharField(max_length=300)

    # Teacher/Seller
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='digital_products'
    )

    # Product Type & Categorization
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    product_type = models.CharField(max_length=30, choices=PRODUCT_TYPE_CHOICES)
    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated tags (e.g., baroque, intermediate, ensemble)"
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Media
    featured_image = models.ImageField(
        upload_to='digital_products/images/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Product thumbnail (recommended: 1200x800px)"
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Denormalized counts for performance (follows existing pattern)
    total_sales = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'teacher']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['product_type', 'status']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # Exclude current instance when checking for duplicates
            queryset = DigitalProduct.objects.filter(slug=slug)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            while queryset.exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                queryset = DigitalProduct.objects.filter(slug=slug)
                if self.pk:
                    queryset = queryset.exclude(pk=self.pk)

            self.slug = slug

        # Set published_at timestamp when first published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('digital_products:detail', kwargs={'slug': self.slug})

    @property
    def is_published(self):
        return self.status == 'published'

    @property
    def main_files(self):
        """Get main product files (downloadable after purchase)"""
        return self.files.filter(file_role__in=['main', 'bonus'])

    @property
    def preview_files(self):
        """Get preview/sample files (publicly viewable)"""
        return self.files.filter(file_role='preview')

    def update_rating_stats(self):
        """Update average rating and review count from published reviews"""
        from django.db.models import Avg

        published_reviews = self.reviews.filter(is_published=True)

        self.review_count = published_reviews.count()

        if self.review_count > 0:
            avg = published_reviews.aggregate(avg=Avg('rating'))['avg']
            self.average_rating = round(avg, 2)
        else:
            self.average_rating = 0.00

        self.save(update_fields=['average_rating', 'review_count'])


class ProductFile(BaseAttachment):
    """
    Product files using BaseAttachment pattern.
    Supports both file uploads and external URLs (e.g., YouTube videos).
    """

    FILE_ROLE_CHOICES = [
        ('main', 'Main Product File'),
        ('preview', 'Preview/Sample File'),
        ('bonus', 'Bonus Content'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('file', 'Uploaded File'),
        ('url', 'External URL'),
    ]

    product = models.ForeignKey(
        DigitalProduct,
        on_delete=models.CASCADE,
        related_name='files'
    )

    # Override file field with specific upload path and validators - now optional
    file = models.FileField(
        upload_to='digital_products/files/%Y/%m/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator([
                'pdf', 'zip', 'mp3', 'mp4', 'wav', 'flac', 'avi', 'mov'
            ])
        ],
        help_text="Upload a file (max 50MB) OR provide a URL below"
    )

    # URL field for external content
    content_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to external content (e.g., private YouTube video, Vimeo, etc.)"
    )

    # Track content type
    content_type = models.CharField(
        max_length=10,
        choices=CONTENT_TYPE_CHOICES,
        default='file',
        help_text="Automatically set based on whether file or URL is provided"
    )

    # Additional fields
    file_role = models.CharField(
        max_length=20,
        choices=FILE_ROLE_CHOICES,
        default='main',
        help_text="Role of this file (main product, preview, or bonus content)"
    )
    file_size_bytes = models.BigIntegerField(
        default=0,
        help_text="File size in bytes (auto-calculated)"
    )

    # Legacy fields (no longer enforced - lifetime access with secure tokens)
    download_limit = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="DEPRECATED: No longer enforced. Kept for historical data."
    )
    access_duration_days = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="DEPRECATED: No longer enforced. Kept for historical data."
    )

    class Meta:
        ordering = ['order', 'file_role', 'title']

    def clean(self):
        """Validate that at least file or URL is provided (can have both)"""
        from django.core.exceptions import ValidationError
        super().clean()

        has_file = bool(self.file)
        has_url = bool(self.content_url)

        if not has_file and not has_url:
            raise ValidationError({
                '__all__': 'Please provide at least a file upload or a URL (or both).'
            })

    def save(self, *args, **kwargs):
        # Auto-set content_type based on what's provided
        if self.file and self.content_url:
            # Both file and URL provided
            self.content_type = 'file'  # Primary type is file
            self.file_size_bytes = self.file.size
        elif self.file:
            # Only file provided
            self.content_type = 'file'
            self.file_size_bytes = self.file.size
        elif self.content_url:
            # Only URL provided
            self.content_type = 'url'
            self.file_size_bytes = 0  # No file size for URLs

        super().save(*args, **kwargs)

    @property
    def is_preview(self):
        """Check if this is a preview file"""
        return self.file_role == 'preview'

    @property
    def is_downloadable_after_purchase(self):
        """Check if this file requires purchase to download"""
        return self.file_role in ['main', 'bonus']

    @property
    def is_file(self):
        """Check if this has a file upload"""
        return bool(self.file)

    @property
    def is_url(self):
        """Check if this has a URL"""
        return bool(self.content_url)

    @property
    def is_video_url(self):
        """Check if URL is from a known video platform"""
        if not self.content_url:
            return False

        video_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
        return any(domain in self.content_url.lower() for domain in video_domains)

    def get_embed_url(self):
        """Convert regular URL to embed URL for iframes"""
        if not self.is_url:
            return None

        url = self.content_url

        # YouTube
        if 'youtube.com/watch?v=' in url:
            video_id = url.split('watch?v=')[1].split('&')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
            return f'https://www.youtube.com/embed/{video_id}'

        # Vimeo
        elif 'vimeo.com/' in url:
            video_id = url.split('vimeo.com/')[1].split('?')[0]
            return f'https://player.vimeo.com/video/{video_id}'

        # Other URLs - return as-is
        return url


class ProductPurchase(PayableModel):
    """
    Tracks digital product purchases.
    Extends PayableModel for payment tracking + download management.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        DigitalProduct,
        on_delete=models.CASCADE,
        related_name='purchases'
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='digital_product_purchases'
    )

    # Purchase details
    purchased_at = models.DateTimeField(auto_now_add=True)

    # Legacy fields (no longer enforced - lifetime access)
    download_counts = models.JSONField(
        default=dict,
        blank=True,
        help_text="DEPRECATED: No longer tracked. Kept for historical data."
    )
    access_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="DEPRECATED: No longer enforced. Users have lifetime access."
    )

    # Payment fields inherited from PayableModel:
    # - payment_status, payment_amount, stripe_payment_intent_id
    # - stripe_checkout_session_id, paid_at, child_profile

    class Meta:
        unique_together = [['student', 'product']]
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['student', 'payment_status']),
            models.Index(fields=['product', 'payment_status']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.product.title}"

    def can_download_file(self, file):
        """
        Check if user can download a file.
        With lifetime access, this always returns True for completed purchases.

        Returns:
            tuple: (can_download: bool, error_message: str or None)
        """
        if self.payment_status != 'completed':
            return False, "Payment not completed"

        return True, None


class ProductReview(models.Model):
    """
    Product reviews and ratings.
    Similar to course/workshop review patterns.
    Only verified purchasers can review.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        DigitalProduct,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='digital_product_reviews'
    )

    purchase = models.OneToOneField(
        ProductPurchase,
        on_delete=models.CASCADE,
        related_name='review',
        help_text="Link to purchase (ensures only purchasers can review)"
    )

    # Review content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1-5 stars"
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()

    # Verification
    is_verified_purchase = models.BooleanField(
        default=True,
        help_text="Always true since review is linked to purchase"
    )

    # Moderation
    is_published = models.BooleanField(
        default=True,
        help_text="Unpublish for moderation"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['student', 'product']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_published']),
            models.Index(fields=['rating', 'created_at']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.product.title} ({self.rating}/5)"


class DigitalProductCartItem(models.Model):
    """
    Cart items for digital products.
    Integrates with existing Cart model from private_teaching.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    cart = models.ForeignKey(
        'private_teaching.Cart',  # Reuse existing Cart model
        on_delete=models.CASCADE,
        related_name='digital_product_items'
    )

    product = models.ForeignKey(
        DigitalProduct,
        on_delete=models.CASCADE
    )

    # Price at time of adding to cart (can change if product price changes)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price when added to cart (frozen)"
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['cart', 'product']]
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.title} in cart"

    @property
    def total_price(self):
        """Total price (quantity is always 1 for digital products)"""
        return self.price
