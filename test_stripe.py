import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')
django.setup()

from django.contrib.auth.models import User
from apps.payments.stripe_service import create_checkout_session
from decimal import Decimal

# Get a student and teacher
student = User.objects.filter(profile__is_student=True).first()
teacher = User.objects.filter(profile__is_teacher=True).first()

print(f"Student: {student}")
print(f"Teacher: {teacher}")

# Try to create a checkout session
try:
    session = create_checkout_session(
          amount=Decimal('30.00'),
          student=student,
          teacher=teacher,
          domain='private_teaching',
          success_url='https://recorder-ed.com/success/',
          cancel_url='https://recorder-ed.com/cancel/',
          metadata={'test': 'true'}
    )
    print(f"\n✅ SUCCESS! Session created: {session.id}")
    print(f"Checkout URL: {session.url}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()