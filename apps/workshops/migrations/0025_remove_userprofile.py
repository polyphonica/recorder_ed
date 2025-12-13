# Generated migration for profile consolidation refactoring
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0024_alter_workshopmaterial_file'),
        # CRITICAL: Must run AFTER accounts sync migration
        ('accounts', '0014_final_sync_before_deletion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='user',
        ),
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
