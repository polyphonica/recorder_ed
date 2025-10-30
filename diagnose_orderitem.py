#!/usr/bin/env python
"""
Diagnostic script to find specific OrderItem causing issues
Run with: python diagnose_orderitem.py
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')
django.setup()

from apps.private_teaching.models import OrderItem, Order
from lessons.models import Lesson

lesson_id = 'a40735e1-fbee-4d94-9891-9ba97a10e938'

print("=" * 60)
print(f"DIAGNOSTIC: Looking for lesson {lesson_id}")
print("=" * 60)

# Check if lesson exists
print("\n1. Checking if lesson exists:")
try:
    lesson = Lesson.objects.get(id=lesson_id)
    print(f"   ✓ Lesson found: {lesson.subject} on {lesson.lesson_date}")
    print(f"   - Teacher: {lesson.teacher}")
    print(f"   - Student: {lesson.student}")
    print(f"   - Payment status: {lesson.payment_status}")
except Lesson.DoesNotExist:
    print(f"   ✗ Lesson NOT found in database!")

# Check for OrderItem
print(f"\n2. Checking for OrderItem with lesson_id={lesson_id}:")
try:
    order_item = OrderItem.objects.get(lesson_id=lesson_id)
    print(f"   ✓ FOUND OrderItem ID: {order_item.id}")
    print(f"   - Order ID: {order_item.order.id}")
    print(f"   - Order Number: {order_item.order.order_number}")
    print(f"   - Order Status: {order_item.order.payment_status}")
    print(f"   - Order Created: {order_item.order.created_at}")
    print(f"   - Price Paid: £{order_item.price_paid}")

    print("\n   Do you want to delete this OrderItem? (y/n)")
    response = input("   > ")
    if response.lower() == 'y':
        order_item.delete()
        print("   ✓ OrderItem deleted!")
    else:
        print("   - Not deleted")

except OrderItem.DoesNotExist:
    print(f"   ✗ NO OrderItem found with this lesson_id")

# Check ALL OrderItems
print(f"\n3. All OrderItems in database:")
all_order_items = OrderItem.objects.all()
print(f"   Total: {all_order_items.count()}")
for item in all_order_items:
    print(f"   - OrderItem {item.id}: Lesson {item.lesson_id}, Order {item.order.order_number} ({item.order.payment_status})")

# Check ALL Orders
print(f"\n4. All Orders in database:")
all_orders = Order.objects.all()
print(f"   Total: {all_orders.count()}")
for order in all_orders:
    print(f"   - Order {order.order_number}: {order.payment_status}, {order.items.count()} items")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
