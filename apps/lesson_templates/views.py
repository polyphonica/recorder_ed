from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.conf import settings
from django.views.decorators.http import require_POST

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
        num_templates=Count('templates')
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
        num_templates=Count('templates')
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


@login_required
@require_POST
def template_ai_assist(request):
    """AI assistant: draft or revise lesson template content."""
    from anthropic import Anthropic

    ai_mode = request.POST.get('mode', '').strip()
    description = request.POST.get('description', '').strip()
    if not description and ai_mode != 'reformat':
        return JsonResponse({'error': 'No description provided.'}, status=400)

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return JsonResponse({'error': 'AI assistant is not configured.'}, status=503)

    template_id = request.POST.get('template_id', '').strip()
    existing_template = None
    if template_id:
        existing_template = get_object_or_404(LessonContentTemplate, pk=template_id, created_by=request.user)

    if ai_mode == 'reformat' and not existing_template:
        return JsonResponse({'error': 'Reformat requires an existing template.'}, status=400)
    if ai_mode == 'reformat' and not existing_template.content:
        return JsonResponse({'error': 'No existing content to reformat.'}, status=400)

    LESSON_STYLE_GUIDE = """
LESSON HTML STYLE GUIDE — apply these exact inline styles to every element. Do not deviate.

FONT: font-family:'Inter',system-ui,sans-serif on all elements.

LEARNING OBJECTIVES — always the opening section, rendered as a coral callout box:
<div style="background:#fff4f3; border-left:5px solid #d94f3d; border-radius:0 6px 6px 0; padding:18px 22px; margin:0 0 36px 0;">
  <p style="font-size:0.68rem; font-weight:700; color:#d94f3d; text-transform:uppercase; letter-spacing:0.14em; margin:0 0 8px 0; font-family:'Inter',system-ui,sans-serif;"><i class="fas fa-bullseye" style="margin-right:6px;"></i>Learning Objectives</p>
  <p style="font-size:1rem; color:#2c1f1e; line-height:1.75; margin:0; font-family:'Inter',system-ui,sans-serif;">Objectives text here.</p>
</div>

THEORY/CONTENT HEADINGS (h2):
<h2 style="font-size:1.15rem; font-weight:700; color:#2d3f50; font-family:'Inter',system-ui,sans-serif; border-bottom:3px solid #d94f3d; padding-bottom:8px; margin:0 0 16px 0; letter-spacing:0.01em;">Heading Text</h2>
- Add a Font Awesome icon before the heading text where thematically appropriate:
  - Listening/audio sections: <i class="fas fa-headphones" style="font-size:0.9rem; margin-right:8px; color:#d94f3d;"></i>
  - Notation/written music sections: <i class="fas fa-music" style="font-size:0.9rem; margin-right:8px; color:#d94f3d;"></i>

BODY PARAGRAPHS:
<p style="font-size:1rem; color:#1e1e1e; line-height:1.8; margin:0 0 14px 0; font-family:'Inter',system-ui,sans-serif;">Text here.</p>
- Last paragraph before a new heading or section: margin:0 0 32px 0

EXERCISE SECTIONS — each exercise in a white card with coral top border:
<div style="background:#ffffff; border:1px solid #dde1e6; border-top:3px solid #d94f3d; border-radius:6px; padding:22px 26px; margin:0 0 32px 0; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
  <p class="exercise-badge" style="font-size:0.68rem; font-weight:700; background:#d94f3d; text-transform:uppercase; letter-spacing:0.12em; display:inline-block; padding:3px 10px; border-radius:3px; margin:0 0 12px 0; font-family:'Inter',system-ui,sans-serif;"><span style="color:#ffffff;">Exercise 1</span></p>
  <h2 style="font-size:1.1rem; font-weight:700; color:#2d3f50; font-family:'Inter',system-ui,sans-serif; margin:0 0 12px 0; border:none; padding:0;">Exercise Title</h2>
  <p style="font-size:1rem; color:#1e1e1e; line-height:1.8; margin:0 0 14px 0; font-family:'Inter',system-ui,sans-serif;">Instructions.</p>
  <ul style="font-size:1rem; color:#1e1e1e; line-height:1.8; margin:0; padding-left:0; list-style:none; font-family:'Inter',system-ui,sans-serif;">
    <li style="padding:4px 0 4px 26px; position:relative;"><span style="position:absolute;left:0;color:#d94f3d;font-weight:bold;">&#9658;</span> Step text</li>
  </ul>
  <p style="font-size:0.95rem; color:#4a5a6a; line-height:1.75; margin:0; font-style:italic; border-top:1px solid #dde1e6; padding-top:12px; font-family:'Inter',system-ui,sans-serif;">Closing note.</p>
</div>

LISTS outside exercise boxes:
<ul style="font-size:1rem; color:#1e1e1e; line-height:1.8; margin:0 0 14px 0; padding-left:0; list-style:none; font-family:'Inter',system-ui,sans-serif;">
  <li style="padding:4px 0 4px 26px; position:relative;"><span style="position:absolute;left:0;color:#d94f3d;font-weight:bold;">&#9658;</span> Item text</li>
</ul>

IMAGE/NOTATION PLACEHOLDERS (use ONLY in new templates when no actual image exists — NEVER replace an existing <img>, <figure>, or <svg> with this):
<div style="background:#f8f9fa; border:1px dashed #d94f3d; border-radius:6px; padding:14px 20px; margin:0 0 14px 0; text-align:center; color:#2d3f50; font-size:0.9rem; font-style:italic; font-family:'Inter',system-ui,sans-serif;"><i class="fas fa-image" style="margin-right:6px; color:#d94f3d;"></i>Description of image or notation example</div>

SUMMARY — always the final section, rendered as a slate callout box:
<div style="background:#f3f6f8; border-left:5px solid #2d3f50; border-radius:0 6px 6px 0; padding:20px 24px; margin:0;">
  <p style="font-size:0.68rem; font-weight:700; color:#2d3f50; text-transform:uppercase; letter-spacing:0.14em; margin:0 0 10px 0; font-family:'Inter',system-ui,sans-serif;"><i class="fas fa-check-circle" style="margin-right:6px;"></i>Summary</p>
  <p style="font-size:1rem; color:#1a2530; line-height:1.8; margin:0; font-family:'Inter',system-ui,sans-serif;">Summary text.</p>
</div>

EMPHASIS: use <strong> for key musical terms; <em> for gentle emphasis within exercise instructions.
DO NOT use any other colours, font sizes, or structural patterns not listed above.
"""

    if ai_mode == 'reformat':
        prompt = f"""You are reformatting an existing recorder lesson template to match the platform's visual style guide.

EXISTING TEMPLATE CONTENT (full HTML):
{existing_template.content}

YOUR TASK: Reformat the HTML using the style guide below. Apply the exact inline styles specified to every element.

STRICT RULES — YOU MUST FOLLOW THESE EXACTLY:
- Do NOT change any words, sentences, paragraphs, or educational content
- Do NOT add, remove, or reorder any sections
- ONLY replace the HTML markup and inline styles to match the style guide
- PRESERVE MEDIA VERBATIM: copy every <img>, <figure>, <svg>, <picture>, <audio>, <video>, and <source> element exactly character-for-character
- The IMAGE/NOTATION PLACEHOLDERS shown in the style guide are ONLY for use when drafting NEW templates — do NOT apply them to existing images or figures
{LESSON_STYLE_GUIDE}
Use the generate_template_content tool to return your response."""

    elif existing_template and existing_template.content:
        prompt = f"""You are an expert recorder music teacher and editor. You are revising an existing lesson template.

EXISTING TEMPLATE CONTENT (full HTML):
{existing_template.content}

TEACHER'S REVISION INSTRUCTIONS:
{description}

YOUR TASK: Revise the template content according to the teacher's instructions above.

CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY:
- Preserve the existing text, structure, and HTML of sections you are NOT changing
- For any new sections or content you add, apply the style guide below precisely
- Do NOT reformat or restyle existing content that the teacher did not ask you to change
- Return the complete revised HTML — not a summary or partial content
{LESSON_STYLE_GUIDE}
Use the generate_template_content tool to return your response."""

    else:
        prompt = f"""You are an expert recorder music teacher and curriculum writer creating a new reusable lesson template.

TEACHER'S NOTES FOR THIS TEMPLATE:
{description}

YOUR TASK: Draft complete lesson template content based on the teacher's notes. Apply the style guide below to every element — use the exact inline styles specified, no exceptions.

Write 300–600 words covering: learning objective, explanation of the concept, practical exercises, and a summary.
{LESSON_STYLE_GUIDE}
Use the generate_template_content tool to return your response."""

    tools = [{
        'name': 'generate_template_content',
        'description': 'Generate lesson template content for the teacher to review before applying.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': 'Complete lesson content as valid HTML with inline styles per the style guide.',
                },
                'summary': {
                    'type': 'string',
                    'description': 'One sentence describing what this template covers.',
                },
            },
            'required': ['content', 'summary'],
        },
    }]

    if ai_mode == 'reformat' or (existing_template and existing_template.content):
        model = 'claude-sonnet-4-6'
        max_tokens = 16000
    else:
        model = 'claude-haiku-4-5-20251001'
        max_tokens = 8192

    try:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice={'type': 'tool', 'name': 'generate_template_content'},
            messages=[{'role': 'user', 'content': prompt}],
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error('Template AI assist failed: %s', e)
        return JsonResponse({'error': 'AI service unavailable. Please try again later.'}, status=503)

    if message.stop_reason == 'max_tokens':
        return JsonResponse({'error': 'The template is too long to process in one request. Try splitting it into shorter sections.'}, status=500)

    try:
        data = message.content[0].input
    except (IndexError, AttributeError) as e:
        import logging
        logging.getLogger(__name__).error('Template AI assist unexpected response: %s', e)
        return JsonResponse({'error': 'Unexpected AI response. Please try again.'}, status=500)

    return JsonResponse(data)
