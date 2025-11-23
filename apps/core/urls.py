from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('components/', views.ComponentShowcaseView.as_view(), name='components'),
    path('forms/', views.FormExampleView.as_view(), name='forms'),
    path('interactive/', views.InteractiveView.as_view(), name='interactive'),
]