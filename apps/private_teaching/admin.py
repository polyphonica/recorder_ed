from django.contrib import admin
from .models import (
    Subject, LessonRequest, LessonRequestMessage, Cart, CartItem, Order, OrderItem,
    TeacherStudentApplication, ApplicationMessage, ExamBoard, ExamRegistration, ExamPiece
)
from lessons.models import Lesson


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject', 'teacher', 'base_price_60min', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['subject', 'teacher__first_name', 'teacher__last_name']
    ordering = ['subject']


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['subject', 'lesson_date', 'lesson_time', 'duration_in_minutes', 'location', 'approved_status', 'payment_status', 'status']
    readonly_fields = ['approved_status', 'payment_status', 'status']


class LessonRequestMessageInline(admin.TabularInline):
    model = LessonRequestMessage
    extra = 0
    fields = ['author', 'message', 'created_at']
    readonly_fields = ['created_at']


@admin.register(LessonRequest)
class LessonRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['student__first_name', 'student__last_name', 'student__email']
    ordering = ['-created_at']
    inlines = [LessonInline, LessonRequestMessageInline]

    def lesson_count(self, obj):
        return obj.lessons.count()
    lesson_count.short_description = 'Lessons'


@admin.register(LessonRequestMessage)
class LessonRequestMessageAdmin(admin.ModelAdmin):
    list_display = ['lesson_request', 'author', 'message_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['author__first_name', 'author__last_name', 'message']
    ordering = ['-created_at']

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ['lesson', 'price', 'added_at']
    readonly_fields = ['added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_count', 'total_amount', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    inlines = [CartItemInline]
    ordering = ['-updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'lesson', 'price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['cart__user__first_name', 'cart__user__last_name']
    ordering = ['-added_at']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['lesson', 'price_paid']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'student', 'total_amount', 'payment_status', 'created_at']
    list_filter = ['payment_status', 'created_at']
    search_fields = ['order_number', 'student__first_name', 'student__last_name']
    inlines = [OrderItemInline]
    ordering = ['-created_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'lesson', 'price_paid']
    list_filter = ['order__created_at']
    search_fields = ['order__order_number']


class ApplicationMessageInline(admin.TabularInline):
    model = ApplicationMessage
    extra = 0
    fields = ['author', 'message', 'is_read', 'created_at']
    readonly_fields = ['created_at']


@admin.register(TeacherStudentApplication)
class TeacherStudentApplicationAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'teacher', 'status', 'created_at', 'status_changed_at']
    list_filter = ['status', 'created_at', 'status_changed_at']
    search_fields = [
        'applicant__first_name', 'applicant__last_name', 'applicant__email',
        'teacher__first_name', 'teacher__last_name',
        'child_profile__first_name', 'child_profile__last_name'
    ]
    ordering = ['-created_at']
    inlines = [ApplicationMessageInline]
    readonly_fields = ['created_at', 'updated_at', 'status_changed_at']

    fieldsets = (
        ('Application Info', {
            'fields': ('applicant', 'child_profile', 'teacher')
        }),
        ('Status', {
            'fields': ('status', 'teacher_notes', 'status_changed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApplicationMessage)
class ApplicationMessageAdmin(admin.ModelAdmin):
    list_display = ['application', 'author', 'message_preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['author__first_name', 'author__last_name', 'message']
    ordering = ['-created_at']

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(ExamBoard)
class ExamBoardAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


class ExamPieceInline(admin.TabularInline):
    model = ExamPiece
    extra = 0
    fields = ['piece_number', 'title', 'composer', 'syllabus_list', 'teacher_notes']


@admin.register(ExamRegistration)
class ExamRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'student_name', 'teacher', 'exam_board', 'grade_type', 'grade_level',
        'exam_date', 'status', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'exam_board', 'grade_type', 'created_at']
    search_fields = [
        'student__first_name', 'student__last_name', 'student__email',
        'teacher__first_name', 'teacher__last_name',
        'child_profile__first_name', 'child_profile__last_name',
        'registration_number'
    ]
    ordering = ['-exam_date', '-created_at']
    inlines = [ExamPieceInline]
    readonly_fields = ['created_at', 'updated_at', 'student_name']

    fieldsets = (
        ('Student & Teacher', {
            'fields': ('student', 'child_profile', 'student_name', 'teacher', 'subject')
        }),
        ('Exam Details', {
            'fields': ('exam_board', 'grade_type', 'grade_level', 'exam_date',
                      'submission_deadline', 'registration_number', 'venue')
        }),
        ('Technical Requirements', {
            'fields': ('scales', 'arpeggios', 'sight_reading', 'aural_tests'),
            'classes': ('collapse',)
        }),
        ('Status & Results', {
            'fields': ('status', 'mark_achieved', 'grade_achieved',
                      'examiner_comments', 'certificate_received_date')
        }),
        ('Payment', {
            'fields': ('fee_amount', 'payment_status', 'payment_amount',
                      'stripe_payment_intent_id', 'paid_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('teacher_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExamPiece)
class ExamPieceAdmin(admin.ModelAdmin):
    list_display = ['exam_registration', 'piece_number', 'title', 'composer', 'syllabus_list']
    list_filter = ['exam_registration__exam_board', 'exam_registration__grade_type']
    search_fields = ['title', 'composer', 'exam_registration__student__first_name']
    ordering = ['exam_registration', 'piece_number']
