from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .revenue_views import TeacherRevenueDashboardView, TeacherRevenueExportView

app_name = 'accounts'

urlpatterns = [
    # Custom login view with role-based redirects
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # Teacher revenue dashboard
    path('teacher/revenue/', TeacherRevenueDashboardView.as_view(), name='teacher_revenue'),
    path('teacher/revenue/export/', TeacherRevenueExportView.as_view(), name='teacher_revenue_export'),

    # Public teacher profile (no login required)
    path('teacher/<int:teacher_id>/', views.TeacherPublicProfileView.as_view(), name='teacher_profile'),

    # Guardian dashboard for managing children
    path('guardian/dashboard/', views.guardian_dashboard_view, name='guardian_dashboard'),
    path('guardian/child/add/', views.add_child_view, name='add_child'),
    path('guardian/child/<uuid:child_id>/edit/', views.edit_child_view, name='edit_child'),
    path('guardian/child/<uuid:child_id>/delete/', views.delete_child_view, name='delete_child'),

    # Account transfer for 18+ children
    path('transfer/<uuid:child_id>/', views.transfer_account_view, name='transfer_account'),
]