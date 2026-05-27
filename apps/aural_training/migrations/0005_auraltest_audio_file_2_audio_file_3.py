from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aural_training', '0004_glossaryterm'),
    ]

    operations = [
        migrations.AddField(
            model_name='auraltest',
            name='audio_file_2',
            field=models.FileField(blank=True, null=True, upload_to='aural_tests/'),
        ),
        migrations.AddField(
            model_name='auraltest',
            name='audio_file_3',
            field=models.FileField(blank=True, null=True, upload_to='aural_tests/'),
        ),
    ]
