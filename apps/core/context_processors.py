from django.conf import settings


def google_analytics(request):
    # Only enable Google Analytics in production (DEBUG=False)
    if settings.DEBUG:
        return {'GOOGLE_ANALYTICS_ID': ''}
    return {'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', '')}
