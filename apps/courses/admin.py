"""
Django admin configuration for courses app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Course, Topic, Lesson, LessonAttachment,
    CourseEnrollment, LessonProgress,
    Quiz, QuizQuestion, QuizAnswer, QuizAttempt,
    CourseMessage, CourseCertificate,
    CourseTermsAndConditions, CourseTermsAcceptance,
    CourseCancellationRequest
)
from .forms import CourseAdminForm
from apps.core.admin import ColoredStatusMixin, StudentDisplayMixin


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
        'is_featured', 'show_as_coming_soon', 'expected_launch_date',
        'cost', 'total_enrollments', 'created_at'
    ]
    list_filter = ['status', 'grade', 'is_featured', 'show_as_coming_soon', 'created_at']
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
                'description', 'status', 'is_featured',
                'show_as_coming_soon', 'expected_launch_date'
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
        'student', 'course', 'is_active', 'payment_status', 'payment_amount',
        'get_progress', 'enrolled_at', 'completed_at'
    ]
    list_filter = ['is_active', 'payment_status', 'enrolled_at', 'completed_at', 'course']
    search_fields = [
        'student__username', 'student__email',
        'student__first_name', 'student__last_name',
        'course__title'
    ]
    readonly_fields = [
        'id', 'enrolled_at', 'completed_at', 'paid_at',
        'get_progress', 'stripe_payment_intent_id', 'stripe_checkout_session_id'
    ]
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('student', 'course', 'child_profile', 'is_active')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_amount', 'paid_at',
                      'stripe_payment_intent_id', 'stripe_checkout_session_id')
        }),
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


# ============================================================================
# TERMS & CONDITIONS ADMIN
# ============================================================================

@admin.register(CourseTermsAndConditions)
class CourseTermsAndConditionsAdmin(admin.ModelAdmin):
    """Admin interface for Course Terms and Conditions"""
    list_display = ['version', 'is_current', 'effective_date', 'created_at', 'get_acceptance_count']
    list_filter = ['is_current', 'effective_date', 'created_at']
    search_fields = ['content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'get_acceptance_count']
    fieldsets = (
        ('Version Information', {
            'fields': ('version', 'is_current', 'effective_date')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Statistics', {
            'fields': ('get_acceptance_count',)
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

    def get_acceptance_count(self, obj):
        """Display number of students who accepted this version"""
        return obj.acceptances.count()
    get_acceptance_count.short_description = 'Acceptances'


@admin.register(CourseTermsAcceptance)
class CourseTermsAcceptanceAdmin(admin.ModelAdmin):
    """Admin interface for Course Terms Acceptance records"""
    list_display = ['get_student', 'get_course', 'terms_version', 'accepted_at', 'ip_address']
    list_filter = ['terms_version', 'accepted_at']
    search_fields = [
        'enrollment__student__username',
        'enrollment__student__email',
        'enrollment__course__title',
        'ip_address'
    ]
    readonly_fields = ['id', 'enrollment', 'terms_version', 'accepted_at', 'ip_address']
    fieldsets = (
        ('Acceptance Information', {
            'fields': ('enrollment', 'terms_version', 'accepted_at', 'ip_address')
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('enrollment', 'enrollment__student', 'enrollment__course', 'terms_version')


# ============================================================================
# CANCELLATION & REFUND ADMIN
# ============================================================================

@admin.register(CourseCancellationRequest)
class CourseCancellationRequestAdmin(ColoredStatusMixin, StudentDisplayMixin, admin.ModelAdmin):
    """
    Admin interface for Course Cancellation Requests.

    Uses ColoredStatusMixin for colored status badges and StudentDisplayMixin
    for formatted student names.
    """
    list_display = [
        'get_student_display', 'get_course', 'get_colored_status',
        'is_eligible_for_refund', 'refund_amount',
        'created_at', 'reviewed_at'
    ]
    list_filter = ['status', 'is_eligible_for_refund', 'created_at', 'reviewed_at']
    search_fields = [
        'student__username', 'student__email',
        'student__first_name', 'student__last_name',
        'enrollment__course__title', 'reason'
    ]
    readonly_fields = [
        'id', 'enrollment', 'student', 'created_at', 'updated_at',
        'get_days_since_enrollment', 'get_student_progress'
    ]
    fieldsets = (
        ('Request Information', {
            'fields': (
                'enrollment', 'student', 'reason', 'status',
                'get_days_since_enrollment', 'get_student_progress'
            )
        }),
        ('Refund Details', {
            'fields': ('is_eligible_for_refund', 'refund_amount', 'refund_processed_at')
        }),
        ('Admin Review', {
            'fields': ('admin_notes', 'reviewed_by', 'reviewed_at')
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
    actions = ['approve_cancellations', 'reject_cancellations']

    # Note: get_student_display provided by StudentDisplayMixin
    # Note: get_colored_status provided by ColoredStatusMixin

    def get_course(self, obj):
        """Display course title"""
        return obj.enrollment.course.title
    get_course.short_description = 'Course'

    def get_days_since_enrollment(self, obj):
        """Calculate days since enrollment"""
        from django.utils import timezone
        delta = timezone.now() - obj.enrollment.enrolled_at
        days = delta.days
        if days <= 7:
            color = 'green'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{} days (enrolled: {})</span>',
            color, days, obj.enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M')
        )
    get_days_since_enrollment.short_description = 'Days Since Enrollment'

    def get_student_progress(self, obj):
        """Display student's progress in course"""
        progress = obj.enrollment.progress_percentage
        if progress < 10:
            color = 'green'
        elif progress < 25:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color, progress
        )
    get_student_progress.short_description = 'Course Progress'

    def approve_cancellations(self, request, queryset):
        """Bulk approve cancellations"""
        count = 0
        for cancellation in queryset.filter(status=CourseCancellationRequest.PENDING):
            cancellation.approve(request.user, 'Bulk approved via admin')
            count += 1
        self.message_user(request, f'{count} cancellation(s) approved.')
    approve_cancellations.short_description = 'Approve selected cancellations'

    def reject_cancellations(self, request, queryset):
        """Bulk reject cancellations"""
        count = 0
        for cancellation in queryset.filter(status=CourseCancellationRequest.PENDING):
            cancellation.reject(request.user, 'Bulk rejected via admin')
            count += 1
        self.message_user(request, f'{count} cancellation(s) rejected.')
    reject_cancellations.short_description = 'Reject selected cancellations'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'student', 'enrollment', 'enrollment__course',
            'reviewed_by'
        )
