from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from .models import ShoppingCart, CartItem, Order, OrderItem, Transaction
from apps.workshops.models import WorkshopSession, WorkshopRegistration


class CartView(LoginRequiredMixin, TemplateView):
    """Display the user's shopping cart"""
    template_name = 'payments/cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create cart for the user
        cart, created = ShoppingCart.objects.get_or_create(user=self.request.user)
        
        context.update({
            'cart': cart,
            'cart_items': cart.items.select_related('session__workshop').all(),
            'total_amount': cart.total_amount,
        })
        return context


class AddToCartView(LoginRequiredMixin, View):
    """Add a workshop session to the user's cart"""
    
    def post(self, request, session_id):
        session = get_object_or_404(WorkshopSession, id=session_id)
        
        # Check if user is already registered for this session
        if WorkshopRegistration.objects.filter(student=request.user, session=session).exists():
            messages.warning(request, f"You are already registered for {session.workshop.title}")
            return redirect('workshops:detail', slug=session.workshop.slug)
        
        # Get or create cart
        cart, created = ShoppingCart.objects.get_or_create(user=request.user)
        
        # Try to add session to cart
        cart_item, created = cart.add_session(session)
        
        if created:
            messages.success(request, f"{session.workshop.title} added to your cart")
        else:
            messages.info(request, f"{session.workshop.title} is already in your cart")
        
        # Redirect back to the workshop detail page
        return redirect('workshops:detail', slug=session.workshop.slug)


class RemoveFromCartView(LoginRequiredMixin, View):
    """Remove an item from the user's cart"""
    
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        workshop_title = cart_item.session.workshop.title
        cart_item.delete()
        
        messages.success(request, f"{workshop_title} removed from your cart")
        return redirect('payments:cart')


class CheckoutView(LoginRequiredMixin, View):
    """Process checkout and create registrations"""
    
    def get(self, request):
        """Display checkout page"""
        cart = get_object_or_404(ShoppingCart, user=request.user)
        
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('payments:cart')
        
        context = {
            'cart': cart,
            'cart_items': cart.items.select_related('session__workshop').all(),
            'total_amount': cart.total_amount,
        }
        return render(request, 'payments/checkout.html', context)
    
    def post(self, request):
        """Process the checkout (mock payment for now)"""
        cart = get_object_or_404(ShoppingCart, user=request.user)
        
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('payments:cart')
        
        try:
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=cart.total_amount,
                    status='completed'  # Mock payment always succeeds
                )
                
                # Create order items and registrations
                for cart_item in cart.items.all():
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        session=cart_item.session,
                        price=cart_item.price
                    )
                    
                    # Create workshop registration
                    WorkshopRegistration.objects.create(
                        student=request.user,
                        session=cart_item.session,
                        status='registered',
                        registration_date=timezone.now()
                    )
                
                # Create mock transaction
                Transaction.objects.create(
                    order=order,
                    amount=order.total_amount,
                    status='completed',
                    payment_method='mock',
                    transaction_id=f"mock_{order.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
                )
                
                # Clear the cart
                cart.clear()
                
                messages.success(request, f"Payment successful! You are now registered for {order.session_count} workshop session(s).")
                return redirect('payments:order_confirmation', order_id=order.id)
                
        except Exception as e:
            messages.error(request, "There was an error processing your payment. Please try again.")
            return redirect('payments:checkout')


class OrderConfirmationView(LoginRequiredMixin, TemplateView):
    """Display order confirmation page"""
    template_name = 'payments/order_confirmation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        order = get_object_or_404(Order, id=kwargs['order_id'], user=self.request.user)
        
        context.update({
            'order': order,
            'order_items': order.items.select_related('session__workshop').all(),
        })
        return context


# Ajax view for updating cart count in header
class CartCountView(LoginRequiredMixin, View):
    """Return cart item count as JSON"""
    
    def get(self, request):
        try:
            cart = ShoppingCart.objects.get(user=request.user)
            count = cart.item_count
        except ShoppingCart.DoesNotExist:
            count = 0
        
        return JsonResponse({'count': count})