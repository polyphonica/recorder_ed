# Generated migration for series registration grouping

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0021_add_session_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshopregistration',
            name='series_registration_id',
            field=models.UUIDField(
                null=True,
                blank=True,
                help_text="Links registrations that were purchased together as a mandatory series. All registrations with the same series_registration_id should be cancelled together."
            ),
        ),
        migrations.AddIndex(
            model_name='workshopregistration',
            index=models.Index(fields=['series_registration_id'], name='workshops_w_series__idx'),
        ),
    ]
