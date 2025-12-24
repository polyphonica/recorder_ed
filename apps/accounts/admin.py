from django.contrib import admin
from .models import UserProfile, ChildProfile

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


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'guardian_name', 'date_of_birth', 'age', 'created_at']
    list_filter = ['created_at', 'date_of_birth']
    search_fields = ['first_name', 'last_name', 'guardian__email', 'guardian__first_name', 'guardian__last_name']
    readonly_fields = ['id', 'age', 'is_adult', 'created_at', 'updated_at']

    fieldsets = (
        ('Child Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth')
        }),
        ('Guardian', {
            'fields': ('guardian',)
        }),
        ('Calculated Fields', {
            'fields': ('age', 'is_adult'),
            'description': 'Age is calculated from date of birth. Students 18+ are eligible for account transfer.'
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def guardian_name(self, obj):
        """Display guardian's name and email"""
        if obj.guardian.get_full_name():
            return f"{obj.guardian.get_full_name()} ({obj.guardian.email})"
        return obj.guardian.email
    guardian_name.short_description = 'Guardian'

    def full_name(self, obj):
        """Display child's full name"""
        return obj.full_name
    full_name.short_description = 'Child Name'