"""
XML Sitemap configuration for SEO
Helps search engines discover and index all public pages
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.workshops.models import Workshop
from apps.courses.models import Course
from django.db.models import Q
from apps.audioplayer.models import Composer, Piece, PieceCollection


class StaticViewSitemap(Sitemap):
    """Static pages sitemap"""
    priority = 1.0
    changefreq = 'monthly'

    def items(self):
        return [
            'domain_selector',  # Homepage
            'workshops:list',
            'courses:list',
            'private_teaching:home',
            'playalongs:home',
            'playalongs:library',
            'playalongs:editions',
        ]

    def location(self, item):
        return reverse(item)


class WorkshopSitemap(Sitemap):
    """Workshop pages sitemap"""
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Workshop.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('workshops:detail', kwargs={'slug': obj.slug})


class CourseSitemap(Sitemap):
    """Course pages sitemap"""
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Course.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('courses:detail', kwargs={'slug': obj.slug})


class PlayalongPieceSitemap(Sitemap):
    """Public play-along pieces listed in the library"""
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Piece.objects.filter(is_public=True, show_in_library=True).order_by('pk')

    def lastmod(self, obj):
        return obj.updated_at


class PlayalongCollectionSitemap(Sitemap):
    """Public play-along collections"""
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return PieceCollection.objects.filter(is_public=True).order_by('pk')

    def lastmod(self, obj):
        return obj.updated_at


class PlayalongComposerSitemap(Sitemap):
    """Composers with something public in the library"""
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Composer.objects.filter(
            Q(pieces__is_public=True, pieces__show_in_library=True) |
            Q(pieces__collection_memberships__collection__is_public=True)
        ).distinct().order_by('pk')

    def lastmod(self, obj):
        return obj.updated_at


# Dictionary of all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'workshops': WorkshopSitemap,
    'courses': CourseSitemap,
    'playalong_pieces': PlayalongPieceSitemap,
    'playalong_collections': PlayalongCollectionSitemap,
    'playalong_composers': PlayalongComposerSitemap,
}
