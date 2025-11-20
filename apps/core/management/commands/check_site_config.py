"""
Management command to check current site configuration
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):
    help = 'Check current site configuration for email branding'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=== Site Configuration Check ===\n'))

        # Check settings.py
        self.stdout.write(f'1. settings.SITE_NAME: "{settings.SITE_NAME}"')
        self.stdout.write(f'2. settings.SITE_ID: {settings.SITE_ID}')

        # Check Django sites framework
        try:
            site = Site.objects.get(pk=settings.SITE_ID)
            self.stdout.write(f'3. Site.objects.get(pk={settings.SITE_ID}):')
            self.stdout.write(f'   - ID: {site.id}')
            self.stdout.write(f'   - Name: "{site.name}"')
            self.stdout.write(f'   - Domain: "{site.domain}"')

            # Check get_current()
            current_site = Site.objects.get_current()
            self.stdout.write(f'4. Site.objects.get_current():')
            self.stdout.write(f'   - ID: {current_site.id}')
            self.stdout.write(f'   - Name: "{current_site.name}"')
            self.stdout.write(f'   - Domain: "{current_site.domain}"')

            # Check what BaseNotificationService would return
            from apps.core.notifications import BaseNotificationService
            site_name = BaseNotificationService.get_site_name()
            self.stdout.write(f'5. BaseNotificationService.get_site_name(): "{site_name}"')

            # Status
            if site_name == 'Recorder-ed':
                self.stdout.write(self.style.SUCCESS('\n✓ Configuration is correct! Emails should show "Recorder-ed"'))
            else:
                self.stdout.write(self.style.ERROR(f'\n✗ Problem: get_site_name() returns "{site_name}" instead of "Recorder-ed"'))
                self.stdout.write(self.style.WARNING('   Run: python manage.py update_site_name'))

        except Site.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Site with ID {settings.SITE_ID} does not exist!'))
            self.stdout.write(self.style.WARNING('   You may need to create it manually in Django admin'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
