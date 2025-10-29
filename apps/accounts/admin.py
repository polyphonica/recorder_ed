from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone', 'is_student', 'is_teacher', 'is_private_teacher', 'profile_completed', 'created_at']
    list_filter = ['profile_completed', 'is_student', 'is_teacher', 'is_private_teacher', 'country', 'created_at']
    search_fields = ['user__email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add help text to role fields
        if 'is_student' in form.base_fields:
            form.base_fields['is_student'].help_text = 'Default for new signups. Allows enrollment in courses, workshops, and private lessons.'
        if 'is_teacher' in form.base_fields:
            form.base_fields['is_teacher'].help_text = 'Must be manually enabled by admin. Allows creating courses, workshops, and offering private lessons.'
        if 'is_private_teacher' in form.base_fields:
            form.base_fields['is_private_teacher'].help_text = 'Set automatically when teacher configures private teaching settings.'
        return form
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'id')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone', 'profile_image')
        }),
        ('Address Information', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country')
        }),
        ('Role Flags', {
            'fields': ('is_student', 'is_teacher', 'is_private_teacher'),
            'description': (
                'User roles for the platform:\n'
                '• is_student: Enabled by default for all new signups. Students can enroll in courses, workshops, and request lessons.\n'
                '• is_teacher: Must be manually enabled by admin. Teachers can create courses, workshops, and offer private lessons.\n'
                '• is_private_teacher: Specific to private teaching module. Set automatically when teachers configure private teaching settings.\n'
                '\nNOTE: New signups are students by default. Only admins can designate teachers.'
            )
        }),
        ('Teacher Information', {
            'fields': ('bio', 'website', 'teaching_experience', 'specializations'),
            'classes': ('collapse',)
        }),
        ('Profile Status', {
            'fields': ('profile_completed',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )