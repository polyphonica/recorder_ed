"""
Django Admin configuration for Help Center.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Article


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for managing help center categories.
    """
    list_display = ['name', 'icon_preview', 'article_count', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'id']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def icon_preview(self, obj):
        """Show icon preview in list view"""
        return format_html('<i class="{}"></i> <code>{}</code>', obj.icon, obj.icon)
    icon_preview.short_description = 'Icon'

    def article_count(self, obj):
        """Show number of published articles"""
        count = obj.article_count
        if count == 0:
            return format_html('<span style="color: #999;">{}</span>', count)
        return count
    article_count.short_description = 'Articles'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """
    Admin interface for managing help center articles.
    """
    list_display = [
        'title',
        'category',
        'order',
        'status',
        'is_promoted',
        'view_count',
        'helpfulness_display',
        'published_at',
        'updated_at'
    ]
    list_filter = ['status', 'is_promoted', 'category', 'created_at', 'published_at']
    list_editable = ['order', 'status', 'is_promoted']
    search_fields = ['title', 'summary', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = [
        'created_at',
        'updated_at',
        'published_at',
        'view_count',
        'helpful_count',
        'not_helpful_count',
        'helpfulness_display',
        'id'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'title', 'slug', 'summary', 'order')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Publishing', {
            'fields': ('status', 'is_promoted', 'published_at')
        }),
        ('SEO', {
            'fields': ('meta_description',),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count', 'helpfulness_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def helpfulness_display(self, obj):
        """Display helpfulness score with visual indicator"""
        score = obj.helpfulness_score
        if score is None:
            return format_html('<span style="color: #999;">No votes yet</span>')

        # Color based on score
        if score >= 75:
            color = '#22c55e'  # Green
        elif score >= 50:
            color = '#eab308'  # Yellow
        else:
            color = '#ef4444'  # Red

        total = obj.helpful_count + obj.not_helpful_count
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span> ({} votes)',
            color,
            score,
            total
        )
    helpfulness_display.short_description = 'Helpfulness'

    actions = ['make_published', 'make_draft', 'make_promoted', 'make_not_promoted']

    def make_published(self, request, queryset):
        """Bulk action to publish articles"""
        updated = queryset.update(status='published')
        self.message_user(request, f'{updated} article(s) published.')
    make_published.short_description = 'Publish selected articles'

    def make_draft(self, request, queryset):
        """Bulk action to set articles to draft"""
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} article(s) set to draft.')
    make_draft.short_description = 'Set selected articles to draft'

    def make_promoted(self, request, queryset):
        """Bulk action to promote articles"""
        updated = queryset.update(is_promoted=True)
        self.message_user(request, f'{updated} article(s) promoted.')
    make_promoted.short_description = 'Promote selected articles'

    def make_not_promoted(self, request, queryset):
        """Bulk action to unpromote articles"""
        updated = queryset.update(is_promoted=False)
        self.message_user(request, f'{updated} article(s) unpromoted.')
    make_not_promoted.short_description = 'Unpromote selected articles'
