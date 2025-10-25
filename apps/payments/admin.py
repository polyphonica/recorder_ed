from django.contrib import admin
from .models import ShoppingCart, CartItem, Order, OrderItem, Transaction


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at', 'item_count']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items in Cart'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'session', 'price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['cart__user__email', 'session__workshop__title']
    readonly_fields = ['added_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'session_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def session_count(self, obj):
        return obj.items.count()
    session_count.short_description = 'Sessions'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'session', 'price']
    list_filter = ['order__created_at']
    search_fields = ['order__user__email', 'session__workshop__title']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__user__email', 'transaction_id']
    readonly_fields = ['id', 'created_at']