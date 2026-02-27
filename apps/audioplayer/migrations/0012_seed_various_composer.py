from django.db import migrations


def seed_various(apps, schema_editor):
    Composer = apps.get_model('audioplayer', 'Composer')
    Composer.objects.get_or_create(name='Various')


class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0011_alter_stem_audio_file'),
    ]

    operations = [
        migrations.RunPython(seed_various, migrations.RunPython.noop),
    ]
