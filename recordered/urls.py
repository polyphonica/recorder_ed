"""
URL configuration for recordered project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.contrib.auth import views as auth_views

# Import views
from views import DomainSelectorView, robots_txt

# Import sitemaps
from .sitemaps import sitemaps

# Import custom forms
from apps.accounts.forms import CustomPasswordResetForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-portal/', include('apps.admin_portal.urls')),  # Admin portal for staff
    path('accounts/', include('apps.accounts.urls')),  # Custom login view here
    # Custom password reset view with HTML email support
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        form_class=CustomPasswordResetForm,
        html_email_template_name='registration/password_reset_email.html'
    ), name='password_reset'),
    path('accounts/', include('django.contrib.auth.urls')),  # Other auth views (logout, password reset, etc.)
    path('core/', include('apps.core.urls')),  # Core demo pages
    path('workshops/', include('apps.workshops.urls')),
    path('payments/', include('apps.payments.urls')),
    path('private-teaching/', include('apps.private_teaching.urls')),
    path('lessons/', include('lessons.urls')),
    path('assignments/', include('assignments.urls')),
    path('expenses/', include('apps.expenses.urls')),
    path('courses/', include('apps.courses.urls')),
    path('products/', include('apps.digital_products.urls')),
    path('audioplayer/', include('apps.audioplayer.urls')),
    path('messages/', include('apps.messaging.urls')),
    path('support/', include('apps.support.urls')),
    path('help/', include('apps.help_center.urls')),
    path('teacher/', include('apps.teacher_applications.urls')),  # Teacher onboarding
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('', DomainSelectorView.as_view(), name='domain_selector'),  # Landing page at root
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
