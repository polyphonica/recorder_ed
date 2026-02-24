"""
State-only migration: remove Cart from private_teaching state and update
CartItem.cart FK to point to core.Cart.

No database operations — the 'private_teaching_cart' table is unchanged.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_cart'),
        ('digital_products', '0005_update_digitalproductcartitem_cart_fk'),
        ('private_teaching', '0033_delete_privatelessonassignment'),
        ('workshops', '0032_update_workshopcartitem_cart_fk'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='Cart'),
                migrations.AlterField(
                    model_name='cartitem',
                    name='cart',
                    field=models.ForeignKey(
                        help_text='Cart this item belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='items',
                        to='core.cart',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
