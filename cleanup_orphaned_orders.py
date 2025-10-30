#!/usr/bin/env python
"""
Cleanup script for orphaned OrderItems and incomplete Orders
Run with: python cleanup_orphaned_orders.py
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')
django.setup()

from apps.private_teaching.models import OrderItem, Order
from django.utils import timezone
from datetime import timedelta

print("=" * 60)
print("CLEANUP SCRIPT: Orphaned OrderItems and Incomplete Orders")
print("=" * 60)

# Specific lesson that's causing issues
lesson_id = '47dcfe03-aebe-4b3b-8159-1cb0c0a72241'

print(f"\n1. Checking for OrderItem with lesson_id: {lesson_id}")
try:
    order_item = OrderItem.objects.get(lesson_id=lesson_id)
    print(f"   ✓ FOUND OrderItem ID: {order_item.id}")
    print(f"   - Order: {order_item.order.order_number}")
    print(f"   - Order Status: {order_item.order.payment_status}")
    print(f"   - Order Created: {order_item.order.created_at}")

    # Ask for confirmation (will auto-proceed if piped)
    print(f"\n   Deleting OrderItem {order_item.id}...")
    order_item.delete()
    print("   ✓ Deleted successfully!")
except OrderItem.DoesNotExist:
    print("   ✗ No OrderItem found with that lesson_id")

# Check all incomplete orders older than 1 hour
print("\n2. Checking for old incomplete orders (pending/failed, >1 hour old)")
one_hour_ago = timezone.now() - timedelta(hours=1)
incomplete_orders = Order.objects.filter(
    payment_status__in=['pending', 'failed'],
    created_at__lt=one_hour_ago
)

print(f"   Found {incomplete_orders.count()} incomplete orders:")
for order in incomplete_orders:
    print(f"   - Order {order.order_number}: {order.payment_status}, {order.items.count()} items, created {order.created_at}")

if incomplete_orders.count() > 0:
    print(f"\n   Deleting {incomplete_orders.count()} incomplete orders...")
    deleted = incomplete_orders.delete()
    print(f"   ✓ Deleted: {deleted}")
else:
    print("   ✓ No old incomplete orders to delete")

# Summary of all orders
print("\n3. Current Orders Summary:")
all_orders = Order.objects.all()
print(f"   Total orders: {all_orders.count()}")
print(f"   - Completed: {Order.objects.filter(payment_status='completed').count()}")
print(f"   - Pending: {Order.objects.filter(payment_status='pending').count()}")
print(f"   - Failed: {Order.objects.filter(payment_status='failed').count()}")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE")
print("=" * 60)
