from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe_webhook'),

    # Finance Dashboard
    path('finance/', views.FinanceDashboardView.as_view(), name='finance_dashboard'),
    path('finance/profit-loss/', views.ProfitLossView.as_view(), name='profit_loss'),
    path('finance/workshops/', views.WorkshopRevenueView.as_view(), name='workshop_revenue'),
    path('finance/courses/', views.CourseRevenueView.as_view(), name='course_revenue'),
    path('finance/private-teaching/', views.PrivateTeachingRevenueView.as_view(), name='private_teaching_revenue'),
    path('finance/private-teaching/by-subject/', views.PrivateTeachingSubjectRevenueView.as_view(), name='private_teaching_subject_revenue'),
]
