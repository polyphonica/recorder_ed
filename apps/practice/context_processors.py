def practice_clip_inbox(request):
    """Count of clips waiting for the teacher, for the nav badge."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    profile = getattr(user, 'profile', None)
    if not profile or not getattr(profile, 'is_teacher', False):
        return {}
    from .clip_views import teacher_inbox_clips
    return {'practice_clip_inbox_count': teacher_inbox_clips(user).count()}
