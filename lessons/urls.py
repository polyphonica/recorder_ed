from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    # Calendar view
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    
    # Lesson CRUD
    path('', views.LessonListView.as_view(), name='lesson_list'),
    path('<uuid:pk>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    path('<uuid:pk>/edit/', views.LessonUpdateView.as_view(), name='lesson_update'),

    # API endpoints
    path('api/calendar-events/', views.calendar_events_api, name='calendar_events_api'),
    path('api/<uuid:lesson_id>/previous-homework/', views.get_previous_homework, name='get_previous_homework'),
]