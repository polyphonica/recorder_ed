"""
Management command to clean up temporary audio files.

Usage:
    python manage.py cleanup_temp_audio              # Delete files older than 2 hours
    python manage.py cleanup_temp_audio --hours=24   # Delete files older than 24 hours
    python manage.py cleanup_temp_audio --dry-run    # Show what would be deleted
"""

import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Clean up temporary audio files from media/temp_audio directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=float,
            default=2,
            help='Delete files older than this many hours (default: 2)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_audio')

        if not os.path.exists(temp_dir):
            self.stdout.write(self.style.WARNING(
                f'Temp directory does not exist: {temp_dir}'
            ))
            return

        cutoff_time = time.time() - (hours * 3600)
        deleted_count = 0
        total_size = 0

        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)

            # Skip directories
            if os.path.isdir(filepath):
                continue

            try:
                file_mtime = os.path.getmtime(filepath)
                file_size = os.path.getsize(filepath)

                if file_mtime < cutoff_time:
                    if dry_run:
                        age_hours = (time.time() - file_mtime) / 3600
                        self.stdout.write(
                            f'Would delete: {filename} '
                            f'(age: {age_hours:.1f}h, size: {file_size // 1024}KB)'
                        )
                    else:
                        os.remove(filepath)

                    deleted_count += 1
                    total_size += file_size

            except OSError as e:
                self.stdout.write(self.style.WARNING(
                    f'Error processing {filename}: {e}'
                ))

        # Summary
        size_mb = total_size / (1024 * 1024)
        action = 'Would delete' if dry_run else 'Deleted'

        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f'{action} {deleted_count} file(s), freeing {size_mb:.2f}MB'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'No files older than {hours} hours found'
            ))
