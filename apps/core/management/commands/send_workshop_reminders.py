"""
Management command to send reminder emails for upcoming workshop sessions.

Run every 15 minutes via cron:
    */15 * * * * /path/to/venv/bin/python /path/to/manage.py send_workshop_reminders
"""
import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import ReminderLog
from apps.scheduling.models import ReminderSettings
from apps.workshops.models import WorkshopRegistration, WorkshopSession
from apps.workshops.notifications import WorkshopReminderNotificationService

logger = logging.getLogger(__name__)

# How far either side of the target time to query, to accommodate cron jitter.
WINDOW_MINUTES = 15


class Command(BaseCommand):
    help = 'Send reminder emails for upcoming workshop sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending or logging',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Load reminder settings for the site teacher
        try:
            reminder_settings = ReminderSettings.objects.select_related('teacher').get(
                teacher__profile__is_teacher=True
            )
        except ReminderSettings.DoesNotExist:
            self.stdout.write('No ReminderSettings found — skipping.')
            return
        except ReminderSettings.MultipleObjectsReturned:
            # Fallback: use the first teacher's settings
            reminder_settings = ReminderSettings.objects.filter(
                teacher__profile__is_teacher=True
            ).select_related('teacher').first()

        if not reminder_settings.workshop_reminders_enabled:
            self.stdout.write('Workshop reminders are disabled — skipping.')
            return

        hours = reminder_settings.workshop_reminder_hours
        now = timezone.now()
        window_start = now + timedelta(hours=hours) - timedelta(minutes=WINDOW_MINUTES)
        window_end = now + timedelta(hours=hours) + timedelta(minutes=WINDOW_MINUTES)

        sessions = WorkshopSession.objects.filter(
            start_datetime__gte=window_start,
            start_datetime__lt=window_end,
            is_cancelled=False,
        ).select_related('workshop__instructor')

        session_ct = ContentType.objects.get_for_model(WorkshopSession)
        registration_ct = ContentType.objects.get_for_model(WorkshopRegistration)

        sessions_processed = 0
        instructor_reminders_sent = 0
        student_reminders_sent = 0

        for session in sessions:
            sessions_processed += 1

            # --- Instructor reminder ---
            already_sent = ReminderLog.objects.filter(
                content_type=session_ct,
                object_id=str(session.id),
                reminder_type=ReminderLog.WORKSHOP_INSTRUCTOR,
            ).exists()

            if already_sent:
                self.stdout.write(
                    f'  [skip] Instructor reminder already sent for session {session.id}'
                )
            elif dry_run:
                self.stdout.write(
                    f'  [dry-run] Would send instructor reminder for session {session.id} '
                    f'({session.workshop.title} on {session.start_datetime})'
                )
            else:
                success = WorkshopReminderNotificationService.send_instructor_reminder(session)
                if success:
                    ReminderLog.objects.create(
                        content_type=session_ct,
                        object_id=str(session.id),
                        reminder_type=ReminderLog.WORKSHOP_INSTRUCTOR,
                        recipient_email=session.workshop.instructor.email,
                        lead_hours=hours,
                    )
                    instructor_reminders_sent += 1
                    self.stdout.write(
                        f'  Sent instructor reminder for session {session.id}'
                    )

            # --- Student reminders ---
            registrations = session.registrations.filter(
                status__in=[
                    WorkshopRegistration.Status.REGISTERED,
                    WorkshopRegistration.Status.PROMOTED,
                ]
            ).select_related('student__profile', 'child_profile')

            for registration in registrations:
                already_sent = ReminderLog.objects.filter(
                    content_type=registration_ct,
                    object_id=str(registration.id),
                    reminder_type=ReminderLog.WORKSHOP_STUDENT,
                ).exists()

                if already_sent:
                    self.stdout.write(
                        f'  [skip] Student reminder already sent for registration {registration.id}'
                    )
                    continue

                recipient = registration.email or registration.student.email

                if dry_run:
                    self.stdout.write(
                        f'  [dry-run] Would send student reminder to {recipient} '
                        f'for registration {registration.id}'
                    )
                    continue

                success = WorkshopReminderNotificationService.send_student_reminder(registration)
                if success:
                    ReminderLog.objects.create(
                        content_type=registration_ct,
                        object_id=str(registration.id),
                        reminder_type=ReminderLog.WORKSHOP_STUDENT,
                        recipient_email=recipient,
                        lead_hours=hours,
                    )
                    student_reminders_sent += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[dry-run] {sessions_processed} session(s) in window. '
                    f'No emails sent.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Done. {sessions_processed} session(s) processed. '
                    f'{instructor_reminders_sent} instructor reminder(s) sent, '
                    f'{student_reminders_sent} student reminder(s) sent.'
                )
            )
