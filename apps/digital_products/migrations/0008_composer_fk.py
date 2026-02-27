from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0012_seed_various_composer'),
        ('digital_products', '0007_allow_free_product_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='digitalproduct',
            name='composer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='digital_products',
                to='audioplayer.composer',
            ),
        ),
    ]
