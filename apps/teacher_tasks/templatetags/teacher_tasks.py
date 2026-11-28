from django import template

from ..links import link_info
from ..models import Task
from ..views import make_link_token

register = template.Library()


@register.inclusion_tag('teacher_tasks/_panel.html', takes_context=True)
def task_panel(context, obj):
    """Open tasks for obj, with an 'Add task' form linked to it. Teachers only."""
    request = context.get('request')
    user = getattr(request, 'user', None)
    empty = {'show': False}
    if obj is None or not getattr(obj, 'pk', None) or not user or not user.is_authenticated:
        return empty
    if not (hasattr(user, 'profile') and user.profile.is_teacher):
        return empty
    info = link_info(obj)
    if not info or not info['allowed'](user, obj):
        return empty
    tasks = Task.objects.filter(owner=user).for_object(obj).open()
    return {
        'show': True,
        'tasks': tasks,
        'link_token': make_link_token(obj),
        'link_label': info['label'](obj),
        'next': request.get_full_path(),
        'request': request,
        'csrf_token': context.get('csrf_token'),
        'in_panel': True,
        'area_choices': Task.Area.choices,
    }
