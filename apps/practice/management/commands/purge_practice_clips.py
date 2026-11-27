"""
Delete old practice clips and abandoned pending clips.

Run daily from cron, e.g.:
    30 3 * * * cd /var/www/recorder_ed && venv/bin/python manage.py purge_practice_clips >> logs/practice_clips.log 2>&1

- Clips (with their replies) whose last activity is older than
  PRACTICE_CLIP_RETENTION_DAYS, unless someone chose to keep them.
- Pending clips (uploaded on Log practice but never attached to a saved
  entry) older than PRACTICE_CLIP_PENDING_HOURS.

Files are removed by the post_delete signal once each deletion commits.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.practice.models import PracticeClip


class Command(BaseCommand):
    help = 'Delete expired practice clips and abandoned pending clips'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report counts without deleting')

    def handle(self, *args, **options):
        now = timezone.now()
        expired = PracticeClip.objects.filter(
            entry__isnull=False,
            keep=False,
            last_activity_at__lt=now - timedelta(days=settings.PRACTICE_CLIP_RETENTION_DAYS),
        )
        abandoned = PracticeClip.objects.filter(
            entry__isnull=True,
            created_at__lt=now - timedelta(hours=settings.PRACTICE_CLIP_PENDING_HOURS),
        )
        counts = {'expired': expired.count(), 'abandoned': abandoned.count()}

        if not options['dry_run']:
            # Delete one by one so each clip's (and reply's) files are removed
            for qs in (expired, abandoned):
                for clip in qs.iterator():
                    clip.delete()

        verb = 'Would delete' if options['dry_run'] else 'Deleted'
        self.stdout.write(f"{now:%Y-%m-%d %H:%M} {verb} {counts['expired']} expired clip(s) "
                          f"and {counts['abandoned']} abandoned pending clip(s)")
