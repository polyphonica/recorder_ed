def playalong_library(request):
    """Whether the public Play-Along Library is open, and whether to show the teachers' Play-Alongs menu."""
    from .models import library_is_open
    match = getattr(request, 'resolver_match', None)
    user = getattr(request, 'user', None)
    is_teacher = bool(user and user.is_authenticated and hasattr(user, 'profile') and user.profile.is_teacher)
    return {
        'playalong_library_open': library_is_open(),
        'playalong_teacher_area': is_teacher and match is not None and match.namespace in ('audioplayer', 'playalongs'),
    }
