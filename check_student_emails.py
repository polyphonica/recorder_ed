#!/usr/bin/env python
"""
Diagnostic script to check why students aren't receiving emails
Run on PRODUCTION server with: python check_student_emails.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')
django.setup()

from django.contrib.auth.models import User
from apps.private_teaching.models import Order, LessonRequest
from apps.workshops.models import WorkshopRegistration
from django.conf import settings
from django.contrib.sites.models import Site

print("=" * 60)
print("STUDENT EMAIL DIAGNOSTIC REPORT")
print("=" * 60)
print()

# Check 1: Email Configuration
print("1. EMAIL CONFIGURATION:")
print(f"   DEBUG mode: {settings.DEBUG}")
print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
if not settings.DEBUG:
    print(f"   EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
    print(f"   EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
    print(f"   EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
    print(f"   EMAIL_HOST_PASSWORD: {'SET' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else 'NOT SET'}")
print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print()

# Check 2: Site Configuration
print("2. SITE CONFIGURATION:")
try:
    site = Site.objects.get_current()
    print(f"   Site ID: {site.id}")
    print(f"   Site Domain: {site.domain}")
    print(f"   Site Name: {site.name}")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Check 3: Recent Private Teaching Orders
print("3. RECENT PRIVATE TEACHING ORDERS (Last 5):")
try:
    orders = Order.objects.filter(payment_status='completed').order_by('-completed_at')[:5]
    if orders:
        for order in orders:
            print(f"   Order {order.id}:")
            print(f"     - Student: {order.student.username}")
            print(f"     - Student Email: '{order.student.email}'")
            print(f"     - Email exists: {bool(order.student.email)}")
            print(f"     - Completed: {order.completed_at}")
            print()
    else:
        print("   No completed orders found")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Check 4: Recent Workshop Registrations
print("4. RECENT WORKSHOP REGISTRATIONS (Last 5):")
try:
    registrations = WorkshopRegistration.objects.filter(
        payment_status='completed'
    ).order_by('-paid_at')[:5]
    if registrations:
        for reg in registrations:
            print(f"   Registration {reg.id}:")
            print(f"     - Student: {reg.student.username}")
            print(f"     - Student Email: '{reg.student.email}'")
            print(f"     - Registration Email: '{reg.email}'")
            print(f"     - Paid: {reg.paid_at}")
            print()
    else:
        print("   No completed registrations found")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Check 5: Recent Lesson Requests
print("5. RECENT LESSON REQUESTS (Last 5):")
try:
    requests = LessonRequest.objects.order_by('-created_at')[:5]
    if requests:
        for req in requests:
            print(f"   Request {req.id}:")
            print(f"     - Student: {req.student.username}")
            print(f"     - Student Email: '{req.student.email}'")
            print(f"     - Created: {req.created_at}")
            lessons = req.lessons.filter(approved_status='Accepted', payment_status='Paid')
            print(f"     - Paid Lessons: {lessons.count()}")
            print()
    else:
        print("   No lesson requests found")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Check 6: Test Email Sending
print("6. TEST EMAIL FUNCTIONALITY:")
print("   To test sending an email, we'll try to import the notification services:")
try:
    from apps.private_teaching.notifications import StudentNotificationService
    from apps.workshops.notifications import StudentNotificationService as WorkshopStudentService
    print("   ✓ Private teaching notifications imported successfully")
    print("   ✓ Workshop notifications imported successfully")

    # Try to get the most recent order
    recent_order = Order.objects.filter(payment_status='completed').order_by('-completed_at').first()
    if recent_order:
        print(f"\n   Most recent order: {recent_order.id}")
        print(f"   Student email would be sent to: {recent_order.student.email}")
        print(f"\n   ** To test email sending, run this in Django shell:")
        print(f"      from apps.private_teaching.notifications import StudentNotificationService")
        print(f"      from apps.private_teaching.models import Order")
        print(f"      order = Order.objects.get(id='{recent_order.id}')")
        print(f"      StudentNotificationService.send_payment_confirmation(order)")

except Exception as e:
    print(f"   ERROR: {e}")
print()

print("=" * 60)
print("END DIAGNOSTIC REPORT")
print("=" * 60)
print()
print("NEXT STEPS:")
print("1. If EMAIL_BACKEND is console and DEBUG is True, emails won't actually send")
print("2. Check if student email addresses are empty or invalid")
print("3. Check your email provider's logs for bounced emails")
print("4. Run the test command above to manually trigger an email")
print()
