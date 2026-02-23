"""
State-only migration: update WorkshopCartItem.cart FK from
private_teaching.Cart to core.Cart.

No database operations — the 'private_teaching_cart' table is unchanged.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_cart'),
        ('workshops', '0031_alter_workshopcartitem_child_profile_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='workshopcartitem',
                    name='cart',
                    field=models.ForeignKey(
                        help_text='Cart this workshop session belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='workshop_items',
                        to='core.cart',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
