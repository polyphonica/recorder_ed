from django.core.management.base import BaseCommand
from apps.workshops.models import WorkshopRegistration, WorkshopSession


class Command(BaseCommand):
    help = 'Check child_profile settings for workshop registrations'

    def handle(self, *args, **options):
        # Check online workshop registrations
        self.stdout.write("\n=== ONLINE WORKSHOPS ===")
        online_sessions = WorkshopSession.objects.filter(
            workshop__delivery_method='online'
        )[:3]

        for session in online_sessions:
            self.stdout.write(f"\nSession: {session.workshop.title}")
            regs = WorkshopRegistration.objects.filter(session=session)[:5]
            for reg in regs:
                child_info = f"Child: {reg.child_profile.full_name}" if reg.child_profile else "No child_profile"
                self.stdout.write(f"  - {reg.student.username}: {child_info}")

        # Check in-person workshop registrations
        self.stdout.write("\n\n=== IN-PERSON WORKSHOPS ===")
        inperson_sessions = WorkshopSession.objects.filter(
            workshop__delivery_method='in_person'
        )[:3]

        for session in inperson_sessions:
            self.stdout.write(f"\nSession: {session.workshop.title}")
            regs = WorkshopRegistration.objects.filter(session=session)[:5]
            for reg in regs:
                child_info = f"Child: {reg.child_profile.full_name}" if reg.child_profile else "No child_profile"
                self.stdout.write(f"  - {reg.student.username}: {child_info}")

        self.stdout.write("\n")
