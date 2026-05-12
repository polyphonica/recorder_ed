from django.contrib import admin
from django.utils.html import format_html

from .models import (
    SightReadingExample, SightReadingSet, SightReadingSetItem,
    SightReadingAssignment, SightReadingResult,
)


class SightReadingSetItemInline(admin.TabularInline):
    model = SightReadingSetItem
    extra = 0
    fields = ('example', 'order')
    ordering = ('order',)


class SightReadingResultInline(admin.TabularInline):
    model = SightReadingResult
    extra = 0
    fields = ('order', 'example', 'result', 'teacher_note', 'played_at')
    readonly_fields = ('played_at',)
    ordering = ('order',)


@admin.register(SightReadingExample)
class SightReadingExampleAdmin(admin.ModelAdmin):
    list_display = ('title', 'grade_level', 'created_by', 'is_public', 'thumbnail', 'created_at')
    list_filter = ('is_public', 'grade_level')
    search_fields = ('title', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at')

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;">', obj.image.url)
        return '-'
    thumbnail.short_description = 'Image'


@admin.register(SightReadingSet)
class SightReadingSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_level', 'created_by', 'is_public', 'item_count', 'created_at')
    list_filter = ('is_public', 'grade_level')
    search_fields = ('name', 'created_by__username')
    inlines = [SightReadingSetItemInline]

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Examples'


@admin.register(SightReadingAssignment)
class SightReadingAssignmentAdmin(admin.ModelAdmin):
    list_display = ('sight_reading_set', 'student_display', 'teacher', 'is_unlocked', 'needs_repeat_display', 'assigned_at', 'completed_at')
    list_filter = ('is_unlocked', 'needs_repeat')
    search_fields = ('sight_reading_set__name', 'student__username', 'teacher__username')
    readonly_fields = ('assigned_at',)
    inlines = [SightReadingResultInline]

    def student_display(self, obj):
        if obj.child_profile:
            return obj.child_profile.full_name
        return obj.student.get_full_name() or obj.student.username
    student_display.short_description = 'Student'

    def needs_repeat_display(self, obj):
        if obj.needs_repeat:
            return format_html('<span style="color:red;font-weight:bold;">⚠ Needs repeat</span>')
        return '—'
    needs_repeat_display.short_description = 'Needs Repeat'


@admin.register(SightReadingResult)
class SightReadingResultAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'order', 'example', 'result', 'played_at')
    list_filter = ('result',)
    search_fields = ('assignment__sight_reading_set__name',)
