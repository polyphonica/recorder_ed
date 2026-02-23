from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html
from django.db.models import Count, Sum, DecimalField
from django.db.models.functions import Coalesce
from apps.core.models import Cart
from .models import (
    Subject, LessonRequest, LessonRequestMessage, CartItem, Order, OrderItem,
    TeacherStudentApplication, ApplicationMessage,
    PrivateLessonTermsAndConditions, PrivateLessonTermsAcceptance, LessonCancellationRequest,
    StudentPieceAssignment, StudentCollectionAssignment
)
from lessons.models import Lesson


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject', 'teacher', 'base_price_60min', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['subject', 'teacher__first_name', 'teacher__last_name']
    ordering = ['subject']
    list_select_related = ['teacher']


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
    list_select_related = ['student']

    def get_queryset(self, request):
        """PERFORMANCE FIX: Annotate lesson count to avoid N+1 queries"""
        return super().get_queryset(request).annotate(
            _lesson_count=Count('lessons')
        )

    def lesson_count(self, obj):
        return obj._lesson_count
    lesson_count.short_description = 'Lessons'
    lesson_count.admin_order_field = '_lesson_count'


@admin.register(LessonRequestMessage)
class LessonRequestMessageAdmin(admin.ModelAdmin):
    list_display = ['lesson_request', 'author', 'message_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['author__first_name', 'author__last_name', 'message']
    ordering = ['-created_at']
    list_select_related = ['lesson_request', 'author']

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
    list_select_related = ['user']

    def get_queryset(self, request):
        """PERFORMANCE FIX: Annotate item count and total to avoid N+1 queries"""
        return super().get_queryset(request).annotate(
            _item_count=Count('items'),
            _total_amount=Coalesce(Sum('items__price'), 0, output_field=DecimalField())
        )

    def item_count(self, obj):
        return obj._item_count
    item_count.short_description = 'Items'
    item_count.admin_order_field = '_item_count'

    def total_amount(self, obj):
        return f"£{obj._total_amount:.2f}" if obj._total_amount else "£0.00"
    total_amount.short_description = 'Total'
    total_amount.admin_order_field = '_total_amount'


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
class OrderAdmin(SimpleHistoryAdmin):
    list_display = ['order_number', 'student', 'total_amount', 'payment_status', 'created_at']
    list_filter = ['payment_status', 'created_at']
    search_fields = ['order_number', 'student__first_name', 'student__last_name']
    inlines = [OrderItemInline]
    ordering = ['-created_at']
    list_select_related = ['student']


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
class TeacherStudentApplicationAdmin(SimpleHistoryAdmin):
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
    list_select_related = ['applicant', 'teacher', 'child_profile']

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

@admin.register(PrivateLessonTermsAndConditions)
class PrivateLessonTermsAndConditionsAdmin(admin.ModelAdmin):
    list_display = ['version', 'effective_date', 'is_current', 'created_by', 'created_at']
    list_filter = ['is_current', 'effective_date']
    search_fields = ['content']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    ordering = ['-version']

    fieldsets = (
        ('Version Information', {
            'fields': ('version', 'is_current', 'effective_date')
        }),
        ('Content', {
            'fields': ('content',),
            'description': 'Use Markdown formatting for better readability'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Automatically set created_by to current user"""
        if not change:  # Only set on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of terms that have been accepted"""
        if obj and obj.acceptances.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PrivateLessonTermsAcceptance)
class PrivateLessonTermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'terms_version', 'lesson', 'accepted_at', 'ip_address']
    list_filter = ['terms_version', 'accepted_at']
    search_fields = ['student__username', 'student__email', 'ip_address']
    readonly_fields = ['student', 'lesson', 'terms_version', 'accepted_at', 'ip_address', 'user_agent']
    ordering = ['-accepted_at']

    def has_add_permission(self, request):
        """Prevent manual creation of acceptance records"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion only for superusers (for database maintenance)"""
        return request.user.is_superuser


@admin.register(LessonCancellationRequest)
class LessonCancellationRequestAdmin(SimpleHistoryAdmin):
    list_display = ['lesson', 'student', 'teacher', 'request_type', 'status', 'is_within_policy', 'hours_before_lesson', 'created_at']
    list_filter = ['status', 'request_type', 'is_within_policy', 'cancellation_reason', 'created_at']
    search_fields = ['student__username', 'teacher__username', 'lesson__subject__subject', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'hours_before_lesson', 'is_within_policy', 'teacher_responded_at', 'completed_at', 'refund_processed_at']
    ordering = ['-created_at']
    list_select_related = ['lesson', 'lesson__subject', 'student', 'teacher']

    fieldsets = (
        ('Request Information', {
            'fields': ('lesson', 'student', 'teacher', 'request_type', 'cancellation_reason', 'reason')
        }),
        ('Timing & Policy', {
            'fields': ('created_at', 'updated_at', 'hours_before_lesson', 'is_within_policy')
        }),
        ('Status & Resolution', {
            'fields': ('status', 'teacher_response', 'teacher_responded_at', 'completed_at')
        }),
        ('Refund Details', {
            'fields': ('refund_amount', 'platform_fee_retained', 'refund_processed_at'),
            'classes': ('collapse',)
        }),
        ('Reschedule Details', {
            'fields': ('proposed_new_date', 'proposed_new_time'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual creation - should be created through student interface"""
        return False


# ============================================================================
# QUIZ ADMIN CLASSES
# ============================================================================

# Quiz admin moved to apps.quizzes.admin


@admin.register(StudentPieceAssignment)
class StudentPieceAssignmentAdmin(admin.ModelAdmin):
    list_display = ('piece', 'student', 'teacher', 'status', 'assigned_at')
    list_filter = ('status', 'teacher')
    search_fields = ('piece__title', 'student__username', 'student__first_name', 'student__last_name')
    raw_id_fields = ('piece', 'student', 'teacher', 'child_profile')


@admin.register(StudentCollectionAssignment)
class StudentCollectionAssignmentAdmin(admin.ModelAdmin):
    list_display = ('collection', 'student', 'teacher', 'status', 'assigned_at')
    list_filter = ('status', 'teacher')
    search_fields = ('collection__title', 'student__username', 'student__first_name', 'student__last_name')
    raw_id_fields = ('collection', 'student', 'teacher', 'child_profile')
