from django.urls import path

from . import views

app_name = 'practice'

urlpatterns = [
    path('practice/log/', views.LogPracticeView.as_view(), name='log_practice'),
    path('practice/', views.PracticeLogView.as_view(), name='practice_log'),
    path('practice/print/', views.PracticeLogPrintView.as_view(), name='practice_log_print'),
    path('practice/<uuid:pk>/edit/', views.EditPracticeView.as_view(), name='edit_practice'),
    path('practice/<uuid:pk>/delete/', views.DeletePracticeView.as_view(), name='delete_practice'),
    path('teacher/students/<int:student_id>/practice/', views.TeacherStudentPracticeView.as_view(), name='teacher_student_practice'),
    path('teacher/practice/<uuid:entry_id>/comment/', views.AddPracticeCommentView.as_view(), name='add_practice_comment'),
]
