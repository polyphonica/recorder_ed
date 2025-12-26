from django.contrib import admin
from .models import Assignment, AssignmentSubmission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'has_notation_component', 'has_written_component', 'is_active', 'created_at']
    list_filter = ['is_active', 'has_notation_component', 'has_written_component', 'created_at']
    search_fields = ['title', 'instructions', 'created_by__username', 'created_by__first_name', 'created_by__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'instructions', 'created_by')
        }),
        ('Assignment Components', {
            'fields': ('has_notation_component', 'has_written_component', 'written_questions')
        }),
        ('Reference/Example', {
            'fields': ('reference_notation',),
            'classes': ('collapse',)
        }),
        ('Auto-Grading (Future)', {
            'fields': ('expected_notation', 'expected_written_answers'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'status', 'grade', 'submitted_at', 'graded_at']
    list_filter = ['status', 'submitted_at', 'graded_at']
    search_fields = ['assignment__title', 'student__username', 'student__first_name', 'student__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'submitted_at', 'draft_saved_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'assignment', 'student', 'status')
        }),
        ('Student Work', {
            'fields': ('notation_data', 'written_answers')
        }),
        ('Submission Tracking', {
            'fields': ('draft_saved_at', 'submitted_at', 'created_at', 'updated_at')
        }),
        ('Grading', {
            'fields': ('grade', 'feedback', 'graded_by', 'graded_at')
        }),
    )
