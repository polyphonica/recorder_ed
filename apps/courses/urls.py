"""
URL configuration for courses app.
"""

from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # ========================================================================
    # INSTRUCTOR URLs - Course Management
    # ========================================================================

    # Instructor Dashboard
    path('instructor/dashboard/', views.InstructorDashboardView.as_view(), name='instructor_dashboard'),

    # Course CRUD
    path('instructor/create/', views.CourseCreateView.as_view(), name='create'),
    path('instructor/<slug:slug>/edit/', views.CourseUpdateView.as_view(), name='edit'),
    path('instructor/<slug:slug>/delete/', views.CourseDeleteView.as_view(), name='delete'),

    # Topic Management
    path('instructor/<slug:slug>/topics/', views.TopicManageView.as_view(), name='manage_topics'),
    path('instructor/<slug:slug>/topics/create/', views.TopicCreateView.as_view(), name='create_topic'),
    path('instructor/topics/<uuid:topic_id>/update/', views.TopicUpdateView.as_view(), name='update_topic'),
    path('instructor/topics/<uuid:topic_id>/delete/', views.TopicDeleteView.as_view(), name='delete_topic'),

    # Lesson Management
    path('instructor/<slug:course_slug>/topic/<int:topic_number>/lessons/',
         views.LessonManageView.as_view(), name='manage_lessons'),
    path('instructor/<slug:course_slug>/topic/<int:topic_number>/lessons/create/',
         views.LessonCreateView.as_view(), name='create_lesson'),
    path('instructor/lessons/<uuid:pk>/edit/',
         views.LessonUpdateView.as_view(), name='edit_lesson'),
    path('instructor/lessons/<uuid:pk>/delete/',
         views.LessonDeleteView.as_view(), name='delete_lesson'),

    # Quiz Management
    path('instructor/lessons/<uuid:lesson_id>/quiz/',
         views.QuizManageView.as_view(), name='manage_quiz'),
    path('instructor/quiz/<uuid:quiz_id>/update/',
         views.QuizUpdateView.as_view(), name='update_quiz'),
    path('instructor/quiz/<uuid:quiz_id>/question/create/',
         views.QuizQuestionCreateView.as_view(), name='create_question'),
    path('instructor/question/<uuid:question_id>/update/',
         views.QuizQuestionUpdateView.as_view(), name='update_question'),
    path('instructor/question/<uuid:question_id>/delete/',
         views.QuizQuestionDeleteView.as_view(), name='delete_question'),

    # Analytics
    path('instructor/analytics/', views.CourseAnalyticsView.as_view(), name='analytics'),
    path('instructor/<slug:slug>/analytics/', views.CourseStudentListView.as_view(), name='course_analytics'),
    path('instructor/<slug:course_slug>/student/<int:student_id>/',
         views.StudentProgressDetailView.as_view(), name='student_progress'),

    # ========================================================================
    # STUDENT URLs - Learning (must come before slug patterns!)
    # ========================================================================

    path('my-courses/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('my-progress/<slug:slug>/', views.StudentCourseProgressView.as_view(), name='my_progress'),
    path('lesson/<uuid:lesson_id>/', views.LessonViewView.as_view(), name='view_lesson'),
    path('lesson/<uuid:lesson_id>/complete/', views.MarkLessonCompleteView.as_view(), name='mark_complete'),
    path('lesson/<uuid:lesson_id>/quiz/', views.QuizTakeView.as_view(), name='take_quiz'),
    path('lesson/<uuid:lesson_id>/quiz/submit/', views.QuizSubmitView.as_view(), name='submit_quiz'),

    # Messaging
    path('messages/', views.MessageInboxView.as_view(), name='messages_inbox'),
    path('messages/compose/<uuid:lesson_id>/', views.MessageComposeView.as_view(), name='message_compose'),
    path('messages/<uuid:message_id>/', views.MessageThreadView.as_view(), name='message_thread'),

    # ========================================================================
    # PUBLIC URLs - Course Browsing
    # ========================================================================

    path('', views.CourseListView.as_view(), name='list'),
    path('<slug:slug>/', views.CourseDetailView.as_view(), name='detail'),
    path('<slug:slug>/enroll/', views.CourseEnrollView.as_view(), name='enroll'),
]
