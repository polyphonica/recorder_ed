from django.contrib import admin
from .models import StudentIntervalProgress, AuralTrainingSession, AuralTestSet, AuralTest, GlossaryTerm


@admin.register(StudentIntervalProgress)
class StudentIntervalProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'child_profile', 'interval', 'attempts', 'correct', 'get_accuracy', 'unlocked', 'get_mastered']
    list_filter = ['interval', 'unlocked']
    search_fields = ['student__email', 'student__first_name', 'student__last_name']
    readonly_fields = ['get_accuracy', 'get_mastered', 'created_at', 'updated_at']

    def get_accuracy(self, obj):
        return f"{obj.accuracy}%"
    get_accuracy.short_description = 'Accuracy'

    def get_mastered(self, obj):
        return obj.is_mastered
    get_mastered.short_description = 'Mastered'
    get_mastered.boolean = True


@admin.register(AuralTrainingSession)
class AuralTrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['student', 'mode', 'started_at', 'ended_at', 'questions_attempted', 'get_accuracy', 'get_duration']
    list_filter = ['mode', 'started_at']
    search_fields = ['student__email', 'student__first_name', 'student__last_name']
    readonly_fields = ['get_accuracy', 'get_duration']

    def get_accuracy(self, obj):
        return f"{obj.accuracy}%"
    get_accuracy.short_description = 'Accuracy'

    def get_duration(self, obj):
        if obj.duration_minutes:
            return f"{obj.duration_minutes} min"
        return "-"
    get_duration.short_description = 'Duration'


class AuralTestInline(admin.TabularInline):
    model = AuralTest
    extra = 0
    fields = ['title', 'instructions', 'audio_file', 'order']
    ordering = ['order', 'title']


@admin.register(AuralTestSet)
class AuralTestSetAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_shared', 'order', 'created_at']
    list_filter = ['is_shared']
    search_fields = ['name', 'created_by__email', 'created_by__first_name', 'created_by__last_name']
    inlines = [AuralTestInline]


@admin.register(AuralTest)
class AuralTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'test_set', 'order', 'created_at']
    list_filter = ['test_set']
    search_fields = ['title', 'test_set__name']


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ['term', 'grade', 'created_by', 'is_shared', 'order', 'created_at']
    list_filter = ['grade', 'is_shared']
    search_fields = ['term', 'definition', 'created_by__email', 'created_by__first_name', 'created_by__last_name']
