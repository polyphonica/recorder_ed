from django.urls import path, include
from . import views

app_name = 'scheduling'

urlpatterns = [
    # API endpoints
    path('api/', include('apps.scheduling.api.urls')),

    # Web views
    path('teacher/availability/', views.TeacherAvailabilityEditorView.as_view(), name='teacher_availability'),
]
