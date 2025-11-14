from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # Public
    path('contact/', views.public_contact, name='public_contact'),

    # Authenticated users
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/my/', views.my_tickets, name='my_tickets'),
    path('tickets/<str:ticket_number>/', views.ticket_detail, name='ticket_detail'),

    # Staff
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/ticket/<str:ticket_number>/update/', views.update_ticket, name='update_ticket'),
]
