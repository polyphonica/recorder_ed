"""
URL patterns for Help Center.
"""

from django.urls import path
from . import views

app_name = 'help_center'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category'),
    path('article/<slug:slug>/', views.ArticleDetailView.as_view(), name='article'),
]
