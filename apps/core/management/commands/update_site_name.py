"""
Management command to update the Django Site name to Recorder-ed
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Update the Django Site name to Recorder-ed'

    def handle(self, *args, **options):
        try:
            site = Site.objects.get_current()
            old_name = site.name
            site.name = 'Recorder-ed'
            site.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated site name from "{old_name}" to "Recorder-ed"'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating site name: {str(e)}')
            )
