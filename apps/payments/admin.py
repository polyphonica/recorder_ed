from django.contrib import admin
from .models import StripePayment


@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'domain',
        'student',
        'teacher',
        'total_amount',
        'refund_amount_display',
        'platform_commission',
        'status',
        'created_at'
    ]
    list_filter = ['domain', 'status', 'created_at']
    search_fields = ['student__email', 'teacher__email', 'stripe_payment_intent_id', 'stripe_refund_id']
    readonly_fields = [
        'stripe_payment_intent_id',
        'stripe_checkout_session_id',
        'stripe_refund_id',
        'created_at',
        'completed_at',
        'refunded_at',
        'refund_type_display'
    ]

    def refund_amount_display(self, obj):
        """Display refund amount if refunded"""
        if obj.status == 'refunded' and obj.refund_amount:
            return f"£{obj.refund_amount}"
        return "-"
    refund_amount_display.short_description = 'Refund Amount'

    def refund_type_display(self, obj):
        """Display refund type (Full/Partial)"""
        if obj.status == 'refunded':
            if obj.is_full_refund():
                return "Full Refund"
            elif obj.is_partial_refund():
                return f"Partial Refund (£{obj.refund_amount} of £{obj.total_amount})"
        return "Not Refunded"
    refund_type_display.short_description = 'Refund Type'

    fieldsets = (
        ('Stripe Information', {
            'fields': ('stripe_payment_intent_id', 'stripe_checkout_session_id', 'stripe_refund_id')
        }),
        ('Platform Details', {
            'fields': ('domain', 'student', 'teacher', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'platform_commission', 'teacher_share', 'currency')
        }),
        ('Refund Information', {
            'fields': ('refund_amount', 'refunded_at', 'refund_type_display'),
            'classes': ('collapse',)
        }),
        ('References', {
            'fields': ('workshop_id', 'course_id', 'order_id')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )
