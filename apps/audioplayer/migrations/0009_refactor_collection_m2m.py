# Generated manually for collection M2M refactor

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0008_add_piece_collections'),
    ]

    operations = [
        # Create the new CollectionPiece through model
        migrations.CreateModel(
            name='CollectionPiece',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order within the collection')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_memberships', to='audioplayer.piececollection')),
                ('piece', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_memberships', to='audioplayer.piece')),
            ],
            options={
                'verbose_name': 'Collection Piece',
                'verbose_name_plural': 'Collection Pieces',
                'ordering': ['order'],
                'unique_together': {('collection', 'piece')},
            },
        ),
        # Remove old fields from Piece
        migrations.RemoveField(
            model_name='piece',
            name='collection',
        ),
        migrations.RemoveField(
            model_name='piece',
            name='order_in_collection',
        ),
        # Update Piece ordering
        migrations.AlterModelOptions(
            name='piece',
            options={'ordering': ['title'], 'verbose_name': 'Playalong Piece', 'verbose_name_plural': 'Playalong Pieces'},
        ),
    ]
