from django.urls import path
from . import views

app_name = 'lesson_templates'

urlpatterns = [
    # Library and browsing
    path('', views.template_library, name='library'),

    # CRUD operations
    path('create/', views.template_create, name='create'),
    path('<uuid:pk>/edit/', views.template_edit, name='edit'),
    path('<uuid:pk>/preview/', views.template_preview, name='preview'),
    path('<uuid:pk>/delete/', views.template_delete, name='delete'),
    path('<uuid:pk>/duplicate/', views.template_duplicate, name='duplicate'),

    # AJAX endpoints
    path('api/<uuid:pk>/content/', views.get_template_content, name='get_content'),
]
