from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    # Teacher: Quiz Library & Management
    path('quizzes/', views.QuizLibraryView.as_view(), name='quiz_library'),
    path('quizzes/create/', views.QuizCreateView.as_view(), name='quiz_create'),
    path('quizzes/<uuid:pk>/', views.QuizDetailView.as_view(), name='quiz_detail'),
    path('quizzes/<uuid:pk>/edit/', views.QuizEditView.as_view(), name='quiz_edit'),
    path('quizzes/<uuid:pk>/delete/', views.QuizDeleteView.as_view(), name='quiz_delete'),
    path('quizzes/<uuid:pk>/duplicate/', views.QuizDuplicateView.as_view(), name='quiz_duplicate'),

    # Teacher: Question Management
    path('quizzes/<uuid:quiz_id>/questions/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/<uuid:pk>/edit/', views.QuestionEditView.as_view(), name='question_edit'),
    path('questions/<uuid:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),

    # Teacher: Quiz Assignments
    path('quizzes/<uuid:quiz_id>/assign/', views.QuizAssignView.as_view(), name='quiz_assign'),
    path('quiz-assignments/', views.QuizAssignmentListView.as_view(), name='quiz_assignment_list'),
    path('quiz-assignments/<uuid:pk>/', views.QuizAssignmentDetailView.as_view(), name='quiz_assignment_detail'),
    path('quiz-assignments/<uuid:pk>/delete/', views.QuizAssignmentDeleteView.as_view(), name='quiz_assignment_delete'),
    path('teacher/quiz-attempts/<uuid:pk>/results/', views.TeacherQuizAttemptResultsView.as_view(), name='teacher_quiz_attempt_results'),

    # Student: Quiz Taking
    path('my-quizzes/', views.StudentQuizListView.as_view(), name='student_quiz_list'),
    path('quiz-assignments/<uuid:assignment_id>/take/', views.QuizTakeView.as_view(), name='quiz_take'),
    path('quiz-assignments/<uuid:assignment_id>/submit/', views.QuizSubmitView.as_view(), name='quiz_submit'),
    path('quiz-assignments/<uuid:assignment_id>/autosave/', views.QuizAutoSaveView.as_view(), name='quiz_autosave'),
    path('quiz-attempts/<uuid:pk>/results/', views.QuizAttemptResultsView.as_view(), name='quiz_attempt_results'),
]
