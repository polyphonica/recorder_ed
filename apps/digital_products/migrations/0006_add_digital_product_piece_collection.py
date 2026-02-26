from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0011_alter_stem_audio_file'),
        ('digital_products', '0005_update_digitalproductcartitem_cart_fk'),
    ]

    operations = [
        migrations.CreateModel(
            name='DigitalProductPiece',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0)),
                ('piece', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='digital_products',
                    to='audioplayer.piece',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='product_pieces',
                    to='digital_products.digitalproduct',
                )),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('product', 'piece')},
            },
        ),
        migrations.CreateModel(
            name='DigitalProductCollection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0)),
                ('collection', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='digital_products',
                    to='audioplayer.piececollection',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='product_collections',
                    to='digital_products.digitalproduct',
                )),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('product', 'collection')},
            },
        ),
    ]
