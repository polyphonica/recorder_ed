def playalong_library(request):
    """Whether the public Play-Along Library is open, for menus and banners."""
    from .models import library_is_open
    return {'playalong_library_open': library_is_open()}
