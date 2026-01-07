from django.core.management.base import BaseCommand
from apps.workshops.models import WorkshopRegistration
from apps.accounts.models import ChildProfile


class Command(BaseCommand):
    help = 'Fix workshop registrations missing child_profile links'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE - No changes will be made ===\n"))

        # Find registrations without child_profile where student is a guardian
        registrations = WorkshopRegistration.objects.filter(
            child_profile__isnull=True,
            student__profile__is_guardian=True
        ).select_related('student', 'session__workshop')

        fixed_count = 0

        for reg in registrations:
            # Get the guardian's children
            children = ChildProfile.objects.filter(guardian=reg.student)

            if children.count() == 1:
                # Only one child - automatically link it
                child = children.first()
                self.stdout.write(
                    f"✓ {reg.session.workshop.title}: "
                    f"{reg.student.username} -> {child.full_name}"
                )

                if not dry_run:
                    reg.child_profile = child
                    reg.save(update_fields=['child_profile'])

                fixed_count += 1

            elif children.count() > 1:
                # Multiple children - need manual selection
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ {reg.session.workshop.title}: "
                        f"{reg.student.username} has {children.count()} children - needs manual fix"
                    )
                )
                for child in children:
                    self.stdout.write(f"    - {child.full_name} (Age {child.age})")

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Would fix {fixed_count} registrations (run without --dry-run to apply)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Fixed {fixed_count} registrations")
            )
