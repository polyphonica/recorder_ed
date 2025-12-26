from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # Teacher URLs
    path('teacher/create/', views.assignment_create, name='teacher_create'),
    path('teacher/library/', views.teacher_assignment_library, name='teacher_library'),
    path('teacher/assignment/<uuid:pk>/edit/', views.assignment_edit, name='teacher_edit'),
    path('teacher/assignment/<uuid:pk>/assign/', views.assign_to_student, name='assign_to_student'),
    path('teacher/submissions/', views.teacher_submissions, name='teacher_submissions'),
    path('teacher/submission/<uuid:pk>/grade/', views.grade_submission, name='grade_submission'),

    # Student URLs
    path('student/library/', views.student_assignment_library, name='student_library'),
    path('student/assignment/<uuid:assignment_link_id>/complete/', views.complete_assignment, name='complete_assignment'),
    path('student/assignment/<uuid:assignment_link_id>/submit/', views.submit_assignment, name='submit_assignment'),
    path('student/submission/<uuid:pk>/view/', views.view_graded_assignment, name='view_graded'),
]
