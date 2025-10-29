# Generated migration to sync workshops instructor_profile to accounts profile

from django.db import migrations


def sync_instructor_to_teacher(apps, schema_editor):
    """
    Sync data from workshops.UserProfile (instructor_profile) to accounts.UserProfile (profile).
    This consolidates the dual profile system into a single unified teacher flag.
    """
    # Get models
    WorkshopUserProfile = apps.get_model('workshops', 'UserProfile')
    AccountsUserProfile = apps.get_model('accounts', 'UserProfile')

    synced_count = 0
    created_count = 0

    # Iterate through all workshop instructor profiles
    for workshop_profile in WorkshopUserProfile.objects.all():
        user = workshop_profile.user

        # Get or create the accounts profile
        accounts_profile, created = AccountsUserProfile.objects.get_or_create(user=user)

        if created:
            created_count += 1

        # Sync the is_instructor flag to is_teacher
        if workshop_profile.is_instructor and not accounts_profile.is_teacher:
            accounts_profile.is_teacher = True

            # Also sync bio and website if they exist in workshop profile and are empty in accounts
            if workshop_profile.bio and not accounts_profile.bio:
                accounts_profile.bio = workshop_profile.bio

            if workshop_profile.website and not accounts_profile.website:
                accounts_profile.website = workshop_profile.website

            accounts_profile.save()
            synced_count += 1

    print(f"Synced {synced_count} instructor profiles to teacher profiles")
    print(f"Created {created_count} new accounts profiles")


def reverse_sync(apps, schema_editor):
    """
    Reverse migration - sync teacher flag back to instructor flag.
    """
    WorkshopUserProfile = apps.get_model('workshops', 'UserProfile')
    AccountsUserProfile = apps.get_model('accounts', 'UserProfile')

    for accounts_profile in AccountsUserProfile.objects.filter(is_teacher=True):
        user = accounts_profile.user

        # Get or create workshop profile
        workshop_profile, created = WorkshopUserProfile.objects.get_or_create(user=user)

        if not workshop_profile.is_instructor:
            workshop_profile.is_instructor = True
            workshop_profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_userprofile_default_zoom_link'),
        ('workshops', '0007_auto_20251022_0510'),
    ]

    operations = [
        migrations.RunPython(sync_instructor_to_teacher, reverse_sync),
    ]
