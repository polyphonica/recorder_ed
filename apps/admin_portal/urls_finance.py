"""
Admin Portal Finance URL Configuration
"""
from django.urls import path
from . import finance_views

app_name = 'finance'

urlpatterns = [
    path('', finance_views.platform_finance_dashboard, name='dashboard'),
    path('revenue/', finance_views.platform_revenue_detail, name='revenue_detail'),
    path('stripe-fees/', finance_views.stripe_fees_detail, name='stripe_fees'),
    path('expenses/', finance_views.platform_expenses_list, name='expenses'),
]
