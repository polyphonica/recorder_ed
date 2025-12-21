from django.core.management.base import BaseCommand
from apps.digital_products.models import DigitalProduct, ProductPurchase


class Command(BaseCommand):
    help = 'Recalculate denormalized stats (total_sales) for all digital products'

    def handle(self, *args, **options):
        products = DigitalProduct.objects.all()

        for product in products:
            # Count actual completed purchases
            actual_sales = ProductPurchase.objects.filter(
                product=product,
                payment_status='completed'
            ).count()

            old_count = product.total_sales
            product.total_sales = actual_sales
            product.save(update_fields=['total_sales'])

            self.stdout.write(
                f"{product.title}: {old_count} → {actual_sales} sales"
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nRecalculated sales for {products.count()} products'
        ))
