from django.contrib import admin
from django.utils.html import format_html
from .models import Ticket, TicketMessage, TicketAttachment


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ['created_at']
    fields = ['author', 'message', 'is_staff_reply', 'is_internal_note', 'created_at']


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_number', 'subject', 'category', 'priority_badge',
        'status_badge', 'assigned_to', 'created_at', 'sla_indicator'
    ]
    list_filter = ['status', 'category', 'priority', 'assigned_to', 'created_at']
    search_fields = ['ticket_number', 'subject', 'description', 'email', 'name']
    readonly_fields = [
        'ticket_number', 'created_at', 'updated_at',
        'first_response_at', 'last_response_at', 'resolved_at', 'closed_at'
    ]
    inlines = [TicketMessageInline, TicketAttachmentInline]

    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_number', 'user', 'name', 'email', 'subject', 'description')
        }),
        ('Categorization', {
            'fields': ('category', 'priority', 'status')
        }),
        ('Assignment', {
            'fields': ('assigned_to',)
        }),
        ('SLA Tracking', {
            'fields': ('first_response_at', 'last_response_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def priority_badge(self, obj):
        colors = {
            'urgent': 'red',
            'high': 'orange',
            'normal': 'blue',
            'low': 'gray',
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    def status_badge(self, obj):
        colors = {
            'open': '#3b82f6',
            'in_progress': '#f59e0b',
            'waiting_user': '#8b5cf6',
            'resolved': '#10b981',
            'closed': '#6b7280',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def sla_indicator(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">⚠ OVERDUE</span>')
        return format_html('<span style="color: green;">✓ On Time</span>')
    sla_indicator.short_description = 'SLA'


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'message_preview', 'is_staff_reply', 'is_internal_note', 'created_at']
    list_filter = ['is_staff_reply', 'is_internal_note', 'created_at']
    search_fields = ['ticket__ticket_number', 'message', 'author__username']
    readonly_fields = ['created_at']

    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'filename', 'uploaded_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['ticket__ticket_number', 'filename']
    readonly_fields = ['created_at']
