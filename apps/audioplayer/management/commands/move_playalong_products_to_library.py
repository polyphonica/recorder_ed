"""
Move published Digital Products of type "Play-Along" into the free library.

For each one: its collections and pieces become public (where the copyright
lock allows), and the product is archived. People who already have it keep
it in My Purchases, and the old product page redirects to the library page.

Run once, by hand:
    python manage.py move_playalong_products_to_library --dry-run
    python manage.py move_playalong_products_to_library
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.digital_products.models import DigitalProduct


class Command(BaseCommand):
    help = 'Move published play-along products into the free Play-Along Library'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report without changing anything')

    def handle(self, *args, dry_run=False, **options):
        products = DigitalProduct.objects.filter(product_type='play_along', status='published')
        for product in products:
            self.stdout.write(f'Product: {product.title} (£{product.price})')
            with transaction.atomic():
                for link in product.product_collections.select_related('collection'):
                    self._publish(link.collection, dry_run)
                for link in product.product_pieces.select_related('piece'):
                    piece = link.piece
                    if not dry_run:
                        piece.show_in_library = True
                    self._publish(piece, dry_run)
                if not dry_run:
                    product.status = 'archived'
                    product.save(update_fields=['status'])
            self.stdout.write('  archived' if not dry_run else '  would archive')
        self.stdout.write(self.style.SUCCESS(f'{"Would move" if dry_run else "Moved"} {products.count() if dry_run else len(products)} product(s).'))

    def _publish(self, item, dry_run):
        if dry_run:
            self.stdout.write(f'  would make public: {item}')
            return
        item.is_public = True
        item.save()  # the copyright lock keeps in-copyright music without permission private
        item.refresh_from_db()
        state = 'public' if item.is_public else 'KEPT PRIVATE (in copyright without permission)'
        self.stdout.write(f'  {item}: {state}')
