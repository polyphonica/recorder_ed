#!/usr/bin/env python
"""
Test script to check email template rendering
Run with: python test_email_rendering.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')
django.setup()

from django.template.loader import render_to_string
from apps.core.notifications import BaseNotificationService

print("=== Email Template Rendering Test ===\n")

# Test 1: Get site name
print("1. Testing site name retrieval:")
site_name = BaseNotificationService.get_site_name()
print(f"   Site name: '{site_name}'")
print()

# Test 2: Render payment confirmation template
print("2. Testing payment confirmation template:")
context = {
    'site_name': site_name,
    'student': type('obj', (object,), {
        'get_full_name': lambda: 'Test Student',
        'username': 'teststudent'
    })(),
    'order': type('obj', (object,), {
        'total_amount': '50.00',
        'completed_at': None,
    })(),
    'order_items': [],
    'lessons_url': 'https://example.com/lessons',
}

try:
    rendered = render_to_string('private_teaching/emails/student_payment_confirmation.txt', context)
    lines = rendered.split('\n')
    print(f"   Subject: {lines[0]}")
    print(f"   Line 2: {lines[2] if len(lines) > 2 else 'N/A'}")
    print(f"   Site name appears in output: {site_name in rendered}")
    print(f"\n   First 10 lines:")
    for i, line in enumerate(lines[:10], 1):
        print(f"   {i}: {line}")
except Exception as e:
    print(f"   ERROR: {e}")

print()

# Test 3: Render lesson request response template
print("3. Testing lesson request response template:")
context = {
    'site_name': site_name,
    'student': type('obj', (object,), {
        'get_full_name': lambda: 'Test Student',
        'username': 'teststudent'
    })(),
    'teacher_name': 'Test Teacher',
    'accepted_lessons': [],
    'rejected_lessons': [],
    'message_text': None,
    'my_requests_url': 'https://example.com/requests',
}

try:
    rendered = render_to_string('private_teaching/emails/student_lesson_request_response.txt', context)
    lines = rendered.split('\n')
    print(f"   Subject: {lines[0]}")
    print(f"   Line 2: {lines[2] if len(lines) > 2 else 'N/A'}")
    print(f"   Site name appears in output: {site_name in rendered}")
    print(f"\n   First 10 lines:")
    for i, line in enumerate(lines[:10], 1):
        print(f"   {i}: {line}")
except Exception as e:
    print(f"   ERROR: {e}")

print()

# Test 4: Test HTML template
print("4. Testing HTML payment confirmation template:")
try:
    html_rendered = render_to_string('private_teaching/emails/student_payment_confirmation.html', context)
    print(f"   HTML rendered successfully: True")
    print(f"   Site name appears in HTML: {site_name in html_rendered}")
    # Check for site name in the header area
    import re
    header_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_rendered, re.DOTALL)
    if header_match:
        print(f"   H1 header content: '{header_match.group(1).strip()}'")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n=== End Test ===")
