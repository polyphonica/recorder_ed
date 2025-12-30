from django.contrib import admin
from .models import LessonContentTemplate, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(LessonContentTemplate)
class LessonContentTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'syllabus', 'grade_level', 'lesson_number', 'created_by', 'is_public', 'use_count', 'created_at']
    list_filter = ['syllabus', 'is_public', 'created_at']
    search_fields = ['title', 'content']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at', 'use_count']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'created_by')
        }),
        ('Categorization', {
            'fields': ('subject', 'syllabus', 'grade_level', 'lesson_number', 'tags')
        }),
        ('Sharing', {
            'fields': ('is_public',)
        }),
        ('Metadata', {
            'fields': ('use_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
