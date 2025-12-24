from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone', 'is_student', 'is_teacher', 'is_guardian', 'email_verified', 'profile_completed', 'created_at']
    list_filter = ['email_verified', 'profile_completed', 'is_student', 'is_teacher', 'is_guardian', 'country', 'created_at']
    search_fields = ['user__email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['id', 'email_verified_at', 'created_at', 'updated_at']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add help text to role fields
        if 'is_student' in form.base_fields:
            form.base_fields['is_student'].help_text = 'Default for adult student signups. Allows enrollment in courses, workshops, and private lessons.'
        if 'is_teacher' in form.base_fields:
            form.base_fields['is_teacher'].help_text = 'Must be manually enabled by admin. Allows creating courses, workshops, and offering private lessons.'
        if 'is_guardian' in form.base_fields:
            form.base_fields['is_guardian'].help_text = 'Parent/guardian managing child profiles (students under 18). Set automatically during signup.'
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
            'fields': ('is_student', 'is_teacher', 'is_guardian'),
            'description': (
                'User roles for the platform:\n'
                '• is_student: Adult student account (18+). Can enroll in courses, workshops, and request private lessons.\n'
                '• is_teacher: Must be manually enabled by admin. Teachers can create courses, workshops, and offer private lessons.\n'
                '• is_guardian: Parent/guardian account managing child profiles (students under 18). Set automatically during signup.\n'
                '\nNOTE: Account type is set during signup based on user selection.'
            )
        }),
        ('Teacher Information', {
            'fields': ('bio', 'website', 'teaching_experience', 'specializations'),
            'classes': ('collapse',)
        }),
        ('Profile Status', {
            'fields': ('profile_completed',)
        }),
        ('Email Verification', {
            'fields': ('email_verified', 'email_verified_at'),
            'description': 'Email verification status. Users receive a verification email upon signup.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )