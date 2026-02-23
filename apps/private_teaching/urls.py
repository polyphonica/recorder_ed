from django.urls import path, include
from . import views

app_name = 'private_teaching'

urlpatterns = [
    # Web views
    path('', views.PrivateTeachingHomeView.as_view(), name='home'),
    path('terms-and-conditions/', views.PrivateLessonTermsView.as_view(), name='terms'),
    path('login/', views.PrivateTeachingLoginView.as_view(), name='login'),
    path('profile/complete/', views.ProfileCompleteView.as_view(), name='profile_complete'),
    path('teacher/profile/complete/', views.TeacherProfileCompleteView.as_view(), name='teacher_profile_complete'),

    # Student Views
    path('dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('request/', views.RedirectToMyTeachersView.as_view(), name='request_lesson'),  # Redirect old URL to new system
    path('book/<int:teacher_id>/', views.BookWithTeacherView.as_view(), name='book_with_teacher'),
    path('my-requests/', views.MyLessonRequestsView.as_view(), name='my_requests'),
    path('my-requests/<int:request_id>/', views.StudentLessonRequestDetailView.as_view(), name='student_request_detail'),
    path('lesson/<uuid:lesson_id>/delete/', views.delete_lesson_from_request, name='delete_lesson_from_request'),
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

    # Voucher Management
    path('teacher/vouchers/', views.VoucherListView.as_view(), name='voucher_list'),
    path('teacher/vouchers/create/', views.VoucherCreateView.as_view(), name='voucher_create'),
    path('teacher/vouchers/<uuid:pk>/', views.VoucherDetailView.as_view(), name='voucher_detail'),
    path('teacher/vouchers/<uuid:pk>/update/', views.VoucherUpdateView.as_view(), name='voucher_update'),
    path('teacher/vouchers/<uuid:pk>/delete/', views.VoucherDeleteView.as_view(), name='voucher_delete'),
    path('teacher/vouchers/<uuid:pk>/toggle/', views.VoucherToggleStatusView.as_view(), name='voucher_toggle'),

    path('teacher/incoming-requests/', views.IncomingRequestsView.as_view(), name='incoming_requests'),
    path('teacher/request/<int:request_id>/', views.LessonRequestDetailView.as_view(), name='lesson_request_detail'),
    path('teacher/schedule/', views.TeacherScheduleView.as_view(), name='teacher_schedule'),
    path('teacher/action/<int:request_id>/', views.ActionRequestView.as_view(), name='action_request'),
    path('teacher/bulk-action/', views.BulkActionView.as_view(), name='bulk_action'),
    path('teacher/library/', views.TeacherDocumentLibraryView.as_view(), name='teacher_library'),
    path('teacher/students/', views.TeacherStudentsListView.as_view(), name='teacher_students'),
    path('teacher/students/<int:student_id>/progress/', views.TeacherStudentProgressView.as_view(), name='teacher_student_progress'),
    path('teacher/students/<int:student_id>/contact/', views.StudentContactDetailView.as_view(), name='student_contact_detail'),
    path('teacher/students/<int:student_id>/assign-playalong/', views.AssignPlayalongView.as_view(), name='assign_playalong'),
    path('teacher/students/<int:student_id>/remove-playalong/<uuid:assignment_id>/', views.RemovePlayalongAssignmentView.as_view(), name='remove_playalong'),
    path('teacher/students/<int:student_id>/playalong-status/<uuid:assignment_id>/', views.UpdatePlayalongStatusView.as_view(), name='update_playalong_status'),
    path('teacher/lessons/<uuid:lesson_id>/', views.TeacherLessonDetailView.as_view(), name='teacher_lesson_detail'),

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
    path('my-teachers/', views.MyTeachersView.as_view(), name='my_teachers'),

    # Teacher Application Management Views
    path('teacher/applications/', views.TeacherApplicationsListView.as_view(), name='teacher_applications'),
    path('teacher/applications/<uuid:application_id>/', views.TeacherApplicationDetailView.as_view(), name='teacher_application_detail'),
    path('teacher/capacity/update/', views.UpdateTeacherCapacityView.as_view(), name='update_teacher_capacity'),

    # Lesson Cancellation Views
    path('lesson/<uuid:lesson_id>/cancel/', views.RequestLessonCancellationView.as_view(), name='request_cancellation'),
    path('lesson/<uuid:lesson_id>/teacher-cancel/', views.TeacherInitiateCancellationView.as_view(), name='teacher_initiate_cancellation'),
    path('cancellation-request/<int:request_id>/', views.CancellationRequestDetailView.as_view(), name='cancellation_request_detail'),
    path('cancellation-request/<int:request_id>/student-respond/', views.StudentRespondToTeacherRescheduleView.as_view(), name='student_respond_to_cancellation'),
    path('teacher/cancellation-requests/', views.TeacherCancellationRequestsView.as_view(), name='teacher_cancellation_requests'),
    path('teacher/cancellation-requests/<int:request_id>/respond/', views.TeacherRespondToCancellationView.as_view(), name='teacher_respond_cancellation'),

    # Quiz URLs moved to apps.quizzes.urls
]
