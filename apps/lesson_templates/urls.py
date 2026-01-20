from django.urls import path
from . import views

app_name = 'lesson_templates'

urlpatterns = [
    # Library and browsing
    path('', views.template_library, name='library'),

    # Template CRUD operations
    path('create/', views.template_create, name='create'),
    path('<uuid:pk>/edit/', views.template_edit, name='edit'),
    path('<uuid:pk>/preview/', views.template_preview, name='preview'),
    path('<uuid:pk>/delete/', views.template_delete, name='delete'),
    path('<uuid:pk>/duplicate/', views.template_duplicate, name='duplicate'),

    # Category management
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<uuid:pk>/', views.category_detail, name='category_detail'),
    path('categories/<uuid:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<uuid:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/<uuid:pk>/duplicate/', views.category_duplicate, name='category_duplicate'),

    # AJAX endpoints
    path('api/<uuid:pk>/content/', views.get_template_content, name='get_content'),
]
