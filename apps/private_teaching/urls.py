from django.urls import path
from . import views

app_name = 'private_teaching'

urlpatterns = [
    path('', views.PrivateTeachingHomeView.as_view(), name='home'),
    path('terms-and-conditions/', views.PrivateLessonTermsView.as_view(), name='terms'),
    path('login/', views.PrivateTeachingLoginView.as_view(), name='login'),
    # path('register/', views.student_register, name='register'),  # REMOVED: Use unified /accounts/signup/
    path('profile/complete/', views.ProfileCompleteView.as_view(), name='profile_complete'),
    path('teacher/profile/complete/', views.TeacherProfileCompleteView.as_view(), name='teacher_profile_complete'),

    # Student Views
    path('dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('request/', views.LessonRequestCreateView.as_view(), name='request_lesson'),
    path('my-requests/', views.MyLessonRequestsView.as_view(), name='my_requests'),
    path('my-requests/<int:request_id>/', views.StudentLessonRequestDetailView.as_view(), name='student_request_detail'),
    path('my-lessons/', views.MyLessonsView.as_view(), name='my_lessons'),
    path('library/', views.StudentDocumentLibraryView.as_view(), name='student_library'),
    
    # Teacher Views
    path('teacher/dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('teacher/settings/', views.TeacherSettingsView.as_view(), name='teacher_settings'),
    path('teacher/settings/zoom-link/', views.UpdateZoomLinkView.as_view(), name='update_zoom_link'),
    path('teacher/subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('teacher/subjects/<int:subject_id>/update/', views.SubjectUpdateView.as_view(), name='subject_update'),
    path('teacher/subjects/<int:subject_id>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
    path('teacher/subjects/reorder/', views.SubjectReorderView.as_view(), name='subject_reorder'),
    path('teacher/incoming-requests/', views.IncomingRequestsView.as_view(), name='incoming_requests'),
    path('teacher/request/<int:request_id>/', views.LessonRequestDetailView.as_view(), name='lesson_request_detail'),
    path('teacher/schedule/', views.TeacherScheduleView.as_view(), name='teacher_schedule'),
    path('teacher/action/<int:request_id>/', views.ActionRequestView.as_view(), name='action_request'),
    path('teacher/bulk-action/', views.BulkActionView.as_view(), name='bulk_action'),
    path('teacher/library/', views.TeacherDocumentLibraryView.as_view(), name='teacher_library'),
    path('teacher/students/', views.TeacherStudentsListView.as_view(), name='teacher_students'),
    path('teacher/students/<int:student_id>/contact/', views.StudentContactDetailView.as_view(), name='student_contact_detail'),
    
    # Cart Views
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<uuid:lesson_id>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('cart/add-all/<int:lesson_request_id>/', views.AddAllToCartView.as_view(), name='add_all_to_cart'),
    path('cart/remove/<uuid:lesson_id>/', views.RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('cart/clear/', views.ClearCartView.as_view(), name='clear_cart'),
    path('payment/process/', views.ProcessPaymentView.as_view(), name='process_payment'),
    path('payment/success/<int:order_id>/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('checkout/success/<int:order_id>/', views.CheckoutSuccessView.as_view(), name='checkout_success'),
    path('checkout/cancel/<int:order_id>/', views.CheckoutCancelView.as_view(), name='checkout_cancel'),

    # Shared Views
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('lesson/<uuid:lesson_id>/details/', views.LessonDetailView.as_view(), name='lesson_detail'),

    # Student Application Views
    path('apply/<int:teacher_id>/', views.ApplyToTeacherView.as_view(), name='apply_to_teacher'),
    path('my-applications/', views.StudentApplicationsListView.as_view(), name='student_applications'),
    path('my-applications/<uuid:application_id>/', views.StudentApplicationDetailView.as_view(), name='student_application_detail'),

    # Teacher Application Management Views
    path('teacher/applications/', views.TeacherApplicationsListView.as_view(), name='teacher_applications'),
    path('teacher/applications/<uuid:application_id>/', views.TeacherApplicationDetailView.as_view(), name='teacher_application_detail'),
    path('teacher/capacity/update/', views.UpdateTeacherCapacityView.as_view(), name='update_teacher_capacity'),

    # Exam Registration Views (Teacher)
    path('exams/', views.ExamRegistrationListView.as_view(), name='exam_list'),
    path('exams/create/', views.ExamRegistrationCreateView.as_view(), name='exam_create'),
    path('exams/<uuid:pk>/', views.ExamRegistrationDetailView.as_view(), name='exam_detail'),
    path('exams/<uuid:pk>/edit/', views.ExamRegistrationUpdateView.as_view(), name='exam_edit'),
    path('exams/<uuid:pk>/delete/', views.ExamRegistrationDeleteView.as_view(), name='exam_delete'),
    path('exams/<uuid:pk>/results/', views.ExamResultsUpdateView.as_view(), name='exam_results'),

    # Exam Views (Student)
    path('my-exams/', views.StudentExamListView.as_view(), name='student_exams'),

    # Exam Payment Views
    path('exams/<uuid:pk>/pay/', views.ExamPaymentView.as_view(), name='exam_payment'),
    path('exams/<uuid:pk>/payment/success/', views.ExamPaymentSuccessView.as_view(), name='exam_payment_success'),
    path('exams/<uuid:pk>/payment/cancel/', views.ExamPaymentCancelView.as_view(), name='exam_payment_cancel'),

    # Lesson Cancellation Views
    path('lesson/<uuid:lesson_id>/cancel/', views.RequestLessonCancellationView.as_view(), name='request_cancellation'),
    path('cancellation-request/<int:request_id>/', views.CancellationRequestDetailView.as_view(), name='cancellation_request_detail'),
    path('teacher/cancellation-requests/', views.TeacherCancellationRequestsView.as_view(), name='teacher_cancellation_requests'),
    path('teacher/cancellation-requests/<int:request_id>/respond/', views.TeacherRespondToCancellationView.as_view(), name='teacher_respond_cancellation'),

    # Practice Diary Views
    path('practice/log/', views.LogPracticeView.as_view(), name='log_practice'),
    path('practice/', views.PracticeLogView.as_view(), name='practice_log'),
    path('teacher/students/<int:student_id>/practice/', views.TeacherStudentPracticeView.as_view(), name='teacher_student_practice'),
    path('teacher/practice/<uuid:entry_id>/comment/', views.AddPracticeCommentView.as_view(), name='add_practice_comment'),
]
