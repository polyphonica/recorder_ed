"""
Nightly: make play-alongs private when their copyright permission has expired,
and remind the teacher 30 days before a permission expires.

Cron (daily):
    cd /var/www/recorder_ed && venv/bin/python manage.py expire_playalong_permissions
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.audioplayer.models import Piece, PieceCollection
from apps.audioplayer.notifications import PlayalongNotificationService

REMINDER_DAYS = 30


class Command(BaseCommand):
    help = 'Make play-alongs private when their permission expires, and send reminders'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report without changing anything or emailing')

    def handle(self, *args, dry_run=False, **options):
        today = timezone.localdate()
        made_private = reminded = 0

        # Public items that are now locked because a permission has run out.
        # Saving them applies the copyright lock, which makes them private.
        for piece in Piece.objects.filter(is_public=True).copyright_locked():
            made_private += self._make_private(piece, dry_run)
        for collection in PieceCollection.objects.filter(is_public=True):
            if collection.is_copyright_locked:
                made_private += self._make_private(collection, dry_run)

        # Tell the teacher about permissions that expired yesterday (the first day they no longer count)
        yesterday = today - datetime.timedelta(days=1)
        for model in (Piece, PieceCollection):
            for item in model.objects.filter(audio_permission=True, permission_expires=yesterday):
                if not dry_run:
                    PlayalongNotificationService.send_permission_expired(item)

        # Reminders a month ahead
        reminder_date = today + datetime.timedelta(days=REMINDER_DAYS)
        for model in (Piece, PieceCollection):
            for item in model.objects.filter(audio_permission=True, permission_expires=reminder_date):
                self.stdout.write(f'Reminder: {item} expires {reminder_date}')
                if not dry_run:
                    PlayalongNotificationService.send_permission_expiring(item)
                reminded += 1

        prefix = 'Would make' if dry_run else 'Made'
        self.stdout.write(self.style.SUCCESS(
            f'{prefix} {made_private} item(s) private; {reminded} reminder(s).'))

    def _make_private(self, item, dry_run):
        self.stdout.write(f'Permission expired, making private: {item}')
        if not dry_run:
            item.save()  # the copyright lock sets is_public=False
        return 1
