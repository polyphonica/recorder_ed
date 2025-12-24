from django.contrib import admin
from .models import Piece, Stem, LessonPiece, Composer, Tag


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


class StemInline(admin.TabularInline):
    model = Stem
    extra = 1
    fields = ['instrument_name', 'audio_file', 'order']
    ordering = ['order']


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ['title', 'composer', 'created_by', 'grade_level', 'genre', 'difficulty', 'is_public', 'stem_count', 'lesson_count', 'created_at']
    search_fields = ['title', 'composer__name', 'description', 'created_by__username', 'created_by__email']
    list_filter = ['created_by', 'grade_level', 'genre', 'difficulty', 'is_public', 'tags', 'composer', 'created_at']
    filter_horizontal = ['tags']
    inlines = [StemInline]

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
