"""
URL configuration for Creator Studio app.
"""

from django.urls import path
from . import views

app_name = 'creator_studio'

urlpatterns = [
    # Landing Page
    path('', views.CreatorStudioHomeView.as_view(), name='home'),

    # Notation Tools
    path('fingering-diagram/', views.FingeringDiagramCreatorView.as_view(), name='fingering_diagram'),
    path('time-signature/', views.TimeSignatureGeneratorView.as_view(), name='time_signature'),

    # Audio Tools
    path('audio-converter/', views.AudioConverterView.as_view(), name='audio_converter'),
    path('audio-converter/result/', views.AudioConverterResultView.as_view(), name='audio_result'),
    path('audio-converter/download/', views.AudioDownloadView.as_view(), name='audio_download'),
    path('audio-converter/save-as-stem/', views.AudioSaveAsStemView.as_view(), name='audio_save_as_stem'),

    # API Endpoints
    path('api/pieces/search/', views.PieceSearchAPIView.as_view(), name='piece_search_api'),
]
