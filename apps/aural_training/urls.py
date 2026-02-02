from django.urls import path, include
from . import views

app_name = 'aural_training'

urlpatterns = [
    # API endpoints
    path('api/', include('apps.aural_training.api.urls')),

    # Student training interface
    path('', views.StudentTrainingView.as_view(), name='student_training'),

    # Student's own progress page
    path('my-progress/', views.StudentProgressView.as_view(), name='student_progress'),
]
