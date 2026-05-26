from django.urls import path, include
from . import views

app_name = 'aural_training'

urlpatterns = [
    # API endpoints
    path('api/', include('apps.aural_training.api.urls')),

    # Interval training
    path('', views.StudentTrainingView.as_view(), name='student_training'),
    path('my-progress/', views.StudentProgressView.as_view(), name='student_progress'),

    # Aural tests tab
    path('tests/', views.AuralTestsView.as_view(), name='aural_tests'),

    # Test set CRUD
    path('tests/sets/new/', views.aural_test_set_create, name='test_set_create'),
    path('tests/sets/<uuid:pk>/edit/', views.aural_test_set_edit, name='test_set_edit'),
    path('tests/sets/<uuid:pk>/delete/', views.aural_test_set_delete, name='test_set_delete'),

    # Test CRUD
    path('tests/sets/<uuid:set_pk>/add/', views.aural_test_create, name='test_create'),
    path('tests/<uuid:pk>/edit/', views.aural_test_edit, name='test_edit'),
    path('tests/<uuid:pk>/delete/', views.aural_test_delete, name='test_delete'),

    # Glossary
    path('glossary/', views.GlossaryView.as_view(), name='glossary'),
    path('glossary/new/', views.glossary_term_create, name='glossary_term_create'),
    path('glossary/<uuid:pk>/edit/', views.glossary_term_edit, name='glossary_term_edit'),
    path('glossary/<uuid:pk>/delete/', views.glossary_term_delete, name='glossary_term_delete'),
]
