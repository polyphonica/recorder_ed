"""
Django admin configuration for teacher applications.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import TeacherApplication, TeacherOnboarding


@admin.register(TeacherApplication)
class TeacherApplicationAdmin(admin.ModelAdmin):
    """Admin interface for teacher applications."""

    list_display = ['name', 'email', 'status', 'created_at', 'reviewed_at', 'reviewed_by']
    list_filter = ['status', 'dbs_check_status', 'created_at', 'reviewed_at']
    search_fields = ['name', 'email', 'subjects', 'teaching_biography']
    readonly_fields = ['created_at', 'updated_at', 'terms_agreed_at']

    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'user')
        }),
        ('Teaching Details', {
            'fields': ('teaching_biography', 'qualifications', 'subjects',
                      'teaching_formats', 'availability')
        }),
        ('Safeguarding', {
            'fields': ('dbs_check_status',)
        }),
        ('Application Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason')
        }),
        ('Terms & Timestamps', {
            'fields': ('terms_agreed', 'terms_agreed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'reviewed_by')

    actions = ['approve_applications', 'reject_applications']

    def approve_applications(self, request, queryset):
        """Bulk approve selected applications."""
        count = 0
        for application in queryset.filter(status='pending'):
            application.approve(reviewed_by_user=request.user)
            count += 1
        self.message_user(request, f'{count} application(s) approved.')
    approve_applications.short_description = 'Approve selected applications'

    def reject_applications(self, request, queryset):
        """Bulk reject selected applications."""
        count = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{count} application(s) rejected.')
    reject_applications.short_description = 'Reject selected applications'


@admin.register(TeacherOnboarding)
class TeacherOnboardingAdmin(admin.ModelAdmin):
    """Admin interface for teacher onboarding progress."""

    list_display = ['user', 'progress_display', 'is_completed', 'completed_at']
    list_filter = ['is_completed', 'step_1_profile_complete', 'step_2_qualifications_added',
                   'step_3_availability_set', 'step_4_payment_setup', 'step_5_first_listing_created']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'step_1_completed_at', 'step_2_completed_at',
                       'step_3_completed_at', 'step_4_completed_at', 'step_5_completed_at', 'completed_at']

    fieldsets = (
        ('User', {
            'fields': ('user', 'application')
        }),
        ('Step 1: Profile', {
            'fields': ('step_1_profile_complete', 'step_1_completed_at')
        }),
        ('Step 2: Qualifications', {
            'fields': ('step_2_qualifications_added', 'step_2_completed_at')
        }),
        ('Step 3: Availability', {
            'fields': ('step_3_availability_set', 'step_3_completed_at')
        }),
        ('Step 4: Payment', {
            'fields': ('step_4_payment_setup', 'step_4_completed_at')
        }),
        ('Step 5: First Listing', {
            'fields': ('step_5_first_listing_created', 'step_5_completed_at')
        }),
        ('Completion', {
            'fields': ('is_completed', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'application')

    def progress_display(self, obj):
        """Display progress percentage with color coding."""
        percentage = obj.get_progress_percentage()
        if percentage == 100:
            color = 'green'
        elif percentage >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} / 5 steps ({}%)</span>',
            color,
            obj.get_completed_steps_count(),
            percentage
        )
    progress_display.short_description = 'Progress'
