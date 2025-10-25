from django.contrib import admin
from .models import ExpenseCategory, Expense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'business_area', 'category', 'amount', 'supplier', 'payment_method']
    list_filter = ['business_area', 'category', 'payment_method', 'date']
    search_fields = ['description', 'supplier', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    autocomplete_fields = ['workshop']

    fieldsets = (
        ('Basic Information', {
            'fields': ('date', 'business_area', 'category', 'description')
        }),
        ('Financial Details', {
            'fields': ('amount', 'supplier', 'payment_method')
        }),
        ('Additional Information', {
            'fields': ('receipt_file', 'notes', 'workshop'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
