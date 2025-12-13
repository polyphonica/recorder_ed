"""
URL configuration for teacher applications and onboarding.
"""
from django.urls import path
from . import views

app_name = 'teacher_applications'

urlpatterns = [
    # Admin portal - application management
    path('admin/', views.application_list, name='list'),
    path('admin/<int:application_id>/', views.application_detail, name='detail'),
    path('admin/<int:application_id>/approve/', views.approve_application, name='approve'),
    path('admin/<int:application_id>/reject/', views.reject_application, name='reject'),
    path('admin/<int:application_id>/on-hold/', views.set_application_on_hold, name='on_hold'),
    path('admin/<int:application_id>/notes/', views.update_application_notes, name='update_notes'),

    # Teacher onboarding
    path('onboarding/', views.onboarding_dashboard, name='onboarding_dashboard'),
    path('onboarding/step/<int:step_number>/', views.onboarding_step, name='onboarding_step'),
]
