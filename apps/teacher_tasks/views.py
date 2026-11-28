from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.audioplayer.views import teacher_required

from .forms import TaskForm
from .links import link_info
from .models import Task

GROUPS = [
    ('overdue', 'Overdue'),
    ('today', 'Today'),
    ('week', 'Next 7 days'),
    ('later', 'Later / no date'),
]
LINK_SALT = 'teacher_tasks.link'


def make_link_token(obj):
    """A signed reference to obj, for the 'Add task' form on its page."""
    ct = ContentType.objects.get_for_model(obj)
    return signing.dumps([ct.pk, str(obj.pk)], salt=LINK_SALT)


def _linked_object(request, token):
    """The object a signed token refers to, if this teacher may link to it."""
    if not token:
        return None
    try:
        ct_id, object_id = signing.loads(token, salt=LINK_SALT)
        obj = ContentType.objects.get_for_id(ct_id).get_object_for_this_type(pk=object_id)
    except Exception:
        raise Http404
    info = link_info(obj)
    if not info or not info['allowed'](request.user, obj):
        raise Http404
    return obj


def _back(request, default='teacher_tasks:list'):
    url = request.POST.get('next') or request.GET.get('next')
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return redirect(url)
    return redirect(default)


@teacher_required
def task_list(request):
    area = request.GET.get('area', '')
    show_done = request.GET.get('done') == '1'
    tasks = Task.objects.filter(owner=request.user).select_related('content_type')
    if area in Task.Area.values:
        tasks = tasks.filter(area=area)

    open_tasks = list(tasks.open())
    groups = [(key, label, [t for t in open_tasks if t.group == key]) for key, label in GROUPS]
    done_tasks = list(tasks.done().order_by('-done_at')[:50]) if show_done else []

    counts = {value: 0 for value in Task.Area.values}
    for t in Task.objects.filter(owner=request.user).open().values_list('area', flat=True):
        counts[t] += 1
    areas = [(value, label, counts[value]) for value, label in Task.Area.choices]

    return render(request, 'teacher_tasks/task_list.html', {
        'form': TaskForm(initial={'area': area or Task.Area.GENERAL}),
        'groups': groups,
        'done_tasks': done_tasks,
        'done_count': tasks.done().count(),
        'show_done': show_done,
        'areas': areas,
        'selected_area': area,
        'open_total': len(open_tasks),
        'open_all': sum(counts.values()),
        'area_choices': Task.Area.choices,
    })


@teacher_required
@require_POST
def task_create(request):
    form = TaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        task.set_link(_linked_object(request, request.POST.get('link')))
        task.save()
    else:
        messages.error(request, 'The task needs a title.')
    return _back(request)


@teacher_required
@require_POST
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    form = TaskForm(request.POST, instance=task)
    if form.is_valid():
        form.save()
        messages.success(request, 'Task updated.')
    else:
        messages.error(request, 'The task needs a title.')
    return _back(request)


@teacher_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.done_at = None if task.is_done else timezone.now()
    task.save(update_fields=['done_at', 'updated_at'])
    return _back(request)


@teacher_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.delete()
    messages.success(request, f'Deleted "{task.title}".')
    return _back(request)
