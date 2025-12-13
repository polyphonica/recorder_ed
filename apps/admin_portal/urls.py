"""
Admin Portal URL Configuration
"""
from django.urls import path, include
from . import views

app_name = 'admin_portal'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('support/', include('apps.admin_portal.urls_support')),
    path('applications/', include('apps.teacher_applications.urls')),
]
