from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0017_fill_library_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='composer',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
        migrations.AlterField(
            model_name='piece',
            name='slug',
            field=models.SlugField(blank=True, help_text='Web address of the public page. Filled in automatically.', max_length=220, unique=True),
        ),
        migrations.AlterField(
            model_name='piececollection',
            name='slug',
            field=models.SlugField(blank=True, help_text='Web address of the public page. Filled in automatically.', max_length=220, unique=True),
        ),
    ]
