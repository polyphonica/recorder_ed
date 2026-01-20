from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count

from .models import LessonContentTemplate, TemplateCategory, Tag
from .forms import LessonContentTemplateForm, TemplateCategoryForm


@login_required
def template_library(request):
    """
    Teacher's library of lesson content templates with search and filters
    """
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    subject_id = request.GET.get('subject', '').strip()
    syllabus = request.GET.get('syllabus', '').strip()
    grade_level = request.GET.get('grade', '').strip()
    lesson_number = request.GET.get('lesson', '').strip()
    tag_id = request.GET.get('tag', '').strip()
    view_mode = request.GET.get('mode', 'my_templates')  # 'my_templates' or 'browse_all'

    # Base queryset
    templates = LessonContentTemplate.objects.all().prefetch_related('tags').select_related('subject', 'created_by', 'category')

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

    # Apply category filter
    if category_id:
        if category_id == 'standalone':
            templates = templates.filter(category__isnull=True)
        else:
            templates = templates.filter(category_id=category_id)

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

    # Order by category, lesson number, then other fields
    templates = templates.order_by('category__display_order', 'category__name', 'lesson_number', 'title')

    # Limit results for performance
    templates = templates[:200]

    # Get user's categories with template counts
    categories = TemplateCategory.objects.filter(
        created_by=request.user
    ).annotate(
        template_count=Count('templates')
    ).order_by('display_order', 'name')

    # Count standalone templates
    standalone_count = LessonContentTemplate.objects.filter(
        created_by=request.user,
        category__isnull=True
    ).count()

    # Get filter options for dropdowns
    from apps.private_teaching.models import Subject
    subjects = Subject.objects.filter(teacher=request.user).order_by('subject')
    tags = Tag.objects.all().order_by('name')

    # Get unique grade levels for filters
    grade_levels = LessonContentTemplate.objects.filter(
        created_by=request.user
    ).exclude(
        grade_level=''
    ).values_list('grade_level', flat=True).distinct().order_by('grade_level')

    # Check if filters are active
    filters_active = any([search_query, category_id, subject_id, syllabus, grade_level, lesson_number, tag_id])

    return render(request, 'lesson_templates/library.html', {
        'templates': templates,
        'categories': categories,
        'standalone_count': standalone_count,
        'subjects': subjects,
        'tags': tags,
        'syllabus_choices': LessonContentTemplate.SYLLABUS_CHOICES,
        'grade_levels': grade_levels,
        'search_query': search_query,
        'selected_category': category_id,
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
        form = LessonContentTemplateForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            form.save_m2m()  # Save many-to-many relationships (tags)
            messages.success(request, f'Template "{template.title}" created successfully!')
            return redirect('lesson_templates:library')
    else:
        # Check if category was passed in URL query
        initial = {}
        category_id = request.GET.get('category')
        if category_id:
            try:
                category = TemplateCategory.objects.get(pk=category_id, created_by=request.user)
                initial['category'] = category
            except TemplateCategory.DoesNotExist:
                pass
        form = LessonContentTemplateForm(user=request.user, initial=initial)

    return render(request, 'lesson_templates/create.html', {
        'form': form,
    })


@login_required
def template_edit(request, pk):
    """Teacher edits an existing lesson content template"""
    template = get_object_or_404(LessonContentTemplate, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = LessonContentTemplateForm(request.POST, instance=template, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Template "{template.title}" updated successfully!')
            return redirect('lesson_templates:library')
    else:
        form = LessonContentTemplateForm(instance=template, user=request.user)

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
    # Clear category if user doesn't own it
    if duplicate.category and duplicate.category.created_by != request.user:
        duplicate.category = None
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


# ============================================================================
# CATEGORY MANAGEMENT VIEWS
# ============================================================================

@login_required
def category_list(request):
    """List all categories for the current teacher"""
    categories = TemplateCategory.objects.filter(
        created_by=request.user
    ).annotate(
        template_count=Count('templates')
    ).order_by('display_order', 'name')

    # Count standalone templates
    standalone_count = LessonContentTemplate.objects.filter(
        created_by=request.user,
        category__isnull=True
    ).count()

    return render(request, 'lesson_templates/category_list.html', {
        'categories': categories,
        'standalone_count': standalone_count,
    })


@login_required
def category_create(request):
    """Create a new template category"""
    if request.method == 'POST':
        form = TemplateCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('lesson_templates:category_list')
    else:
        form = TemplateCategoryForm()

    # Filter subjects to only show user's subjects
    from apps.private_teaching.models import Subject
    form.fields['subject'].queryset = Subject.objects.filter(teacher=request.user)

    return render(request, 'lesson_templates/category_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
def category_edit(request, pk):
    """Edit an existing template category"""
    category = get_object_or_404(TemplateCategory, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = TemplateCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('lesson_templates:category_list')
    else:
        form = TemplateCategoryForm(instance=category)

    # Filter subjects to only show user's subjects
    from apps.private_teaching.models import Subject
    form.fields['subject'].queryset = Subject.objects.filter(teacher=request.user)

    return render(request, 'lesson_templates/category_form.html', {
        'form': form,
        'category': category,
        'action': 'Edit',
    })


@login_required
def category_delete(request, pk):
    """Delete a template category"""
    category = get_object_or_404(TemplateCategory, pk=pk, created_by=request.user)

    if request.method == 'POST':
        category_name = category.name
        # Templates will have their category set to NULL (not deleted)
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted. Templates are now standalone.')
        return redirect('lesson_templates:category_list')

    # Get templates that will become standalone
    affected_templates = category.templates.all()

    return render(request, 'lesson_templates/category_delete_confirm.html', {
        'category': category,
        'affected_templates': affected_templates,
    })


@login_required
def category_detail(request, pk):
    """View a category and its templates"""
    category = get_object_or_404(TemplateCategory, pk=pk)

    # Check permissions: user must own the category or it must be public
    if category.created_by != request.user and not category.is_public:
        messages.error(request, 'You do not have permission to view this category.')
        return redirect('lesson_templates:category_list')

    templates = category.templates.all().prefetch_related('tags').select_related('subject').order_by('lesson_number', 'title')

    return render(request, 'lesson_templates/category_detail.html', {
        'category': category,
        'templates': templates,
    })


@login_required
def category_duplicate(request, pk):
    """Duplicate a category (without its templates)"""
    original_category = get_object_or_404(TemplateCategory, pk=pk)

    # Check permissions: user must own the category or it must be public
    if original_category.created_by != request.user and not original_category.is_public:
        messages.error(request, 'You do not have permission to duplicate this category.')
        return redirect('lesson_templates:category_list')

    # Create a copy of the category (not the templates)
    duplicate = TemplateCategory(
        name=f"{original_category.name} (Copy)",
        description=original_category.description,
        subject=original_category.subject if original_category.subject and original_category.subject.teacher == request.user else None,
        syllabus=original_category.syllabus,
        grade_level=original_category.grade_level,
        color=original_category.color,
        display_order=original_category.display_order,
        is_public=False,  # Duplicates are private by default
        created_by=request.user,
    )
    duplicate.save()

    messages.success(request, f'Category duplicated as "{duplicate.name}". Templates were not copied.')
    return redirect('lesson_templates:category_edit', pk=duplicate.pk)
