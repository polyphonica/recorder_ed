from django.contrib import admin
from django.db.models import Count, Subquery, OuterRef
from django.utils.html import format_html

from .models import Quiz, QuizQuestion, QuizAnswer, QuizAssignment, QuizAttempt


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 4
    fields = ['text', 'is_correct', 'order']
    ordering = ['order']


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'quiz', 'order', 'points']
    list_filter = ['quiz']
    search_fields = ['text', 'quiz__title']
    ordering = ['quiz', 'order']
    inlines = [QuizAnswerInline]
    readonly_fields = ['id']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'created_by', 'syllabus', 'grade_level',
        'question_count', 'pass_percentage', 'is_public', 'use_count', 'created_at',
    ]
    list_filter = ['syllabus', 'is_public', 'created_at', 'grade_level']
    search_fields = ['title', 'description']
    filter_horizontal = ['tags']
    readonly_fields = ['id', 'use_count', 'created_at', 'updated_at', 'total_points']
    list_select_related = ['created_by']
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'description', 'instructions', 'created_by']
        }),
        ('Quiz Settings', {
            'fields': [
                'pass_percentage', 'time_limit_minutes', 'randomize_questions',
                'show_correct_answers', 'allow_retakes', 'max_attempts',
            ]
        }),
        ('Categorization', {
            'fields': ['subject', 'syllabus', 'grade_level', 'tags']
        }),
        ('Sharing', {
            'fields': ['is_public']
        }),
        ('Course Context', {
            'fields': ['course_lesson', 'status'],
            'classes': ['collapse'],
        }),
        ('Metadata', {
            'fields': ['id', 'use_count', 'total_points', 'created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_question_count=Count('questions'))

    def question_count(self, obj):
        return obj._question_count
    question_count.short_description = 'Questions'
    question_count.admin_order_field = '_question_count'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(QuizAssignment)
class QuizAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'quiz', 'student_name', 'teacher', 'status',
        'assigned_date', 'due_date', 'attempt_count', 'best_score',
    ]
    list_filter = ['status', 'assigned_date', 'teacher']
    search_fields = ['quiz__title', 'student__username', 'student__email']
    readonly_fields = ['id', 'assigned_date', 'attempt_count', 'best_score', 'passed_status']
    list_select_related = ['quiz', 'student', 'child_profile', 'teacher']

    def get_queryset(self, request):
        best_score_subquery = QuizAttempt.objects.filter(
            assignment=OuterRef('pk'),
            submitted_at__isnull=False,
        ).order_by('-score').values('score')[:1]

        has_passed_subquery = QuizAttempt.objects.filter(
            assignment=OuterRef('pk'),
            submitted_at__isnull=False,
            passed=True,
        ).values('passed')[:1]

        return super().get_queryset(request).annotate(
            _attempt_count=Count('attempts'),
            _best_score=Subquery(best_score_subquery),
            _has_passed=Subquery(has_passed_subquery),
        )

    def student_name(self, obj):
        if obj.child_profile:
            return f"{obj.child_profile.full_name} (via {obj.student.username})"
        if obj.student:
            return obj.student.get_full_name() or obj.student.username
        return '—'
    student_name.short_description = 'Student'

    def attempt_count(self, obj):
        return obj._attempt_count
    attempt_count.short_description = 'Attempts'
    attempt_count.admin_order_field = '_attempt_count'

    def best_score(self, obj):
        if obj._best_score is None:
            return '-'
        color = 'green' if obj._has_passed else 'red'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color,
            f'{float(obj._best_score):.1f}',
        )
    best_score.short_description = 'Best Score'
    best_score.admin_order_field = '_best_score'

    def passed_status(self, obj):
        if obj._has_passed:
            return format_html('<span style="color: green;">✓ Passed</span>')
        return format_html('<span style="color: red;">✗ Not Passed</span>')
    passed_status.short_description = 'Status'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'assignment', 'started_at', 'submitted_at',
        'colored_score', 'passed_indicator', 'time_taken_minutes',
    ]
    list_filter = ['passed', 'submitted_at', 'started_at']
    search_fields = ['assignment__quiz__title', 'assignment__student__username']
    readonly_fields = [
        'id', 'started_at', 'submitted_at', 'score',
        'passed', 'time_taken_minutes', 'answers_data',
    ]
    list_select_related = ['assignment', 'assignment__quiz', 'assignment__student']

    def colored_score(self, obj):
        if not obj.submitted_at:
            return '-'
        color = 'green' if obj.passed else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            f'{float(obj.score):.1f}',
        )
    colored_score.short_description = 'Score'

    def passed_indicator(self, obj):
        if not obj.submitted_at:
            return format_html('<span style="color: gray;">In Progress</span>')
        if obj.passed:
            return format_html('<span style="color: green;">✓ Passed</span>')
        return format_html('<span style="color: red;">✗ Failed</span>')
    passed_indicator.short_description = 'Result'
