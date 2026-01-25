from django.contrib import admin
from .models import Piece, Stem, LessonPiece, Composer, Tag, PieceCollection, LessonCollection, CollectionPiece


@admin.register(Composer)
class ComposerAdmin(admin.ModelAdmin):
    list_display = ['name', 'period', 'piece_count', 'created_at']
    search_fields = ['name', 'period']
    list_filter = ['period', 'created_at']
    ordering = ['name']

    def piece_count(self, obj):
        return obj.pieces.count()
    piece_count.short_description = 'Pieces'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'piece_count', 'created_at']
    search_fields = ['name']
    ordering = ['name']

    def piece_count(self, obj):
        return obj.pieces.count()
    piece_count.short_description = 'Pieces'


class CollectionPieceInline(admin.TabularInline):
    """Inline for viewing/editing pieces within a collection via M2M"""
    model = CollectionPiece
    extra = 1
    fields = ['piece', 'order']
    autocomplete_fields = ['piece']
    ordering = ['order']


@admin.register(PieceCollection)
class PieceCollectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'composer', 'created_by', 'grade_level', 'difficulty', 'piece_count', 'is_public', 'created_at']
    search_fields = ['title', 'composer__name', 'description', 'created_by__username', 'created_by__email']
    list_filter = ['created_by', 'grade_level', 'genre', 'difficulty', 'is_public', 'tags', 'composer', 'created_at']
    filter_horizontal = ['tags']
    inlines = [CollectionPieceInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'composer')
        }),
        ('PDF Score', {
            'fields': ('pdf_score_title', 'pdf_score'),
            'description': 'Full score PDF for download (shared across all pieces in this collection)'
        }),
        ('Classification', {
            'fields': ('grade_level', 'genre', 'difficulty', 'tags')
        }),
        ('Visibility & Owner', {
            'fields': ('is_public', 'created_by')
        }),
    )

    def piece_count(self, obj):
        return obj.collection_memberships.count()
    piece_count.short_description = 'Pieces'


class StemInline(admin.TabularInline):
    model = Stem
    extra = 1
    fields = ['instrument_name', 'audio_file', 'order']
    ordering = ['order']


class PieceCollectionMembershipInline(admin.TabularInline):
    """Inline showing which collections a piece belongs to"""
    model = CollectionPiece
    extra = 1
    fields = ['collection', 'order']
    autocomplete_fields = ['collection']
    ordering = ['order']
    verbose_name = 'Collection Membership'
    verbose_name_plural = 'Collection Memberships'


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ['title', 'composer', 'created_by', 'grade_level', 'genre', 'difficulty', 'is_public', 'stem_count', 'collection_count', 'lesson_count', 'created_at']
    search_fields = ['title', 'composer__name', 'description', 'created_by__username', 'created_by__email']
    list_filter = ['created_by', 'grade_level', 'genre', 'difficulty', 'is_public', 'tags', 'composer', 'created_at']
    filter_horizontal = ['tags']
    inlines = [StemInline, PieceCollectionMembershipInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'composer', 'svg_image', 'pdf_score_title', 'pdf_score')
        }),
        ('Classification', {
            'fields': ('grade_level', 'genre', 'difficulty', 'tags')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Visibility & Owner', {
            'fields': ('is_public', 'created_by')
        }),
    )

    def stem_count(self, obj):
        return obj.stems.count()
    stem_count.short_description = 'Stems'

    def collection_count(self, obj):
        return obj.collection_memberships.count()
    collection_count.short_description = 'Collections'

    def lesson_count(self, obj):
        return obj.lesson_assignments.count()
    lesson_count.short_description = 'Used in Lessons'


@admin.register(Stem)
class StemAdmin(admin.ModelAdmin):
    list_display = ['instrument_name', 'piece', 'order', 'created_at']
    list_filter = ['piece']
    search_fields = ['instrument_name', 'piece__title']
    ordering = ['piece', 'order']


@admin.register(LessonPiece)
class LessonPieceAdmin(admin.ModelAdmin):
    list_display = ['id', 'piece', 'order']

    def get_queryset(self, request):
        """Override to select related lesson data"""
        qs = super().get_queryset(request)
        return qs.select_related('lesson__topic__course', 'piece')


@admin.register(LessonCollection)
class LessonCollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'collection', 'lesson', 'order', 'is_visible', 'created_at']
    list_filter = ['is_visible', 'created_at']
    search_fields = ['collection__title']
    ordering = ['lesson', 'order']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('lesson__topic__course', 'collection')


@admin.register(CollectionPiece)
class CollectionPieceAdmin(admin.ModelAdmin):
    list_display = ['id', 'piece', 'collection', 'order', 'created_at']
    list_filter = ['collection', 'created_at']
    search_fields = ['piece__title', 'collection__title']
    ordering = ['collection', 'order']
    autocomplete_fields = ['piece', 'collection']
