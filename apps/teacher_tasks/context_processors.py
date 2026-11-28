def teacher_tasks(request):
    """Count of a teacher's tasks due today or overdue, for the menu badge."""
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated and hasattr(user, 'profile') and user.profile.is_teacher):
        return {}
    from .models import Task
    return {'teacher_tasks_due': Task.objects.filter(owner=user).due_by_today().count()}
