"""
Run on the staging server to create 5 test student accounts.

Usage:
    python manage.py shell < create_test_students.py
  or:
    python manage.py runscript create_test_students  (if django-extensions installed)
"""

from django.contrib.auth.models import User
from django.utils import timezone

TEST_ACCOUNTS = [
    'testStudent1@testmail.com',
    'testStudent2@testmail.com',
    'testStudent3@testmail.com',
    'testStudent4@testmail.com',
    'testStudent5@testmail.com',
]
PASSWORD = '!Telemann04?'

for email in TEST_ACCOUNTS:
    username = email.lower()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email},
    )
    if created:
        user.set_password(PASSWORD)
        user.save()
        print(f'Created: {email}')
    else:
        print(f'Already exists: {email}')

    # Ensure email is verified (works for both new and existing accounts)
    profile = user.profile
    if not profile.email_verified:
        profile.email_verified = True
        profile.email_verified_at = timezone.now()
        profile.save(update_fields=['email_verified', 'email_verified_at'])
        print(f'  → email verified')

print('Done.')
