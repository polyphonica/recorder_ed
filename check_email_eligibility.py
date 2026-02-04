#!/usr/bin/env python
"""
Check which workshop participants are eligible to receive emails.
Run with: python manage.py shell < check_email_eligibility.py
"""
from apps.workshops.models import WorkshopSession, WorkshopRegistration

print("\n" + "="*60)
print("WORKSHOP EMAIL ELIGIBILITY CHECK")
print("="*60)

for s in WorkshopSession.objects.order_by('-start_datetime')[:5]:
    print(f"\n{s.workshop.title} - {s.start_datetime.strftime('%Y-%m-%d %H:%M')}")
    print("-" * 40)

    regs = WorkshopRegistration.objects.filter(
        session=s,
        status__in=['registered', 'waitlisted', 'promoted', 'attended']
    ).select_related('student', 'student__profile')

    if not regs:
        print("  No registrations")
        continue

    opted_in = 0
    opted_out = 0

    for r in regs:
        email = r.email or r.student.email or 'NO EMAIL'
        try:
            can_email = r.student.profile.workshop_email_notifications
        except:
            can_email = True

        status = "YES" if can_email else "NO"
        if can_email:
            opted_in += 1
        else:
            opted_out += 1

        print(f"  {r.student.username}: {email} | Can email: {status}")

    print(f"\n  Summary: {opted_in} can receive emails, {opted_out} opted out")

print("\n" + "="*60)
