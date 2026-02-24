from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import ExamBoard, ExamRegistration, ExamPiece


@admin.register(ExamBoard)
class ExamBoardAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


class ExamPieceInline(admin.TabularInline):
    model = ExamPiece
    extra = 0
    fields = ['piece_number', 'title', 'composer', 'syllabus_list', 'playalong_piece', 'teacher_notes']
    autocomplete_fields = ['playalong_piece']


@admin.register(ExamRegistration)
class ExamRegistrationAdmin(SimpleHistoryAdmin):
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
    list_select_related = ['student', 'teacher', 'child_profile', 'exam_board', 'subject']

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
            'fields': ('payment_amount', 'payment_status',
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
