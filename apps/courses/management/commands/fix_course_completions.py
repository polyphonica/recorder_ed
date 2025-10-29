"""
Management command to fix course enrollments that are 100% complete but not marked as such.

This command checks all active enrollments and calls check_and_mark_complete() on those
that have completed all lessons and quizzes but don't have a completed_at timestamp.

Usage:
    python manage.py fix_course_completions
    python manage.py fix_course_completions --dry-run
"""

from django.core.management.base import BaseCommand
from apps.courses.models import CourseEnrollment


class Command(BaseCommand):
    help = 'Fix course enrollments that are 100% complete but not marked as such'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))

        # Get all active enrollments without a completion date
        enrollments = CourseEnrollment.objects.filter(
            is_active=True,
            completed_at__isnull=True
        ).select_related('course', 'student')

        self.stdout.write(f'Found {enrollments.count()} enrollments to check\n')

        fixed_count = 0
        already_complete = 0

        for enrollment in enrollments:
            student_name = enrollment.student.get_full_name() or enrollment.student.username
            course_title = enrollment.course.title

            # Check if enrollment is actually complete
            if enrollment.progress_percentage == 100:
                self.stdout.write(
                    f'  Checking: {student_name} - {course_title} (100% complete)'
                )

                if not dry_run:
                    # This will check all topics, mark complete if needed, and create certificate
                    was_marked = enrollment.check_and_mark_complete()

                    if was_marked:
                        fixed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'    ✓ Marked as complete and created certificate')
                        )
                    else:
                        already_complete += 1
                        self.stdout.write(
                            self.style.WARNING(f'    ⚠ Already had completion date (this shouldn\'t happen)')
                        )
                else:
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'    ✓ Would mark as complete and create certificate')
                    )

        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\nDRY RUN COMPLETE'))
            self.stdout.write(f'Would fix {fixed_count} enrollments')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nCOMPLETE'))
            self.stdout.write(f'Fixed {fixed_count} enrollments')
            if already_complete > 0:
                self.stdout.write(f'{already_complete} were already marked complete')

        self.stdout.write('')
