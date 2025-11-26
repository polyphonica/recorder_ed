"""
Views for Help Center.
"""

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.views.generic import ListView, DetailView
from .models import Category, Article


def home(request):
    """
    Help center homepage with category grid and promoted articles.
    """
    categories = Category.objects.filter(is_active=True).prefetch_related('articles')
    promoted_articles = Article.objects.filter(
        status='published',
        is_promoted=True
    ).select_related('category')[:9]  # Show max 9 promoted articles

    context = {
        'categories': categories,
        'promoted_articles': promoted_articles,
    }
    return render(request, 'help_center/home.html', context)


class CategoryDetailView(DetailView):
    """
    Display all articles in a category.
    """
    model = Category
    template_name = 'help_center/category_detail.html'
    context_object_name = 'category'

    def get_queryset(self):
        return Category.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = Article.objects.filter(
            category=self.object,
            status='published'
        ).order_by('order', '-created_at')
        return context


class ArticleDetailView(DetailView):
    """
    Display article content and increment view count.
    """
    model = Article
    template_name = 'help_center/article_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        return Article.objects.filter(status='published').select_related('category')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        obj.increment_view_count()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get related articles from same category
        context['related_articles'] = Article.objects.filter(
            category=self.object.category,
            status='published'
        ).exclude(pk=self.object.pk)[:5]
        return context


class SearchView(ListView):
    """
    Search articles by title and content.
    """
    model = Article
    template_name = 'help_center/search_results.html'
    context_object_name = 'articles'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if not query:
            return Article.objects.none()

        return Article.objects.filter(
            Q(title__icontains=query) |
            Q(summary__icontains=query) |
            Q(content__icontains=query),
            status='published'
        ).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context
