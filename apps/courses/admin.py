"""
Django admin configuration for courses app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Course, Topic, Lesson, LessonAttachment,
    CourseEnrollment, LessonProgress,
    Quiz, QuizQuestion, QuizAnswer, QuizAttempt,
    CourseMessage, CourseCertificate
)
from .forms import CourseAdminForm


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class TopicInline(admin.TabularInline):
    """Inline admin for Topics within Course admin"""
    model = Topic
    extra = 0
    fields = ['topic_number', 'topic_title', 'description']
    ordering = ['topic_number']


class LessonInline(admin.TabularInline):
    """Inline admin for Lessons within Topic admin"""
    model = Lesson
    extra = 0
    fields = ['lesson_number', 'lesson_title', 'status', 'is_preview']
    ordering = ['lesson_number']


class LessonAttachmentInline(admin.TabularInline):
    """Inline admin for Attachments within Lesson admin"""
    model = LessonAttachment
    extra = 0
    fields = ['title', 'file', 'file_type', 'order']
    ordering = ['order']


class QuizQuestionInline(admin.TabularInline):
    """Inline admin for Questions within Quiz admin"""
    model = QuizQuestion
    extra = 0
    fields = ['order', 'text', 'points']
    ordering = ['order']


class QuizAnswerInline(admin.TabularInline):
    """Inline admin for Answers within QuizQuestion admin"""
    model = QuizAnswer
    extra = 0
    fields = ['order', 'text', 'is_correct']
    ordering = ['order']


class LessonProgressInline(admin.TabularInline):
    """Inline admin for LessonProgress within CourseEnrollment admin"""
    model = LessonProgress
    extra = 0
    fields = ['lesson', 'is_completed', 'completed_at']
    readonly_fields = ['lesson', 'completed_at']
    can_delete = False
    max_num = 0


# ============================================================================
# MODEL ADMIN CLASSES
# ============================================================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin interface for Course model"""
    form = CourseAdminForm  # Use custom form with filtered instructor dropdown

    list_display = [
        'title', 'grade', 'instructor', 'status',
        'is_featured', 'cost', 'total_enrollments', 'created_at'
    ]
    list_filter = ['status', 'grade', 'is_featured', 'created_at']
    search_fields = ['title', 'description', 'instructor__username', 'instructor__email']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'published_at',
        'total_topics', 'total_lessons', 'total_enrollments'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'slug', 'instructor', 'grade',
                'description', 'status', 'is_featured'
            )
        }),
        ('Media', {
            'fields': ('image', 'preview_video_url')
        }),
        ('Pricing', {
            'fields': ('cost',)
        }),
        ('Statistics (Read Only)', {
            'fields': (
                'total_topics', 'total_lessons',
                'total_enrollments', 'average_rating'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    inlines = [TopicInline]
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('instructor')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Admin interface for Topic model"""
    list_display = [
        'topic_number', 'topic_title', 'course',
        'get_lessons_count', 'created_at'
    ]
    list_filter = ['course', 'created_at']
    search_fields = ['topic_title', 'description', 'course__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Topic Information', {
            'fields': ('course', 'topic_number', 'topic_title', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    inlines = [LessonInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('course')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """Admin interface for Lesson model"""
    list_display = [
        'lesson_number', 'lesson_title', 'topic', 'status',
        'is_preview', 'duration_minutes', 'created_at'
    ]
    list_filter = ['status', 'is_preview', 'topic__course', 'created_at']
    search_fields = ['lesson_title', 'content', 'topic__topic_title', 'topic__course__title']
    prepopulated_fields = {'slug': ('lesson_title',)}
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Lesson Information', {
            'fields': (
                'topic', 'lesson_number', 'lesson_title',
                'slug', 'content', 'status'
            )
        }),
        ('Media & Access', {
            'fields': ('video_url', 'duration_minutes', 'is_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    inlines = [LessonAttachmentInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('topic', 'topic__course')


@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for LessonAttachment model"""
    list_display = ['title', 'lesson', 'file_type', 'order', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['title', 'lesson__lesson_title']
    readonly_fields = ['id', 'created_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('lesson', 'lesson__topic', 'lesson__topic__course')


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    """Admin interface for CourseEnrollment model"""
    list_display = [
        'student', 'course', 'is_active',
        'get_progress', 'enrolled_at', 'completed_at'
    ]
    list_filter = ['is_active', 'enrolled_at', 'completed_at', 'course']
    search_fields = [
        'student__username', 'student__email',
        'student__first_name', 'student__last_name',
        'course__title'
    ]
    readonly_fields = [
        'id', 'enrolled_at', 'completed_at',
        'get_progress',  # 'order' - TODO: add back when implementing course payments
    ]
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('student', 'course', 'is_active')
        }),
        # TODO: Add back when implementing course payments
        # ('Payment', {
        #     'fields': ('order',)
        # }),
        ('Progress', {
            'fields': ('get_progress', 'enrolled_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    inlines = [LessonProgressInline]
    date_hierarchy = 'enrolled_at'

    def get_progress(self, obj):
        """Display progress percentage"""
        return f"{obj.progress_percentage}%"
    get_progress.short_description = 'Progress'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'course')  # 'order' - TODO: add back when implementing course payments


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    """Admin interface for LessonProgress model"""
    list_display = [
        'enrollment', 'lesson', 'is_completed',
        'started_at', 'completed_at', 'time_spent_display'
    ]
    list_filter = ['is_completed', 'completed_at', 'enrollment__course']
    search_fields = [
        'enrollment__student__username',
        'enrollment__student__email',
        'lesson__lesson_title'
    ]
    readonly_fields = [
        'id', 'started_at', 'completed_at', 'last_accessed_at'
    ]

    def time_spent_display(self, obj):
        """Display time spent in human-readable format"""
        seconds = obj.time_spent_seconds
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        else:
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    time_spent_display.short_description = 'Time Spent'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'enrollment', 'enrollment__student', 'enrollment__course',
            'lesson', 'lesson__topic'
        )


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin interface for Quiz model"""
    list_display = [
        'title', 'lesson', 'status', 'pass_percentage',
        'get_question_count', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'lesson__topic__course']
    search_fields = ['title', 'description', 'lesson__lesson_title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'get_question_count']
    fieldsets = (
        ('Quiz Information', {
            'fields': ('lesson', 'title', 'description', 'pass_percentage', 'status')
        }),
        ('Statistics', {
            'fields': ('get_question_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    inlines = [QuizQuestionInline]

    def get_question_count(self, obj):
        """Display number of questions"""
        return obj.questions.count()
    get_question_count.short_description = 'Questions'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('lesson', 'lesson__topic', 'lesson__topic__course')


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    """Admin interface for QuizQuestion model"""
    list_display = ['get_text_preview', 'quiz', 'order', 'points', 'created_at']
    list_filter = ['quiz', 'created_at']
    search_fields = ['text', 'quiz__title']
    readonly_fields = ['id', 'created_at']
    inlines = [QuizAnswerInline]

    def get_text_preview(self, obj):
        """Display preview of question text"""
        from django.utils.html import strip_tags
        text = strip_tags(obj.text)
        return text[:75] + '...' if len(text) > 75 else text
    get_text_preview.short_description = 'Question'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('quiz', 'quiz__lesson')


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    """Admin interface for QuizAnswer model"""
    list_display = ['text', 'question', 'is_correct_display', 'order', 'created_at']
    list_filter = ['is_correct', 'created_at']
    search_fields = ['text', 'question__text']
    readonly_fields = ['id', 'created_at']

    def is_correct_display(self, obj):
        """Display correct/incorrect with icon"""
        if obj.is_correct:
            return format_html('<span style="color: green;">✓ Correct</span>')
        return format_html('<span style="color: red;">✗ Incorrect</span>')
    is_correct_display.short_description = 'Correct?'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('question', 'question__quiz')


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    """Admin interface for QuizAttempt model"""
    list_display = [
        'enrollment', 'quiz', 'score_display',
        'passed_display', 'started_at', 'submitted_at'
    ]
    list_filter = ['passed', 'started_at', 'quiz']
    search_fields = [
        'enrollment__student__username',
        'enrollment__student__email',
        'quiz__title'
    ]
    readonly_fields = [
        'id', 'started_at', 'submitted_at',
        'score', 'passed', 'answers_data'
    ]
    fieldsets = (
        ('Attempt Information', {
            'fields': ('enrollment', 'quiz')
        }),
        ('Results', {
            'fields': ('score', 'passed', 'started_at', 'submitted_at')
        }),
        ('Answers', {
            'fields': ('answers_data',),
            'classes': ('collapse',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )

    def score_display(self, obj):
        """Display score with color"""
        color = 'green' if obj.passed else 'red'
        return format_html(
            '<span style="color: {};">{:.2f}%</span>',
            color, obj.score
        )
    score_display.short_description = 'Score'

    def passed_display(self, obj):
        """Display pass/fail status with icon"""
        if obj.passed:
            return format_html('<span style="color: green;">✓ Passed</span>')
        return format_html('<span style="color: red;">✗ Failed</span>')
    passed_display.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'enrollment', 'enrollment__student', 'enrollment__course',
            'quiz', 'quiz__lesson'
        )


@admin.register(CourseMessage)
class CourseMessageAdmin(admin.ModelAdmin):
    """Admin interface for CourseMessage model"""
    list_display = [
        'subject', 'sender', 'recipient', 'course',
        'lesson', 'is_read_display', 'sent_at'
    ]
    list_filter = ['read_at', 'sent_at', 'course']
    search_fields = [
        'subject', 'body',
        'sender__username', 'sender__email',
        'recipient__username', 'recipient__email'
    ]
    readonly_fields = ['id', 'sent_at', 'read_at']
    fieldsets = (
        ('Message Information', {
            'fields': ('sender', 'recipient', 'course', 'lesson', 'parent_message')
        }),
        ('Content', {
            'fields': ('subject', 'body')
        }),
        ('Status', {
            'fields': ('sent_at', 'read_at')
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )

    def is_read_display(self, obj):
        """Display read status with icon"""
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange;">○ Unread</span>')
    is_read_display.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sender', 'recipient', 'course', 'lesson')


@admin.register(CourseCertificate)
class CourseCertificateAdmin(admin.ModelAdmin):
    """Admin interface for CourseCertificate model"""
    list_display = [
        'certificate_number', 'get_student', 'get_course',
        'issued_at', 'has_pdf'
    ]
    list_filter = ['issued_at']
    search_fields = [
        'certificate_number',
        'enrollment__student__username',
        'enrollment__student__email',
        'enrollment__course__title'
    ]
    readonly_fields = ['id', 'certificate_number', 'issued_at', 'enrollment']
    fieldsets = (
        ('Certificate Information', {
            'fields': ('enrollment', 'certificate_number', 'issued_at')
        }),
        ('PDF File', {
            'fields': ('pdf_file',)
        }),
        ('IDs', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )

    def get_student(self, obj):
        """Display student name"""
        return obj.enrollment.student.get_full_name() or obj.enrollment.student.username
    get_student.short_description = 'Student'

    def get_course(self, obj):
        """Display course title"""
        return obj.enrollment.course.title
    get_course.short_description = 'Course'

    def has_pdf(self, obj):
        """Display if PDF exists"""
        if obj.pdf_file:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    has_pdf.short_description = 'PDF'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('enrollment', 'enrollment__student', 'enrollment__course')
