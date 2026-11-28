"""Public Play-Along Library pages, mounted at /playalongs/."""
from django.urls import path

from . import public_views
from .views import PlayAlongLibraryView

app_name = 'playalongs'

urlpatterns = [
    path('', public_views.library_home, name='home'),
    path('library/', PlayAlongLibraryView.as_view(), name='library'),
    path('editions/', public_views.editions_page, name='editions'),
    path('piece/<slug:slug>/', public_views.piece_page, name='piece'),
    path('collection/<slug:slug>/', public_views.collection_page, name='collection'),
    path('composer/<slug:slug>/', public_views.composer_page, name='composer'),
]
