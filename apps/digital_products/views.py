import logging
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages

from apps.core.mixins import InstructorRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse, reverse_lazy
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings

from apps.payments.stripe_service import create_checkout_session_with_items
from apps.payments.utils import calculate_commission

from .models import (
    ProductCategory,
    DigitalProduct,
    ProductFile,
    ProductPurchase,
    ProductReview,
    DigitalProductCartItem
)
from .forms import ProductForm, ProductFileFormSet, ProductReviewForm
from .cart import DigitalProductCartManager

logger = logging.getLogger(__name__)


# ============================================================
# PUBLIC CATALOG VIEWS
# ============================================================

class ProductCatalogView(ListView):
    """Display digital products catalog with category filtering"""
    model = DigitalProduct
    template_name = 'digital_products/catalog.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = DigitalProduct.objects.filter(status='published').select_related(
            'teacher',
            'category'
        ).order_by('-published_at')

        # Category filter
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Search query
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__icontains=search_query)
            )

        # Product type filter
        product_type = self.request.GET.get('type')
        if product_type:
            queryset = queryset.filter(product_type=product_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ProductCategory.objects.filter(is_active=True).order_by('order', 'name')
        context['selected_category'] = self.kwargs.get('category_slug')
        context['search_query'] = self.request.GET.get('q', '')
        context['product_types'] = DigitalProduct.PRODUCT_TYPE_CHOICES
        return context


class ProductDetailView(DetailView):
    """Display product details with preview files"""
    model = DigitalProduct
    template_name = 'digital_products/detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return DigitalProduct.objects.filter(status='published').select_related(
            'teacher',
            'category'
        ).prefetch_related(
            'files',
            'reviews__student'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Check if user is the product owner (teacher)
        if self.request.user.is_authenticated:
            context['is_own_product'] = product.teacher == self.request.user
        else:
            context['is_own_product'] = False

        # Check if user already purchased
        if self.request.user.is_authenticated:
            context['already_purchased'] = ProductPurchase.objects.filter(
                student=self.request.user,
                product=product,
                payment_status='completed'
            ).exists()
        else:
            context['already_purchased'] = False

        # Get main files and preview files
        context['main_files'] = product.main_files
        context['preview_files'] = product.preview_files

        # Get published reviews
        context['reviews'] = product.reviews.filter(is_published=True).select_related('student').order_by('-created_at')

        # Related products (same category)
        if product.category:
            context['related_products'] = DigitalProduct.objects.filter(
                category=product.category,
                status='published'
            ).exclude(id=product.id).select_related('teacher')[:4]

        return context


# ============================================================
# CART VIEWS
# ============================================================

class CartView(LoginRequiredMixin, View):
    """Display shopping cart"""
    template_name = 'digital_products/cart.html'

    def get(self, request):
        cart_manager = DigitalProductCartManager(request)
        cart_context = cart_manager.get_cart_context()
        return render(request, self.template_name, cart_context)


@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    cart_manager = DigitalProductCartManager(request)
    success, message = cart_manager.add_product(product_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    # Redirect back to product detail or catalog
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('digital_products:cart')


@login_required
def remove_from_cart(request, product_id):
    """Remove product from cart"""
    cart_manager = DigitalProductCartManager(request)
    success, message = cart_manager.remove_product(product_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('digital_products:cart')


# ============================================================
# CHECKOUT VIEWS
# ============================================================

class ProductCheckoutView(LoginRequiredMixin, View):
    """Handle checkout for digital products (single or cart)"""

    def post(self, request):
        # Determine checkout mode: single product or cart
        product_id = request.POST.get('product_id')
        checkout_cart = request.POST.get('checkout_cart')

        if product_id:
            # Single product checkout
            product = get_object_or_404(DigitalProduct, id=product_id, status='published')

            # Check if already purchased
            if ProductPurchase.objects.filter(student=request.user, product=product, payment_status='completed').exists():
                messages.error(request, "You have already purchased this product")
                return redirect('digital_products:my_purchases')

            # Create Stripe checkout session
            line_items = [{
                'name': product.title,
                'description': product.short_description,
                'amount': product.price
            }]
            total_amount = product.price
            teacher = product.teacher
            metadata = {
                'product_id': str(product.id),
            }

        elif checkout_cart:
            # Cart checkout (multiple products)
            cart_manager = DigitalProductCartManager(request)
            cart = cart_manager.get_cart()

            if not cart or not cart.digital_product_items.exists():
                messages.error(request, "Your cart is empty")
                return redirect('digital_products:cart')

            # Build line items
            line_items = []
            product_ids = []
            cart_items = cart.digital_product_items.select_related('product__teacher').all()

            for item in cart_items:
                line_items.append({
                    'name': item.product.title,
                    'description': item.product.short_description,
                    'amount': item.price
                })
                product_ids.append(str(item.product.id))

            total_amount = sum(item.price for item in cart_items)
            teacher = cart_items.first().product.teacher  # First product's teacher for commission
            metadata = {
                'product_ids': ','.join(product_ids),
                'cart_id': str(cart.id),
            }

        else:
            messages.error(request, "Invalid checkout request")
            return redirect('digital_products:catalog')

        # Calculate commission
        platform_commission, teacher_share = calculate_commission(total_amount)

        # Build URLs
        success_url = request.build_absolute_uri(reverse('digital_products:checkout_success'))
        cancel_url = request.build_absolute_uri(reverse('digital_products:checkout_cancel'))

        try:
            # Create Stripe Checkout Session
            session = create_checkout_session_with_items(
                line_items=line_items,
                student=request.user,
                teacher=teacher,
                domain='digital_products',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata
            )

            return redirect(session.url, code=303)

        except Exception as e:
            logger.error(f"Stripe checkout error: {e}", exc_info=True)
            # Show detailed error in development
            if settings.DEBUG:
                messages.error(request, f"Payment processing error: {str(e)}")
            else:
                messages.error(request, "Payment processing error. Please try again.")
            if checkout_cart:
                return redirect('digital_products:cart')
            else:
                return redirect('digital_products:detail', slug=product.slug)


class CheckoutSuccessView(LoginRequiredMixin, View):
    """Success page after checkout"""
    template_name = 'digital_products/checkout_success.html'

    def get(self, request):
        return render(request, self.template_name)


class CheckoutCancelView(LoginRequiredMixin, View):
    """Cancel page if user cancels checkout"""
    template_name = 'digital_products/checkout_cancel.html'

    def get(self, request):
        return render(request, self.template_name)


# ============================================================
# STUDENT DASHBOARD (MY PURCHASES)
# ============================================================

class MyPurchasesView(LoginRequiredMixin, ListView):
    """Display user's purchased products"""
    model = ProductPurchase
    template_name = 'digital_products/my_purchases.html'
    context_object_name = 'purchases'

    def get_queryset(self):
        return ProductPurchase.objects.filter(
            student=self.request.user,
            payment_status='completed'
        ).select_related('product__teacher').prefetch_related('product__files').order_by('-purchased_at')


@login_required
def download_product_file(request, purchase_id, file_id):
    """
    Secure download view with lifetime access.
    Users can download files unlimited times after purchase.
    """
    # Verify purchase ownership
    purchase = get_object_or_404(
        ProductPurchase,
        id=purchase_id,
        student=request.user,
        payment_status='completed'
    )

    # Get file
    file_obj = get_object_or_404(
        ProductFile,
        id=file_id,
        product=purchase.product
    )

    # Check if this is a purchasable file (not preview)
    if not file_obj.is_downloadable_after_purchase:
        return HttpResponseForbidden("This file is not available for download")

    # Check download eligibility (only verifies payment is completed)
    can_download, error_msg = purchase.can_download_file(file_obj)
    if not can_download:
        messages.error(request, error_msg)
        return redirect('digital_products:my_purchases')

    # Serve file securely using Django FileResponse
    try:
        file_path = file_obj.file.path
        filename = file_obj.file.name.split('/')[-1]

        response = FileResponse(
            open(file_path, 'rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Log download for analytics
        logger.info(
            f"Product download: user={request.user.id}, "
            f"product={purchase.product.id}, file={file_obj.id}"
        )

        return response

    except FileNotFoundError:
        logger.error(f"File not found: {file_obj.file.name}")
        messages.error(request, "File not found. Please contact support.")
        return redirect('digital_products:my_purchases')


# ============================================================
# REVIEW VIEWS
# ============================================================

class SubmitReviewView(LoginRequiredMixin, View):
    """Submit a product review (verified purchasers only)"""
    template_name = 'digital_products/submit_review.html'

    def get(self, request, product_id):
        product = get_object_or_404(DigitalProduct, id=product_id, status='published')

        # Check if user purchased this product
        try:
            purchase = ProductPurchase.objects.get(
                student=request.user,
                product=product,
                payment_status='completed'
            )
        except ProductPurchase.DoesNotExist:
            messages.error(request, "You must purchase this product before leaving a review")
            return redirect('digital_products:detail', slug=product.slug)

        # Check if already reviewed
        if hasattr(purchase, 'review'):
            messages.info(request, "You have already reviewed this product")
            return redirect('digital_products:detail', slug=product.slug)

        form = ProductReviewForm(purchase=purchase)
        return render(request, self.template_name, {'form': form, 'product': product})

    def post(self, request, product_id):
        product = get_object_or_404(DigitalProduct, id=product_id, status='published')

        try:
            purchase = ProductPurchase.objects.get(
                student=request.user,
                product=product,
                payment_status='completed'
            )
        except ProductPurchase.DoesNotExist:
            return HttpResponseForbidden("You must purchase this product to review it")

        if hasattr(purchase, 'review'):
            messages.error(request, "You have already reviewed this product")
            return redirect('digital_products:detail', slug=product.slug)

        form = ProductReviewForm(request.POST, purchase=purchase)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for your review!")
            return redirect('digital_products:detail', slug=product.slug)

        return render(request, self.template_name, {'form': form, 'product': product})


# ============================================================
# TEACHER DASHBOARD VIEWS
# ============================================================

class TeacherDashboardView(InstructorRequiredMixin, ListView):
    """Teacher dashboard showing all their products"""
    model = DigitalProduct
    template_name = 'digital_products/teacher/dashboard.html'
    context_object_name = 'products'

    def get_queryset(self):
        return DigitalProduct.objects.filter(teacher=self.request.user).annotate(
            files_count=Count('files')
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate stats
        products = context['products']
        context['total_products'] = products.count()
        context['published_products'] = products.filter(status='published').count()
        context['draft_products'] = products.filter(status='draft').count()
        context['total_sales'] = sum(p.total_sales for p in products)

        # Calculate revenue
        purchases = ProductPurchase.objects.filter(
            product__teacher=self.request.user,
            payment_status='completed'
        )
        total_revenue = sum((p.payment_amount for p in purchases), Decimal('0.00'))
        commission_rate = Decimal(str(settings.PLATFORM_COMMISSION_PERCENTAGE)) / Decimal('100')
        context['total_revenue'] = total_revenue
        context['teacher_earnings'] = total_revenue * (Decimal('1') - commission_rate)

        return context


class ProductCreateView(InstructorRequiredMixin, CreateView):
    """Create a new digital product"""
    model = DigitalProduct
    form_class = ProductForm
    template_name = 'digital_products/teacher/create_product.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['file_formset'] = ProductFileFormSet(self.request.POST, self.request.FILES)
        else:
            context['file_formset'] = ProductFileFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        file_formset = context['file_formset']

        if file_formset.is_valid():
            self.object = form.save()
            file_formset.instance = self.object
            file_formset.save()
            messages.success(self.request, f"Product '{self.object.title}' created successfully!")
            return redirect('digital_products:teacher_dashboard')
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('digital_products:teacher_dashboard')


class ProductEditView(InstructorRequiredMixin, UpdateView):
    """Edit an existing digital product"""
    model = DigitalProduct
    form_class = ProductForm
    template_name = 'digital_products/teacher/create_product.html'
    pk_url_kwarg = 'product_id'

    def get_queryset(self):
        # Only allow editing own products
        return DigitalProduct.objects.filter(teacher=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['file_formset'] = ProductFileFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['file_formset'] = ProductFileFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        file_formset = context['file_formset']

        if file_formset.is_valid():
            self.object = form.save()
            file_formset.instance = self.object
            file_formset.save()
            messages.success(self.request, f"Product '{self.object.title}' updated successfully!")
            return redirect('digital_products:teacher_dashboard')
        else:
            return self.render_to_response(self.get_context_data(form=form))


class ProductSalesView(InstructorRequiredMixin, ListView):
    """View sales for a specific product"""
    model = ProductPurchase
    template_name = 'digital_products/teacher/product_sales.html'
    context_object_name = 'purchases'

    def get_queryset(self):
        self.product = get_object_or_404(
            DigitalProduct,
            id=self.kwargs['product_id'],
            teacher=self.request.user
        )
        return ProductPurchase.objects.filter(
            product=self.product,
            payment_status='completed'
        ).select_related('student').order_by('-purchased_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        purchases = context['purchases']
        total_revenue = sum(p.payment_amount for p in purchases)
        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100
        context['total_revenue'] = total_revenue
        context['teacher_earnings'] = total_revenue * (1 - Decimal(str(commission_rate)))
        return context


@login_required
def archive_product(request, product_id):
    """Archive or unarchive a product (toggle)"""
    product = get_object_or_404(DigitalProduct, id=product_id, teacher=request.user)
    
    if product.status == 'archived':
        product.status = 'draft'
        messages.success(request, f"Product '{product.title}' has been unarchived")
    else:
        product.status = 'archived'
        messages.success(request, f"Product '{product.title}' has been archived")
    
    product.save()
    return redirect('digital_products:teacher_dashboard')


@login_required
def delete_product(request, product_id):
    """Delete a product (with confirmation via POST)"""
    product = get_object_or_404(DigitalProduct, id=product_id, teacher=request.user)
    
    if request.method == 'POST':
        # Check if product has sales
        if product.total_sales > 0:
            messages.error(
                request,
                f"Cannot delete '{product.title}' because it has {product.total_sales} sale(s). "
                "You can archive it instead."
            )
            return redirect('digital_products:teacher_dashboard')
        
        product_title = product.title
        product.delete()
        messages.success(request, f"Product '{product_title}' has been deleted")
        return redirect('digital_products:teacher_dashboard')
    
    # GET request - show confirmation page
    return render(request, 'digital_products/teacher/confirm_delete.html', {
        'product': product
    })
