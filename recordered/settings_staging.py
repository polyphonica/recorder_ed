"""
Staging settings for recorder_ed.

Inherits from settings.py and overrides values appropriate for the staging
server (old server). Set DJANGO_SETTINGS_MODULE=recordered.settings_staging
on the staging server (systemd unit or .env file).

Secrets (DB password, Stripe test keys, etc.) are read from the staging
server's .env file via decouple — never hardcode real credentials here.
"""

from .settings import *  # noqa: F401, F403
from decouple import config, Csv

# ------------------------------------------------------------------
# Core
# ------------------------------------------------------------------
DEBUG = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Disable all HTTPS/HSTS security settings — staging runs over HTTP
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None

# ------------------------------------------------------------------
# Database — separate staging DB, never point at production
# ------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='recorder_ed_staging'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# ------------------------------------------------------------------
# Email — print to console so no real emails are sent from staging
# ------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ------------------------------------------------------------------
# Stripe — use test-mode keys in the staging server's .env
# (set STRIPE_PUBLISHABLE_KEY / STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET
#  to pk_test_..., sk_test_..., whsec_test_... values)
# ------------------------------------------------------------------
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# ------------------------------------------------------------------
# Media — separate directory so staging uploads don't mix with production
# ------------------------------------------------------------------
MEDIA_ROOT = '/var/www/recorder_ed_staging/media/'

# ------------------------------------------------------------------
# Site URL
# ------------------------------------------------------------------
SITE_URL = config('SITE_URL', default='http://localhost:8000')
