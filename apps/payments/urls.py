from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Cart management
    path('', views.CartView.as_view(), name='cart'),
    path('add/<uuid:session_id>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('remove/<int:item_id>/', views.RemoveFromCartView.as_view(), name='remove_from_cart'),
    
    # Checkout process
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('confirmation/<uuid:order_id>/', views.OrderConfirmationView.as_view(), name='order_confirmation'),
    
    # Ajax endpoints
    path('cart-count/', views.CartCountView.as_view(), name='cart_count'),
]