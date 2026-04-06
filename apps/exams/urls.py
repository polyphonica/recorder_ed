from django.urls import path

from . import views

app_name = 'exams'

urlpatterns = [
    # Teacher exam views
    path('exams/', views.ExamRegistrationListView.as_view(), name='exam_list'),
    path('exams/create/', views.ExamRegistrationCreateView.as_view(), name='exam_create'),
    path('exams/<uuid:pk>/', views.ExamRegistrationDetailView.as_view(), name='exam_detail'),
    path('exams/<uuid:pk>/edit/', views.ExamRegistrationUpdateView.as_view(), name='exam_edit'),
    path('exams/<uuid:pk>/delete/', views.ExamRegistrationDeleteView.as_view(), name='exam_delete'),
    path('exams/<uuid:pk>/results/', views.ExamResultsUpdateView.as_view(), name='exam_results'),
    path('exams/<uuid:pk>/pdf/', views.ExamProgrammePDFView.as_view(), name='exam_pdf'),

    # Student exam views
    path('my-exams/', views.StudentExamListView.as_view(), name='student_exams'),
    path('exams/<uuid:pk>/approve/', views.ExamProgrammeApproveView.as_view(), name='exam_approve'),

    # Payment views
    path('exams/<uuid:pk>/pay/', views.ExamPaymentView.as_view(), name='exam_payment'),
    path('exams/<uuid:pk>/payment/success/', views.ExamPaymentSuccessView.as_view(), name='exam_payment_success'),
    path('exams/<uuid:pk>/payment/cancel/', views.ExamPaymentCancelView.as_view(), name='exam_payment_cancel'),
]
