from django.urls import path
from . import views
from .views_audio_upload import audio_upload

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy'),
    path('terms/', views.TermsConditionsView.as_view(), name='terms'),
    path('components/', views.ComponentShowcaseView.as_view(), name='components'),
    path('forms/', views.FormExampleView.as_view(), name='forms'),
    path('interactive/', views.InteractiveView.as_view(), name='interactive'),
    path('audio-upload/', audio_upload, name='audio_upload'),
]