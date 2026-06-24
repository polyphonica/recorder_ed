from django.contrib import admin

from .models import PracticeEntry


@admin.register(PracticeEntry)
class PracticeEntryAdmin(admin.ModelAdmin):
    list_display = [
        'practice_date',
        'student',
        'child_profile',
        'teacher',
        'duration_minutes',
        'preparing_for_exam',
        'preparing_for_performance',
        'teacher_viewed_at',
        'created_at',
    ]
    list_filter = [
        'preparing_for_exam',
        'preparing_for_performance',
        'practice_date',
        'created_at',
    ]
    search_fields = [
        'student__username',
        'student__email',
        'teacher__username',
        'teacher__email',
        'child_profile__full_name',
        'pieces_practiced',
        'teacher_comment',
    ]
    date_hierarchy = 'practice_date'
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('People', {
            'fields': ('student', 'child_profile', 'teacher', 'lesson_request')
        }),
        ('Practice Details', {
            'fields': ('practice_date', 'duration_minutes', 'pieces_practiced', 'exercises_practiced')
        }),
        ('Reflections', {
            'fields': ('focus_areas', 'struggles', 'achievements', 'enjoyment_rating')
        }),
        ('Preparation', {
            'fields': ('preparing_for_exam', 'preparing_for_performance')
        }),
        ('Teacher Interaction', {
            'fields': ('teacher_comment', 'teacher_viewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'child_profile', 'teacher', 'lesson_request')
