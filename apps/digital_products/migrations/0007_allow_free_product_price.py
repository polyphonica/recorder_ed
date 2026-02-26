from decimal import Decimal
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('digital_products', '0006_add_digital_product_piece_collection'),
    ]

    operations = [
        migrations.AlterField(
            model_name='digitalproduct',
            name='price',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]
            ),
        ),
    ]
