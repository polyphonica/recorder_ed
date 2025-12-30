from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from .models import LessonContentTemplate, Tag
from .forms import LessonContentTemplateForm


@login_required
def template_library(request):
    """
    Teacher's library of lesson content templates with search and filters
    """
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    subject_id = request.GET.get('subject', '').strip()
    syllabus = request.GET.get('syllabus', '').strip()
    grade_level = request.GET.get('grade', '').strip()
    lesson_number = request.GET.get('lesson', '').strip()
    tag_id = request.GET.get('tag', '').strip()
    view_mode = request.GET.get('mode', 'my_templates')  # 'my_templates' or 'browse_all'

    # Base queryset
    templates = LessonContentTemplate.objects.all().prefetch_related('tags').select_related('subject', 'created_by')

    # Filter by view mode
    if view_mode == 'my_templates':
        # Show only templates created by the logged-in teacher
        templates = templates.filter(created_by=request.user)
    elif view_mode == 'browse_all':
        # Show all public templates
        templates = templates.filter(is_public=True)

    # Apply search filter
    if search_query:
        templates = templates.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    # Apply subject filter
    if subject_id:
        templates = templates.filter(subject_id=subject_id)

    # Apply syllabus filter
    if syllabus:
        templates = templates.filter(syllabus=syllabus)

    # Apply grade level filter
    if grade_level:
        templates = templates.filter(grade_level=grade_level)

    # Apply lesson number filter
    if lesson_number:
        templates = templates.filter(lesson_number=lesson_number)

    # Apply tag filter
    if tag_id:
        templates = templates.filter(tags__id=tag_id)

    # Order by syllabus, grade, lesson number, and title (as per model Meta)
    templates = templates.order_by('syllabus', 'grade_level', 'lesson_number', 'title')

    # Limit results for performance
    templates = templates[:200]

    # Get filter options for dropdowns
    from apps.private_teaching.models import Subject
    subjects = Subject.objects.filter(teacher__user=request.user).order_by('subject')
    tags = Tag.objects.all().order_by('name')

    # Get unique grade levels and lesson numbers for filters
    grade_levels = LessonContentTemplate.objects.filter(
        created_by=request.user
    ).exclude(
        grade_level=''
    ).values_list('grade_level', flat=True).distinct().order_by('grade_level')

    # Check if filters are active
    filters_active = any([search_query, subject_id, syllabus, grade_level, lesson_number, tag_id])

    return render(request, 'lesson_templates/library.html', {
        'templates': templates,
        'subjects': subjects,
        'tags': tags,
        'syllabus_choices': LessonContentTemplate.SYLLABUS_CHOICES,
        'grade_levels': grade_levels,
        'search_query': search_query,
        'selected_subject': subject_id,
        'selected_syllabus': syllabus,
        'selected_grade': grade_level,
        'selected_lesson': lesson_number,
        'selected_tag': tag_id,
        'view_mode': view_mode,
        'filters_active': filters_active,
    })


@login_required
def template_create(request):
    """Teacher creates a new lesson content template"""
    if request.method == 'POST':
        form = LessonContentTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            form.save_m2m()  # Save many-to-many relationships (tags)
            messages.success(request, f'Template "{template.title}" created successfully!')
            return redirect('lesson_templates:library')
    else:
        form = LessonContentTemplateForm()

    return render(request, 'lesson_templates/create.html', {
        'form': form,
    })


@login_required
def template_edit(request, pk):
    """Teacher edits an existing lesson content template"""
    template = get_object_or_404(LessonContentTemplate, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = LessonContentTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'Template "{template.title}" updated successfully!')
            return redirect('lesson_templates:library')
    else:
        form = LessonContentTemplateForm(instance=template)

    return render(request, 'lesson_templates/edit.html', {
        'form': form,
        'template': template,
    })


@login_required
def template_preview(request, pk):
    """Preview a lesson content template"""
    template = get_object_or_404(LessonContentTemplate, pk=pk)

    # Check permissions: user must own the template or it must be public
    if template.created_by != request.user and not template.is_public:
        messages.error(request, 'You do not have permission to view this template.')
        return redirect('lesson_templates:library')

    return render(request, 'lesson_templates/preview.html', {
        'template': template,
    })


@login_required
def template_delete(request, pk):
    """Teacher deletes a lesson content template"""
    template = get_object_or_404(LessonContentTemplate, pk=pk, created_by=request.user)

    if request.method == 'POST':
        template_title = template.title
        template.delete()
        messages.success(request, f'Template "{template_title}" deleted successfully!')
        return redirect('lesson_templates:library')

    return render(request, 'lesson_templates/delete_confirm.html', {
        'template': template,
    })


@login_required
def template_duplicate(request, pk):
    """Duplicate an existing template"""
    original_template = get_object_or_404(LessonContentTemplate, pk=pk)

    # Check permissions: user must own the template or it must be public
    if original_template.created_by != request.user and not original_template.is_public:
        messages.error(request, 'You do not have permission to duplicate this template.')
        return redirect('lesson_templates:library')

    # Create a copy
    duplicate = LessonContentTemplate.objects.get(pk=pk)
    duplicate.pk = None  # This will create a new instance
    duplicate.id = None
    duplicate.title = f"{original_template.title} (Copy)"
    duplicate.created_by = request.user
    duplicate.is_public = False  # Duplicates are private by default
    duplicate.use_count = 0
    duplicate.save()

    # Copy the tags
    for tag in original_template.tags.all():
        duplicate.tags.add(tag)

    messages.success(request, f'Template duplicated as "{duplicate.title}"!')
    return redirect('lesson_templates:edit', pk=duplicate.pk)


@login_required
def get_template_content(request, pk):
    """
    AJAX endpoint to get template content for insertion into lessons
    Returns JSON with template content
    """
    template = get_object_or_404(LessonContentTemplate, pk=pk)

    # Check permissions
    if template.created_by != request.user and not template.is_public:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # Increment use count
    template.increment_use_count()

    return JsonResponse({
        'success': True,
        'content': template.content,
        'title': template.title,
    })
