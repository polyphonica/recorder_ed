"""
State-only migration: update DigitalProductCartItem.cart FK from
private_teaching.Cart to core.Cart.

No database operations — the 'private_teaching_cart' table is unchanged.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_cart'),
        ('digital_products', '0004_alter_productpurchase_child_profile'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='digitalproductcartitem',
                    name='cart',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='digital_product_items',
                        to='core.cart',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
