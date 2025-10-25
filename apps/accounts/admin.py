from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone', 'is_student', 'is_private_teacher', 'profile_completed', 'created_at']
    list_filter = ['profile_completed', 'is_student', 'is_teacher', 'is_private_teacher', 'country', 'created_at']
    search_fields = ['user__email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
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
            'description': 'Set user roles for different features'
        }),
        ('Guardian Information (for under 18 students)', {
            'fields': ('under_eighteen', 'guardian_first_name', 'guardian_last_name', 'guardian_email', 'guardian_phone'),
            'classes': ('collapse',)
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