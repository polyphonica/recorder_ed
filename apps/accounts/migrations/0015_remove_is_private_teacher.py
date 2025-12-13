# Generated migration for removing is_private_teacher field
# All references have been updated to use is_teacher instead
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_final_sync_before_deletion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='is_private_teacher',
        ),
    ]
