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
        'platform_commission', 
        'status', 
        'created_at'
    ]
    list_filter = ['domain', 'status', 'created_at']
    search_fields = ['student__email', 'teacher__email', 'stripe_payment_intent_id']
    readonly_fields = [
        'stripe_payment_intent_id',
        'stripe_checkout_session_id',
        'created_at',
        'completed_at'
    ]
    
    fieldsets = (
        ('Stripe Information', {
            'fields': ('stripe_payment_intent_id', 'stripe_checkout_session_id')
        }),
        ('Platform Details', {
            'fields': ('domain', 'student', 'teacher', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'platform_commission', 'teacher_share', 'currency')
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
