from django.contrib import admin
from django.utils.html import format_html


# ============================================================================
# ADMIN MIXINS FOR COMMON FUNCTIONALITY
# ============================================================================

class TimestampFieldsetMixin:
    """
    Mixin to provide standard timestamp fieldset for admin classes.

    Adds a collapsible "Timestamps" fieldset with created_at and updated_at fields.
    These fields are automatically marked as readonly.

    Usage:
        class MyModelAdmin(TimestampFieldsetMixin, admin.ModelAdmin):
            # ... other admin configuration ...
            pass
    """

    def get_fieldsets(self, request, obj=None):
        """Add timestamp fieldset to existing fieldsets"""
        fieldsets = super().get_fieldsets(request, obj)

        # Convert to list if it's a tuple
        fieldsets = list(fieldsets)

        # Add timestamp fieldset if created_at/updated_at exist in model
        model_fields = [f.name for f in self.model._meta.get_fields()]
        timestamp_fields = []

        if 'created_at' in model_fields:
            timestamp_fields.append('created_at')
        if 'updated_at' in model_fields:
            timestamp_fields.append('updated_at')

        if timestamp_fields:
            fieldsets.append((
                'Timestamps',
                {
                    'fields': tuple(timestamp_fields),
                    'classes': ('collapse',)
                }
            ))

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        """Automatically mark timestamp fields as readonly"""
        readonly = list(super().get_readonly_fields(request, obj))

        model_fields = [f.name for f in self.model._meta.get_fields()]

        if 'created_at' in model_fields and 'created_at' not in readonly:
            readonly.append('created_at')
        if 'updated_at' in model_fields and 'updated_at' not in readonly:
            readonly.append('updated_at')

        return readonly


class StudentDisplayMixin:
    """
    Mixin to provide formatted student name display in admin.

    Adds a get_student_display method that shows the student's full name
    with username in parentheses, useful for list_display.

    Requires model to have a 'student' field.

    Usage:
        class MyModelAdmin(StudentDisplayMixin, admin.ModelAdmin):
            list_display = ['get_student_display', ...]
    """

    def get_student_display(self, obj):
        """Display student with full name and username"""
        if not obj.student:
            return "-"

        full_name = obj.student.get_full_name()
        username = obj.student.username

        if full_name:
            return f"{full_name} ({username})"
        return username

    get_student_display.short_description = 'Student'
    get_student_display.admin_order_field = 'student__username'


class ColoredStatusMixin:
    """
    Mixin to provide colored status badges in admin list views.

    Adds a get_colored_status method that displays status with color coding:
    - Green: completed, approved, published
    - Yellow: pending, draft
    - Red: rejected, cancelled, failed
    - Blue: in progress, processing
    - Gray: other statuses

    Requires model to have a 'status' field.

    Usage:
        class MyModelAdmin(ColoredStatusMixin, admin.ModelAdmin):
            list_display = ['get_colored_status', ...]
    """

    # Status color mapping
    STATUS_COLORS = {
        'completed': '#28a745',      # Green
        'approved': '#28a745',
        'published': '#28a745',
        'active': '#28a745',

        'pending': '#ffc107',        # Yellow
        'draft': '#ffc107',
        'review': '#ffc107',

        'rejected': '#dc3545',       # Red
        'cancelled': '#dc3545',
        'failed': '#dc3545',
        'error': '#dc3545',

        'processing': '#007bff',     # Blue
        'in_progress': '#007bff',

        'default': '#6c757d'         # Gray
    }

    def get_colored_status(self, obj):
        """Display status with color coding"""
        if not hasattr(obj, 'status'):
            return "-"

        status = obj.status
        display_text = obj.get_status_display() if hasattr(obj, 'get_status_display') else status

        # Get color for this status
        color = self.STATUS_COLORS.get(status.lower(), self.STATUS_COLORS['default'])

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            display_text
        )

    get_colored_status.short_description = 'Status'
    get_colored_status.admin_order_field = 'status'


# Register your models here.
