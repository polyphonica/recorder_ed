from django.contrib import admin
from .models import (
    ProductCategory,
    DigitalProduct,
    ProductFile,
    ProductPurchase,
    ProductReview,
    DigitalProductCartItem
)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


class ProductFileInline(admin.TabularInline):
    model = ProductFile
    extra = 1
    fields = ['title', 'file', 'content_url', 'content_type', 'file_role', 'order']
    readonly_fields = ['content_type']
    ordering = ['order']


@admin.register(DigitalProduct)
class DigitalProductAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'teacher',
        'category',
        'product_type',
        'price',
        'status',
        'total_sales',
        'average_rating',
        'created_at'
    ]
    list_filter = ['status', 'category', 'product_type', 'created_at']
    search_fields = ['title', 'description', 'tags', 'teacher__username', 'teacher__email']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['total_sales', 'average_rating', 'review_count', 'created_at', 'updated_at']
    inlines = [ProductFileInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'short_description', 'description')
        }),
        ('Categorization', {
            'fields': ('category', 'product_type', 'tags')
        }),
        ('Teacher & Pricing', {
            'fields': ('teacher', 'price')
        }),
        ('Media', {
            'fields': ('featured_image',)
        }),
        ('Status & Stats', {
            'fields': ('status', 'published_at', 'total_sales', 'average_rating', 'review_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('teacher', 'category')


@admin.register(ProductFile)
class ProductFileAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'product',
        'file_role',
        'file_extension',
        'file_size',
        'download_limit',
        'access_duration_days',
        'order'
    ]
    list_filter = ['file_role', 'created_at']
    search_fields = ['title', 'product__title']
    ordering = ['product', 'order']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


@admin.register(ProductPurchase)
class ProductPurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'student',
        'product',
        'payment_amount',
        'payment_status',
        'purchased_at',
    ]
    list_filter = ['payment_status', 'purchased_at']
    search_fields = [
        'student__username',
        'student__email',
        'product__title',
        'stripe_payment_intent_id',
        'stripe_checkout_session_id'
    ]
    readonly_fields = [
        'purchased_at',
        'download_counts',
        'stripe_payment_intent_id',
        'stripe_checkout_session_id',
        'paid_at',
    ]

    fieldsets = (
        ('Purchase Details', {
            'fields': ('student', 'product', 'child_profile', 'purchased_at')
        }),
        ('Payment Information', {
            'fields': (
                'payment_status',
                'payment_amount',
                'stripe_payment_intent_id',
                'stripe_checkout_session_id',
                'paid_at'
            )
        }),
        ('Legacy Fields (Deprecated)', {
            'fields': (
                'access_expires_at',
                'download_counts'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'product', 'child_profile')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'student',
        'rating',
        'title',
        'is_verified_purchase',
        'is_published',
        'created_at'
    ]
    list_filter = ['rating', 'is_published', 'is_verified_purchase', 'created_at']
    search_fields = [
        'product__title',
        'student__username',
        'student__email',
        'title',
        'comment'
    ]
    readonly_fields = ['is_verified_purchase', 'created_at', 'updated_at']

    fieldsets = (
        ('Review Details', {
            'fields': ('product', 'student', 'purchase')
        }),
        ('Content', {
            'fields': ('rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_published')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'student', 'purchase')


@admin.register(DigitalProductCartItem)
class DigitalProductCartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['cart__user__username', 'product__title']
    readonly_fields = ['added_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cart__user', 'product')
