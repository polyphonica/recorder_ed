"""
Support ticket management URLs for admin portal.
Reuses existing support views but integrates into admin portal.
"""
from django.urls import path
from apps.support import views as support_views

app_name = 'support'

urlpatterns = [
    path('', support_views.staff_dashboard, name='list'),
    path('<str:ticket_number>/', support_views.ticket_detail, name='detail'),
    path('<str:ticket_number>/update/', support_views.update_ticket, name='update'),
]
