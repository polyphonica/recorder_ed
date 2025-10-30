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

# Check ALL incomplete orders (any age, not just old ones)
print("\n1. Checking for ALL incomplete orders (pending/failed)")
incomplete_orders = Order.objects.filter(
    payment_status__in=['pending', 'failed']
)

print(f"   Found {incomplete_orders.count()} incomplete orders:")
for order in incomplete_orders:
    print(f"   - Order {order.order_number}: {order.payment_status}, {order.items.count()} items, created {order.created_at}")
    # Show the lesson IDs
    for item in order.items.all():
        print(f"     * Lesson ID: {item.lesson_id}")

if incomplete_orders.count() > 0:
    print(f"\n   Deleting {incomplete_orders.count()} incomplete orders...")
    deleted = incomplete_orders.delete()
    print(f"   ✓ Deleted: {deleted}")
else:
    print("   ✓ No incomplete orders to delete")

# Summary of all orders
print("\n2. Current Orders Summary:")
all_orders = Order.objects.all()
print(f"   Total orders: {all_orders.count()}")
print(f"   - Completed: {Order.objects.filter(payment_status='completed').count()}")
print(f"   - Pending: {Order.objects.filter(payment_status='pending').count()}")
print(f"   - Failed: {Order.objects.filter(payment_status='failed').count()}")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE")
print("=" * 60)
