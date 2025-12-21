"""
Management command to create initial product categories for digital products.
Usage: python manage.py create_product_categories
"""
from django.core.management.base import BaseCommand
from apps.digital_products.models import ProductCategory


class Command(BaseCommand):
    help = 'Create initial product categories for digital products'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Sheet Music',
                'slug': 'sheet-music',
                'description': 'Individual pieces and collections of sheet music in PDF format',
                'icon': '🎼',
                'color': '#3B82F6',
                'order': 0
            },
            {
                'name': 'Practice Materials',
                'slug': 'practice-materials',
                'description': 'Exercises, etudes, and practice guides for skill development',
                'icon': '📝',
                'color': '#10B981',
                'order': 1
            },
            {
                'name': 'Audio Recordings',
                'slug': 'audio',
                'description': 'Audio files including performances and accompaniment tracks',
                'icon': '🎵',
                'color': '#F59E0B',
                'order': 2
            },
            {
                'name': 'Video Tutorials',
                'slug': 'video',
                'description': 'Instructional videos and masterclasses',
                'icon': '🎬',
                'color': '#EF4444',
                'order': 3
            },
            {
                'name': 'Research & Articles',
                'slug': 'research',
                'description': 'Academic papers, articles, and educational resources',
                'icon': '📚',
                'color': '#8B5CF6',
                'order': 4
            },
            {
                'name': 'Method Books',
                'slug': 'method-books',
                'description': 'Comprehensive method books and instructional materials',
                'icon': '📖',
                'color': '#EC4899',
                'order': 5
            },
            {
                'name': 'Ensemble Parts',
                'slug': 'ensemble',
                'description': 'Parts for duets, trios, quartets, and larger ensembles',
                'icon': '👥',
                'color': '#14B8A6',
                'order': 6
            },
            {
                'name': 'Bundles',
                'slug': 'bundles',
                'description': 'Curated collections of multiple resources',
                'icon': '📦',
                'color': '#6366F1',
                'order': 7
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories:
            category, created = ProductCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created category: {category.name}")
                )
            else:
                # Update existing category with new data
                for key, value in cat_data.items():
                    if key != 'slug':  # Don't update the slug
                        setattr(category, key, value)
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"⟳ Updated category: {category.name}")
                )

        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Done! Created {created_count} categories, updated {updated_count} categories.\n"
            )
        )
