"""
URL configuration for teacher applications.
"""
from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.application_list, name='list'),
    path('<int:application_id>/', views.application_detail, name='detail'),
    path('<int:application_id>/approve/', views.approve_application, name='approve'),
    path('<int:application_id>/reject/', views.reject_application, name='reject'),
    path('<int:application_id>/on-hold/', views.set_application_on_hold, name='on_hold'),
    path('<int:application_id>/notes/', views.update_application_notes, name='update_notes'),
]
