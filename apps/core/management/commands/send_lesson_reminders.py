"""
Management command to send reminder emails for upcoming private lessons.

Run every 15 minutes via cron:
    */15 * * * * /path/to/venv/bin/python /path/to/manage.py send_lesson_reminders
"""
import logging
import zoneinfo
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import ReminderLog
from apps.private_teaching.notifications import LessonReminderNotificationService
from apps.scheduling.models import ReminderSettings
from lessons.models import Lesson

logger = logging.getLogger(__name__)

# How far either side of the target time to query, to accommodate cron jitter.
WINDOW_MINUTES = 15


class Command(BaseCommand):
    help = 'Send reminder emails for upcoming private lessons'

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
            reminder_settings = ReminderSettings.objects.filter(
                teacher__profile__is_teacher=True
            ).select_related('teacher').first()

        if not reminder_settings.lesson_reminders_enabled:
            self.stdout.write('Lesson reminders are disabled — skipping.')
            return

        hours = reminder_settings.lesson_reminder_hours
        teacher = reminder_settings.teacher

        # Determine teacher's timezone for correct date/time arithmetic
        try:
            teacher_tz = zoneinfo.ZoneInfo(
                teacher.availability_settings.timezone or 'UTC'
            )
        except (AttributeError, zoneinfo.ZoneInfoNotFoundError):
            teacher_tz = zoneinfo.ZoneInfo('UTC')

        now = timezone.now()
        target_dt = now + timedelta(hours=hours)
        target_dt_local = target_dt.astimezone(teacher_tz)

        # Build a ±WINDOW_MINUTES time range in the teacher's local timezone
        window_start_local = (target_dt - timedelta(minutes=WINDOW_MINUTES)).astimezone(teacher_tz)
        window_end_local = (target_dt + timedelta(minutes=WINDOW_MINUTES)).astimezone(teacher_tz)

        target_date = target_dt_local.date()
        time_min = window_start_local.time()
        time_max = window_end_local.time()

        lessons_qs = Lesson.objects.filter(
            is_deleted=False,
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            lesson_date=target_date,
            lesson_time__gte=time_min,
            lesson_time__lt=time_max,
        ).select_related('student__profile', 'teacher__profile')

        lesson_ct = ContentType.objects.get_for_model(Lesson)

        lessons_processed = 0
        student_reminders_sent = 0
        teacher_reminders_sent = 0

        for lesson in lessons_qs:
            lessons_processed += 1

            # --- Student reminder ---
            student_already_sent = ReminderLog.objects.filter(
                content_type=lesson_ct,
                object_id=str(lesson.id),
                reminder_type=ReminderLog.LESSON_STUDENT,
            ).exists()

            if student_already_sent:
                self.stdout.write(
                    f'  [skip] Student reminder already sent for lesson {lesson.id}'
                )
            elif dry_run:
                self.stdout.write(
                    f'  [dry-run] Would send student reminder to {lesson.student.email} '
                    f'for lesson {lesson.id} on {lesson.lesson_date} at {lesson.lesson_time}'
                )
            else:
                success = LessonReminderNotificationService.send_student_reminder(lesson)
                if success:
                    ReminderLog.objects.create(
                        content_type=lesson_ct,
                        object_id=str(lesson.id),
                        reminder_type=ReminderLog.LESSON_STUDENT,
                        recipient_email=lesson.student.email,
                        lead_hours=hours,
                    )
                    student_reminders_sent += 1
                    self.stdout.write(
                        f'  Sent student reminder for lesson {lesson.id}'
                    )

            # --- Teacher reminder ---
            teacher_already_sent = ReminderLog.objects.filter(
                content_type=lesson_ct,
                object_id=str(lesson.id),
                reminder_type=ReminderLog.LESSON_TEACHER,
            ).exists()

            if teacher_already_sent:
                self.stdout.write(
                    f'  [skip] Teacher reminder already sent for lesson {lesson.id}'
                )
            elif dry_run:
                self.stdout.write(
                    f'  [dry-run] Would send teacher reminder to {lesson.teacher.email} '
                    f'for lesson {lesson.id}'
                )
            else:
                success = LessonReminderNotificationService.send_teacher_reminder(lesson)
                if success:
                    ReminderLog.objects.create(
                        content_type=lesson_ct,
                        object_id=str(lesson.id),
                        reminder_type=ReminderLog.LESSON_TEACHER,
                        recipient_email=lesson.teacher.email,
                        lead_hours=hours,
                    )
                    teacher_reminders_sent += 1
                    self.stdout.write(
                        f'  Sent teacher reminder for lesson {lesson.id}'
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[dry-run] {lessons_processed} lesson(s) in window. '
                    f'No emails sent.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Done. {lessons_processed} lesson(s) processed. '
                    f'{student_reminders_sent} student reminder(s) sent, '
                    f'{teacher_reminders_sent} teacher reminder(s) sent.'
                )
            )
