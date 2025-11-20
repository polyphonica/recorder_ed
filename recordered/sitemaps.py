"""
XML Sitemap configuration for SEO
Helps search engines discover and index all public pages
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.workshops.models import Workshop
from apps.courses.models import Course


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
        ]

    def location(self, item):
        return reverse(item)


class WorkshopSitemap(Sitemap):
    """Workshop pages sitemap"""
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Workshop.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('workshops:detail', kwargs={'slug': obj.slug})


class CourseSitemap(Sitemap):
    """Course pages sitemap"""
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Course.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('courses:detail', kwargs={'slug': obj.slug})


# Dictionary of all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'workshops': WorkshopSitemap,
    'courses': CourseSitemap,
}
