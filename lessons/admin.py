from django.contrib import admin

from .models import Lesson, Document, LessonOrder, LessonAttachedUrl, PrivateLessonPiece


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('subject', 'lesson_date', 'lesson_time', 'status', 'approved_status', 'payment_status')
    list_filter = ('status', 'approved_status', 'payment_status', 'location', 'subject')
    search_fields = ('subject__subject', 'student__email', 'student__first_name', 'student__last_name', 'teacher__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'teacher', 'student', 'subject', 'lesson_request')
        }),
        ('Lesson Details', {
            'fields': ('lesson_date', 'lesson_time', 'duration_in_minutes', 'fee', 'location')
        }),
        ('Content', {
            'fields': ('lesson_content', 'teacher_notes', 'homework', 'private_note')
        }),
        ('Settings', {
            'fields': ('zoom_link', 'attendance')
        }),
        ('Status', {
            'fields': ('status', 'approved_status', 'payment_status', 'in_cart')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('title', 'lesson__subject__subject')


@admin.register(LessonAttachedUrl)
class LessonAttachedUrlAdmin(admin.ModelAdmin):
    list_display = ('name', 'lesson', 'url', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'lesson__subject__subject')


@admin.register(LessonOrder)
class LessonOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment_status', 'get_total', 'created', 'modified')
    list_filter = ('payment_status', 'created', 'modified')
    search_fields = ('transaction_id',)
    readonly_fields = ('created', 'modified', 'get_total')

    def get_total(self, obj):
        return f"£{obj.get_total:.2f}"
    get_total.short_description = 'Total Amount'


@admin.register(PrivateLessonPiece)
class PrivateLessonPieceAdmin(admin.ModelAdmin):
    list_display = ('piece', 'lesson', 'order', 'is_visible', 'is_optional', 'created_at')
    list_filter = ('is_visible', 'is_optional', 'created_at')
    search_fields = ('piece__title', 'lesson__subject__subject', 'lesson__student__email')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Piece Assignment', {
            'fields': ('lesson', 'piece', 'order')
        }),
        ('Settings', {
            'fields': ('is_visible', 'is_optional', 'instructions')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
