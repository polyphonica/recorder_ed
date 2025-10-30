from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
]
