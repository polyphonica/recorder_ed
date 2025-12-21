from django.urls import path
from . import views

app_name = 'digital_products'

urlpatterns = [
    # Public Catalog
    path('', views.ProductCatalogView.as_view(), name='catalog'),
    path('category/<slug:category_slug>/', views.ProductCatalogView.as_view(), name='catalog_by_category'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='detail'),

    # Shopping Cart
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<uuid:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<uuid:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Checkout
    path('checkout/', views.ProductCheckoutView.as_view(), name='checkout'),
    path('checkout/success/', views.CheckoutSuccessView.as_view(), name='checkout_success'),
    path('checkout/cancel/', views.CheckoutCancelView.as_view(), name='checkout_cancel'),

    # Student Dashboard
    path('my-purchases/', views.MyPurchasesView.as_view(), name='my_purchases'),
    path('my-purchases/<uuid:purchase_id>/download/<uuid:file_id>/', views.download_product_file, name='download_file'),

    # Reviews
    path('product/<uuid:product_id>/review/', views.SubmitReviewView.as_view(), name='submit_review'),

    # Teacher Dashboard
    path('teacher/dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('teacher/product/create/', views.ProductCreateView.as_view(), name='create_product'),
    path('teacher/product/<uuid:product_id>/edit/', views.ProductEditView.as_view(), name='edit_product'),
    path('teacher/product/<uuid:product_id>/sales/', views.ProductSalesView.as_view(), name='product_sales'),
    path('teacher/product/<uuid:product_id>/archive/', views.archive_product, name='archive_product'),
    path('teacher/product/<uuid:product_id>/delete/', views.delete_product, name='delete_product'),
]
