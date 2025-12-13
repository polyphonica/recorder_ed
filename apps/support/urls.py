from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'support'


def staff_dashboard_redirect(request):
    """Redirect old staff dashboard URL to new admin portal location"""
    return redirect('admin_portal:support:list', permanent=True)


urlpatterns = [
    # Public
    path('contact/', views.public_contact, name='public_contact'),
    path('apply-to-teach/', views.apply_to_teach, name='apply_to_teach'),

    # Authenticated users
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/my/', views.my_tickets, name='my_tickets'),
    path('tickets/<str:ticket_number>/', views.ticket_detail, name='ticket_detail'),

    # Staff (redirects to admin portal)
    path('staff/', staff_dashboard_redirect, name='staff_dashboard'),
    path('staff/ticket/<str:ticket_number>/update/', views.update_ticket, name='update_ticket'),
]
