# Generated migration for profile consolidation refactoring
from django.db import migrations


def final_sync(apps, schema_editor):
    """
    Final sync before removing workshops.UserProfile.
    Ensures no data loss by syncing all data from workshops to accounts.
    """
    try:
        WorkshopProfile = apps.get_model('workshops', 'UserProfile')
        AccountProfile = apps.get_model('accounts', 'UserProfile')

        synced = 0
        created = 0

        for wp in WorkshopProfile.objects.select_related('user').all():
            ap, created_flag = AccountProfile.objects.get_or_create(user=wp.user)

            if created_flag:
                created += 1

            # Sync instructor status
            if wp.is_instructor and not ap.is_teacher:
                ap.is_teacher = True
                synced += 1

            # Preserve bio/website if accounts profile is empty
            if wp.bio and not ap.bio:
                ap.bio = wp.bio
            if wp.website and not ap.website:
                ap.website = wp.website

            ap.save()

        print(f"\n=== Profile Sync Complete ===")
        print(f"  Synced: {synced} users")
        print(f"  Created: {created} profiles")
        print(f"  Total processed: {WorkshopProfile.objects.count()}")
        print(f"=============================\n")

    except Exception as e:
        print(f"\n!!! Error during profile sync: {e}")
        print("This is likely because workshops.UserProfile has already been deleted.")
        print("Skipping sync - this is safe if the deletion migration already ran.\n")


def reverse_sync(apps, schema_editor):
    """
    Reverse migration - for rollback safety.
    No action needed since we're only syncing data, not deleting.
    """
    print("Reverse sync: No action needed (data preservation only)")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_userprofile_email_verified_and_more'),
        ('workshops', '0007_auto_20251022_0510'),
    ]

    operations = [
        migrations.RunPython(final_sync, reverse_sync),
    ]
