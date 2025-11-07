from django.contrib import admin
from .models import Piece, Stem, LessonPiece


class StemInline(admin.TabularInline):
    model = Stem
    extra = 1
    fields = ['instrument_name', 'audio_file', 'order']
    ordering = ['order']


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ['title', 'stem_count', 'lesson_count', 'created_at', 'updated_at']
    search_fields = ['title']
    list_filter = ['created_at']
    inlines = [StemInline]

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
    list_display = ['piece', 'lesson', 'order', 'is_visible', 'is_optional', 'created_at']
    list_filter = ['is_visible', 'is_optional', 'lesson__topic__course']
    search_fields = ['piece__title', 'lesson__lesson_title', 'lesson__topic__course__title']
    ordering = ['lesson', 'order']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('lesson', 'piece', 'order')
        }),
        ('Display Settings', {
            'fields': ('is_visible', 'is_optional', 'instructions')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
