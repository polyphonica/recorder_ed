from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('digital_products', '0008_composer_fk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='digitalproduct',
            name='product_type',
            field=models.CharField(
                choices=[
                    ('sheet_music', 'Sheet Music (PDF)'),
                    ('practice_materials', 'Practice Materials (PDF)'),
                    ('play_along', 'Play-Along'),
                    ('video', 'Video Recording'),
                    ('audio', 'Audio File'),
                    ('research', 'Research Article/Paper (PDF)'),
                    ('bundle', 'Bundle (Multiple Files)'),
                ],
                max_length=30,
            ),
        ),
    ]
