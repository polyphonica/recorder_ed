"""
Admin Portal URL Configuration
"""
from django.urls import path, include
from . import views
from apps.teacher_applications import views as app_views

app_name = 'admin_portal'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('support/', include('apps.admin_portal.urls_support')),

    # Teacher applications admin - inline to avoid namespace issues
    path('applications/', app_views.application_list, name='applications_list'),
    path('applications/<int:application_id>/', app_views.application_detail, name='applications_detail'),
    path('applications/<int:application_id>/approve/', app_views.approve_application, name='applications_approve'),
    path('applications/<int:application_id>/reject/', app_views.reject_application, name='applications_reject'),
    path('applications/<int:application_id>/on-hold/', app_views.set_application_on_hold, name='applications_on_hold'),
    path('applications/<int:application_id>/notes/', app_views.update_application_notes, name='applications_update_notes'),
]
