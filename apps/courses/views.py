"""
Views for courses app.
"""

import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, View
)
from django.db import transaction
from django.db.models import Count, Q, Prefetch, Max, Avg
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from apps.core.views import (
    BaseCheckoutSuccessView, BaseCheckoutCancelView, SearchableListViewMixin,
    SuccessMessageMixin, SetUserFieldMixin, CourseOwnershipMixin, CourseContextMixin
)
from .models import (
    Course, Topic, Lesson, LessonAttachment,
    CourseEnrollment, LessonProgress,
    CourseMessage, CourseCancellationRequest
)
from apps.quizzes.models import Quiz, QuizQuestion, QuizAttempt, QuizAssignment
from .mixins import InstructorRequiredMixin, CourseInstructorMixin, EnrollmentRequiredMixin
from .forms import (
    CourseAdminForm, QuizAnswerFormSet, CourseMessageForm, MessageReplyForm,
    LessonPieceFormSet, LessonAttachmentFormSet
)


# ============================================================================
# INSTRUCTOR VIEWS - Course Management
# ============================================================================

class InstructorDashboardView(InstructorRequiredMixin, TemplateView):
    """
    Main dashboard for instructors to manage their courses.
    Shows list of courses with quick stats.
    """
    template_name = 'courses/instructor/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get instructor's courses with related data
        courses = Course.objects.filter(
            instructor=self.request.user
        ).annotate(
            topic_count=Count('topics', distinct=True),
            lesson_count=Count('topics__lessons', distinct=True),
            enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True), distinct=True),
            quiz_count=Count('topics__lessons__quiz', distinct=True)
        ).order_by('created_at')

        paginator = Paginator(courses, 12)
        courses_page = paginator.get_page(self.request.GET.get('page'))

        # Calculate stats
        # PERFORMANCE FIX: Consolidate course counts into single aggregate
        course_stats = Course.objects.filter(instructor=self.request.user).aggregate(
            total=Count('id'),
            published=Count('id', filter=Q(status=Course.Status.PUBLISHED)),
            draft=Count('id', filter=Q(status=Course.Status.DRAFT))
        )
        total_courses = course_stats['total']
        published_courses = course_stats['published']
        draft_courses = course_stats['draft']

        total_students = CourseEnrollment.objects.filter(
            course__instructor=self.request.user,
            is_active=True
        ).values('student').distinct().count()

        # Get recent cancellations for instructor's courses (last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_cancellations = CourseCancellationRequest.objects.filter(
            enrollment__course__instructor=self.request.user,
            created_at__gte=thirty_days_ago
        ).select_related('enrollment', 'enrollment__course', 'student').order_by('-created_at')[:10]

        context.update({
            'courses': courses_page,
            'page_obj': courses_page,
            'is_paginated': courses_page.has_other_pages(),
            'total_courses': total_courses,
            'published_courses': published_courses,
            'draft_courses': draft_courses,
            'total_students': total_students,
            'recent_cancellations': recent_cancellations,
            'recent_cancellations_count': recent_cancellations.count(),
        })

        return context


class CourseCreateView(SuccessMessageMixin, SetUserFieldMixin, InstructorRequiredMixin, CreateView):
    """
    Create a new course.
    Uses SuccessMessageMixin for automatic success messages and SetUserFieldMixin to set instructor.
    """
    model = Course
    template_name = 'courses/instructor/course_form.html'
    fields = [
        'title', 'slug', 'grade', 'description', 'cost',
        'content_rating', 'content_warnings',
        'image', 'preview_video_url', 'status', 'is_featured',
        'show_as_coming_soon', 'expected_launch_date'
    ]
    success_message = 'Course "{title}" created successfully!'
    user_field_name = 'instructor'

    def get_form(self, form_class=None):
        """Customize form widgets with proper styling"""
        form = super().get_form(form_class)
        # Add CSS classes to content rating fields
        form.fields['content_rating'].widget.attrs.update({
            'class': 'select select-bordered w-full'
        })
        form.fields['content_warnings'].widget.attrs.update({
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'e.g., "Contains historical art depicting nudity from Renaissance period"'
        })
        return form

    def get_success_url(self):
        # Redirect to topic management for the new course
        return reverse('courses:manage_topics', kwargs={'slug': self.object.slug})


class CourseUpdateView(SuccessMessageMixin, InstructorRequiredMixin, CourseInstructorMixin, UpdateView):
    """
    Edit an existing course. Uses SuccessMessageMixin.
    """
    model = Course
    template_name = 'courses/instructor/course_form.html'
    fields = [
        'title', 'slug', 'grade', 'description', 'cost',
        'content_rating', 'content_warnings',
        'image', 'preview_video_url', 'status', 'is_featured',
        'show_as_coming_soon', 'expected_launch_date'
    ]
    success_message = 'Course "{title}" updated successfully!'

    def get_form(self, form_class=None):
        """Customize form widgets with proper styling"""
        form = super().get_form(form_class)
        # Add CSS classes to content rating fields
        form.fields['content_rating'].widget.attrs.update({
            'class': 'select select-bordered w-full'
        })
        form.fields['content_warnings'].widget.attrs.update({
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'e.g., "Contains historical art depicting nudity from Renaissance period"'
        })
        return form

    def get_success_url(self):
        return reverse('courses:instructor_dashboard')


class CourseDeleteView(InstructorRequiredMixin, CourseInstructorMixin, DeleteView):
    """
    Delete a course (soft delete - set to archived).
    """
    model = Course
    template_name = 'courses/instructor/course_confirm_delete.html'
    success_url = reverse_lazy('courses:instructor_dashboard')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete - set status to archived
        self.object.status = Course.Status.ARCHIVED
        self.object.save()
        messages.success(request, f'Course "{self.object.title}" has been archived.')
        return redirect(self.success_url)


class TopicManageView(InstructorRequiredMixin, CourseInstructorMixin, DetailView):
    """
    Manage topics for a course (AJAX-powered interface).
    """
    model = Course
    template_name = 'courses/instructor/topic_manage.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        topics = self.object.topics.all().prefetch_related('lessons')
        context['topics'] = topics
        return context


class TopicCreateView(InstructorRequiredMixin, View):
    """
    AJAX endpoint to create a topic.
    """

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)

        # Check ownership
        if not course.is_owned_by(request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        topic_number = request.POST.get('topic_number')
        topic_title = request.POST.get('topic_title')
        description = request.POST.get('description', '')

        if not topic_number or not topic_title:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

        # Check if topic number already exists
        if Topic.objects.filter(course=course, topic_number=topic_number).exists():
            return JsonResponse({
                'success': False,
                'error': f'Topic number {topic_number} already exists'
            }, status=400)

        topic = Topic.objects.create(
            course=course,
            topic_number=topic_number,
            topic_title=topic_title,
            description=description
        )

        return JsonResponse({
            'success': True,
            'topic': {
                'id': str(topic.id),
                'topic_number': topic.topic_number,
                'topic_title': topic.topic_title,
                'description': topic.description,
            }
        })


class TopicUpdateView(InstructorRequiredMixin, View):
    """
    AJAX endpoint to update a topic.
    """

    def post(self, request, topic_id):
        topic = get_object_or_404(Topic, id=topic_id)

        # Check ownership
        if not topic.course.is_owned_by(request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        topic.topic_title = request.POST.get('topic_title', topic.topic_title)
        topic.description = request.POST.get('description', topic.description)
        topic.save()

        return JsonResponse({
            'success': True,
            'topic': {
                'id': str(topic.id),
                'topic_number': topic.topic_number,
                'topic_title': topic.topic_title,
                'description': topic.description,
            }
        })


class TopicDeleteView(InstructorRequiredMixin, View):
    """
    AJAX endpoint to delete a topic.
    """

    def post(self, request, topic_id):
        topic = get_object_or_404(Topic, id=topic_id)

        # Check ownership
        if not topic.course.is_owned_by(request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        # Check if topic has lessons
        if topic.lessons.exists():
            return JsonResponse({
                'success': False,
                'error': 'Cannot delete topic with lessons. Delete lessons first.'
            }, status=400)

        topic.delete()
        return JsonResponse({'success': True})


class LessonManageView(InstructorRequiredMixin, TemplateView):
    """
    Manage lessons for a topic (AJAX-powered interface).
    """
    template_name = 'courses/instructor/lesson_manage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        topic = get_object_or_404(Topic, course=course, topic_number=self.kwargs['topic_number'])

        # Check ownership
        if not course.is_owned_by(self.request.user):
            messages.error(self.request, 'Permission denied')
            return redirect('courses:instructor_dashboard')

        lessons = topic.lessons.all().prefetch_related('attachments')

        context.update({
            'course': course,
            'topic': topic,
            'lessons': lessons,
        })

        return context


class LessonReorderView(InstructorRequiredMixin, View):
    """
    POST endpoint: reorder lessons within a topic.
    Accepts JSON body: {"lesson_ids": ["uuid1", "uuid2", ...]}
    The new lesson_number is determined by position in the list (1-indexed).
    Handles unique_together constraint by first moving to a temporary offset.
    """

    def post(self, request, course_slug, topic_number):
        course = get_object_or_404(Course, slug=course_slug)
        if not course.is_owned_by(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        topic = get_object_or_404(Topic, course=course, topic_number=topic_number)

        try:
            data = json.loads(request.body)
            lesson_ids = data.get('lesson_ids', [])
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        lessons = {str(l.id): l for l in topic.lessons.all()}

        if set(lesson_ids) != set(lessons.keys()):
            return JsonResponse({'error': 'Lesson IDs do not match topic lessons'}, status=400)

        offset = 10000  # temp offset avoids unique_together collisions during renumber

        with transaction.atomic():
            # Pass 1: move all to temporary positions
            for i, lesson_id in enumerate(lesson_ids, start=1):
                lesson = lessons[lesson_id]
                lesson.lesson_number = offset + i
                lesson.save(update_fields=['lesson_number'])

            # Pass 2: set final positions
            for i, lesson_id in enumerate(lesson_ids, start=1):
                lesson = lessons[lesson_id]
                lesson.lesson_number = i
                lesson.save(update_fields=['lesson_number'])

        return JsonResponse({'status': 'ok'})


class InstructorLessonPreviewView(InstructorRequiredMixin, DetailView):
    """
    Instructor preview of any lesson regardless of status.
    Shows the student lesson view with an instructor banner and back link.
    """
    model = Lesson
    template_name = 'courses/student/lesson_view.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'

    def get_queryset(self):
        return Lesson.objects.select_related('topic__course')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        course = self.object.topic.course
        if not course.is_owned_by(request.user):
            messages.error(request, 'Permission denied.')
            return redirect('courses:instructor_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        course = lesson.topic.course
        topic = lesson.topic

        has_quiz = hasattr(lesson, 'quiz') and lesson.quiz.status == Quiz.Status.PUBLISHED

        # Prev/next based on published lessons only
        all_lessons = [
            l
            for t in course.topics.order_by('topic_number')
            for l in t.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number')
        ]
        try:
            idx = all_lessons.index(lesson)
            prev_lesson = all_lessons[idx - 1] if idx > 0 else None
            next_lesson = all_lessons[idx + 1] if idx < len(all_lessons) - 1 else None
        except ValueError:
            prev_lesson = None
            next_lesson = None

        # Sidebar navigation — no progress data in preview
        topics_with_progress = []
        for t in course.topics.order_by('topic_number'):
            lessons_data = [
                {'lesson': l, 'is_completed': False, 'is_current': l.id == lesson.id}
                for l in t.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number')
            ]
            if lessons_data:
                topics_with_progress.append({
                    'topic': t,
                    'lessons': lessons_data,
                    'completed': 0,
                    'total': len(lessons_data),
                    'progress_pct': 0,
                    'is_current_topic': t.id == topic.id,
                })

        context.update({
            'course': course,
            'topic': topic,
            'is_owner': True,
            'is_instructor_preview': True,
            'manage_lessons_url': reverse('courses:manage_lessons', kwargs={
                'course_slug': course.slug,
                'topic_number': topic.topic_number,
            }),
            'has_quiz': has_quiz,
            'quiz_passed': False,
            'best_attempt': None,
            'lesson_progress': None,
            'prev_lesson': prev_lesson,
            'next_lesson': next_lesson,
            'topics_with_progress': topics_with_progress,
        })
        return context


class LessonCreateView(SuccessMessageMixin, CourseContextMixin, InstructorRequiredMixin, CreateView):
    """
    Create a new lesson. Uses SuccessMessageMixin and CourseContextMixin.
    """
    model = Lesson
    template_name = 'courses/instructor/lesson_form.html'
    fields = [
        'lesson_number', 'lesson_title', 'content',
        'video_url', 'duration_minutes', 'is_preview', 'status'
    ]
    success_message = 'Lesson "{lesson_title}" created successfully!'

    def dispatch(self, request, *args, **kwargs):
        # Get and verify ownership
        self.course = get_object_or_404(Course, slug=kwargs['course_slug'])
        self.topic = get_object_or_404(Topic, course=self.course, topic_number=kwargs['topic_number'])

        if not self.course.is_owned_by(request.user):
            messages.error(request, 'Permission denied')
            return redirect('courses:instructor_dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        from django.db.models import Max
        max_num = self.topic.lessons.aggregate(Max('lesson_number'))['lesson_number__max']
        initial['lesson_number'] = (max_num or 0) + 1
        return initial

    def form_valid(self, form):
        form.instance.topic = self.topic
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:edit_lesson', kwargs={'lesson_id': self.object.id})


class LessonUpdateView(CourseOwnershipMixin, CourseContextMixin, InstructorRequiredMixin, UpdateView):
    """
    Edit an existing lesson. Uses CourseOwnershipMixin and CourseContextMixin.
    """
    model = Lesson
    template_name = 'courses/instructor/lesson_form.html'
    fields = [
        'lesson_number', 'lesson_title', 'content',
        'video_url', 'duration_minutes', 'is_preview', 'status'
    ]

    def get_context_data(self, **kwargs):
        # CourseContextMixin automatically adds course, topic, lesson
        context = super().get_context_data(**kwargs)

        # Add piece formset
        if self.request.POST:
            context['piece_formset'] = LessonPieceFormSet(self.request.POST, instance=self.object)
            context['attachment_formset'] = LessonAttachmentFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context['piece_formset'] = LessonPieceFormSet(instance=self.object)
            context['attachment_formset'] = LessonAttachmentFormSet(instance=self.object)

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        piece_formset = context['piece_formset']
        attachment_formset = context['attachment_formset']

        if piece_formset.is_valid() and attachment_formset.is_valid():
            self.object = form.save()
            piece_formset.instance = self.object
            piece_formset.save()
            attachment_formset.instance = self.object
            attachment_formset.save()
            messages.success(self.request, f'Lesson "{form.instance.lesson_title}" updated successfully!')
            return redirect(self.get_success_url())
        else:
            if not piece_formset.is_valid():
                messages.error(self.request, 'Please correct the errors in the playalong pieces section.')
            if not attachment_formset.is_valid():
                messages.error(self.request, 'Please correct the errors in the attachments section.')
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('courses:manage_lessons', kwargs={
            'course_slug': self.object.topic.course.slug,
            'topic_number': self.object.topic.topic_number
        })


class LessonAIAssistView(InstructorRequiredMixin, View):
    """
    AI assistant: draft lesson content from a natural language description.
    Accepts course/topic context to tailor the output.
    POST params:
      - description: instructor's notes on what the lesson should cover
      - course_slug + topic_number: context for new lessons
      - lesson_id: context for revising an existing lesson
    """

    def post(self, request, *args, **kwargs):
        import json
        from anthropic import Anthropic
        from django.db.models import Max

        ai_mode = request.POST.get('mode', '').strip()  # 'reformat', or blank for normal generate/revise
        description = request.POST.get('description', '').strip()
        if not description and ai_mode != 'reformat':
            return JsonResponse({'error': 'No description provided.'}, status=400)

        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            return JsonResponse({'error': 'AI assistant is not configured.'}, status=503)

        # Resolve course/topic context
        course = topic = existing_lesson = None
        lesson_id = request.POST.get('lesson_id', '').strip()
        course_slug = request.POST.get('course_slug', '').strip()
        topic_number = request.POST.get('topic_number', '').strip()

        if lesson_id:
            existing_lesson = get_object_or_404(Lesson, id=lesson_id)
            topic = existing_lesson.topic
            course = topic.course
            if not course.is_owned_by(request.user):
                return JsonResponse({'error': 'Permission denied.'}, status=403)
        elif course_slug and topic_number:
            course = get_object_or_404(Course, slug=course_slug)
            if not course.is_owned_by(request.user):
                return JsonResponse({'error': 'Permission denied.'}, status=403)
            topic = get_object_or_404(Topic, course=course, topic_number=int(topic_number))
        else:
            return JsonResponse({'error': 'Course context required.'}, status=400)

        if ai_mode == 'reformat' and not existing_lesson:
            return JsonResponse({'error': 'Reformat requires an existing lesson.'}, status=400)

        # Gather existing lesson titles in this topic for context
        existing_lessons_qs = topic.lessons.order_by('lesson_number').exclude(
            id=existing_lesson.id if existing_lesson else None
        )
        existing_lessons = list(existing_lessons_qs.values_list('lesson_number', 'lesson_title'))
        existing_lessons_text = '\n'.join(
            f'  Lesson {n}: {t}' for n, t in existing_lessons
        ) or '  (none yet)'

        grade_display = course.get_grade_display()
        mode = 'revise' if existing_lesson else 'draft'

        # Canonical style guide — exact HTML inline styles for every element type.
        # Applied to all AI-generated lessons to ensure visual consistency across the platform.
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
  <!-- If closing with a reflective note, separate it with a rule: -->
  <p style="font-size:0.95rem; color:#4a5a6a; line-height:1.75; margin:0; font-style:italic; border-top:1px solid #dde1e6; padding-top:12px; font-family:'Inter',system-ui,sans-serif;">Closing note.</p>
</div>

LISTS outside exercise boxes:
<ul style="font-size:1rem; color:#1e1e1e; line-height:1.8; margin:0 0 14px 0; padding-left:0; list-style:none; font-family:'Inter',system-ui,sans-serif;">
  <li style="padding:4px 0 4px 26px; position:relative;"><span style="position:absolute;left:0;color:#d94f3d;font-weight:bold;">&#9658;</span> Item text</li>
</ul>

IMAGE/NOTATION PLACEHOLDERS (use ONLY in new lessons when no actual image exists yet — NEVER replace an existing <img>, <figure>, or <svg> with this):
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
            prompt = f"""You are reformatting an existing recorder lesson to match the platform's visual style guide.

EXISTING LESSON CONTENT (full HTML):
{existing_lesson.content}

YOUR TASK: Reformat the HTML using the style guide below. Apply the exact inline styles specified to every element.

STRICT RULES — YOU MUST FOLLOW THESE EXACTLY:
- Do NOT change any words, sentences, paragraphs, or educational content
- Do NOT add, remove, or reorder any sections
- Do NOT change lesson title, duration, or any factual information
- ONLY replace the HTML markup and inline styles to match the style guide
- PRESERVE MEDIA VERBATIM: copy every <img>, <figure>, <svg>, <picture>, <audio>, <video>, and <source> element exactly character-for-character — do NOT simplify, replace, or omit them under any circumstances
- The IMAGE/NOTATION PLACEHOLDERS shown in the style guide are ONLY for use when drafting NEW lessons that need a placeholder — do NOT apply them to existing images or figures in this lesson
{LESSON_STYLE_GUIDE}
Use the generate_lesson tool to return your response."""

        elif mode == 'revise':
            prompt = f"""You are an expert recorder music teacher and editor. You are revising an existing lesson for an online recorder education platform.

Course: {course.title}
Grade level: {grade_display}
Topic: {topic.topic_number}. {topic.topic_title}

EXISTING LESSON CONTENT (full HTML):
{existing_lesson.content}

TEACHER'S REVISION INSTRUCTIONS:
{description}

YOUR TASK: Revise the lesson content according to the teacher's instructions above.

CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY:
- Preserve the existing text, structure, and HTML of sections you are NOT changing
- For any new sections or content you add, apply the style guide below precisely
- Do NOT reformat or restyle existing content that the teacher did not ask you to change
- Return the complete revised HTML — not a summary or partial content
{LESSON_STYLE_GUIDE}
Use the generate_lesson tool to return your response."""
        else:
            prompt = f"""You are an expert recorder music teacher and curriculum writer creating a new lesson for an online recorder education platform.

Course: {course.title}
Grade level: {grade_display}
Topic: {topic.topic_number}. {topic.topic_title}

Other lessons already in this topic:
{existing_lessons_text}

TEACHER'S NOTES FOR THIS LESSON:
{description}

YOUR TASK: Draft a complete new lesson based on the teacher's notes. Apply the style guide below to every element — use the exact inline styles specified, no exceptions.

Write 400–800 words covering: learning objective, explanation of the concept, practical exercises, and a summary. Tailor language and complexity to the grade level.
{LESSON_STYLE_GUIDE}
Use the generate_lesson tool to return your response."""

        tools = [{
            'name': 'generate_lesson',
            'description': 'Generate structured lesson content for the instructor to review.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'lesson_title': {'type': 'string'},
                    'content': {'type': 'string', 'description': 'Complete lesson content as valid HTML. Must preserve all existing inline styles, attributes, and formatting if revising. Do NOT return plain text or markdown.'},
                    'duration_minutes': {'type': 'integer'},
                    'suggested_quiz_questions': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'question': {'type': 'string'},
                                'answers': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'object',
                                        'properties': {
                                            'text': {'type': 'string'},
                                            'is_correct': {'type': 'boolean'},
                                        },
                                        'required': ['text', 'is_correct'],
                                    },
                                },
                            },
                            'required': ['question', 'answers'],
                        },
                    },
                    'summary': {'type': 'string'},
                },
                'required': ['lesson_title', 'content', 'duration_minutes', 'suggested_quiz_questions', 'summary'],
            },
        }]

        # Reformat and revise send full lesson HTML — use Sonnet for larger context/output.
        # Draft (new lesson) only needs to generate content, Haiku is sufficient.
        if ai_mode in ('reformat', 'revise'):
            model = 'claude-sonnet-4-6'
            max_tokens = 16000
        else:
            model = 'claude-haiku-4-5-20251001'
            max_tokens = 4096

        try:
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice={'type': 'tool', 'name': 'generate_lesson'},
                messages=[{'role': 'user', 'content': prompt}],
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error('AI assist API call failed: %s', e)
            return JsonResponse({'error': 'AI service unavailable. Please try again later.'}, status=503)

        if message.stop_reason == 'max_tokens':
            return JsonResponse({'error': 'The lesson is too long to process in one request. Try splitting it into shorter sections.'}, status=500)

        try:
            data = message.content[0].input
        except (IndexError, AttributeError) as e:
            import logging
            logging.getLogger(__name__).error('AI assist unexpected response: %s', e)
            return JsonResponse({'error': 'Unexpected AI response. Please try again.'}, status=500)

        return JsonResponse(data)


class LessonDeleteView(CourseOwnershipMixin, InstructorRequiredMixin, DeleteView):
    """
    Delete a lesson. Uses CourseOwnershipMixin.
    """
    model = Lesson
    template_name = 'courses/instructor/lesson_confirm_delete.html'

    def get_success_url(self):
        """Return URL to redirect to after successful deletion"""
        return reverse('courses:manage_lessons', kwargs={
            'course_slug': self.object.topic.course.slug,
            'topic_number': self.object.topic.topic_number
        })

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        lesson_title = self.object.lesson_title

        # Add success message before deleting
        messages.success(request, f'Lesson "{lesson_title}" has been deleted.')

        return super().delete(request, *args, **kwargs)


class QuizManageView(CourseOwnershipMixin, CourseContextMixin, InstructorRequiredMixin, DetailView):
    """
    Manage quiz for a lesson. Uses CourseOwnershipMixin and CourseContextMixin.
    """
    model = Lesson
    template_name = 'courses/instructor/quiz_manage.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'

    def get_context_data(self, **kwargs):
        # CourseContextMixin automatically adds course, topic, lesson
        context = super().get_context_data(**kwargs)

        # Get or create quiz for this lesson
        quiz, created = Quiz.objects.get_or_create(
            course_lesson=self.object,
            defaults={
                'title': f'Quiz: {self.object.lesson_title}',
                'status': Quiz.Status.DRAFT
            }
        )

        questions = quiz.questions.all().prefetch_related('answers').order_by('order')

        context.update({
            'quiz': quiz,
            'questions': questions,
        })

        return context


class QuizUpdateView(InstructorRequiredMixin, View):
    """
    Update quiz settings via AJAX.
    """
    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        lesson = quiz.course_lesson

        # Verify ownership
        if not lesson.topic.course.is_owned_by(request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)

        # Update quiz fields
        title = data.get('title')
        pass_percentage = data.get('pass_percentage')
        status = data.get('status')

        if title:
            quiz.title = title
        if pass_percentage is not None:
            try:
                pass_pct = int(pass_percentage)
                if 0 <= pass_pct <= 100:
                    quiz.pass_percentage = pass_pct
                else:
                    return JsonResponse({'success': False, 'error': 'Pass percentage must be between 0 and 100'}, status=400)
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid pass percentage'}, status=400)

        if status in [Quiz.Status.DRAFT, Quiz.Status.PUBLISHED]:
            quiz.status = status

        quiz.save()

        return JsonResponse({
            'success': True,
            'message': 'Quiz settings updated successfully',
            'quiz': {
                'title': quiz.title,
                'pass_percentage': quiz.pass_percentage,
                'status': quiz.status,
            }
        })


class QuizQuestionCreateView(InstructorRequiredMixin, CreateView):
    """
    Create a quiz question with answers (using formset).
    """
    model = QuizQuestion
    template_name = 'courses/instructor/question_form.html'
    form_class = None  # Will use fields instead
    fields = ['text', 'points', 'order']

    def dispatch(self, request, *args, **kwargs):
        # Get quiz and verify ownership
        self.quiz = get_object_or_404(Quiz, id=kwargs['quiz_id'])
        lesson = self.quiz.course_lesson

        if not lesson.topic.course.is_owned_by(request.user):
            messages.error(request, 'Permission denied')
            return redirect('courses:instructor_dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .forms import QuizAnswerFormSet

        if self.request.POST:
            context['answer_formset'] = QuizAnswerFormSet(self.request.POST, instance=self.object)
        else:
            context['answer_formset'] = QuizAnswerFormSet(instance=self.object)

        # Set context vars based on self.quiz
        context['quiz'] = self.quiz
        context['lesson'] = self.quiz.course_lesson
        context['course'] = self.quiz.course_lesson.topic.course
        context['topic'] = self.quiz.course_lesson.topic

        return context

    def form_valid(self, form):
        from .forms import QuizAnswerFormSet

        # Set the quiz before saving
        form.instance.quiz = self.quiz

        # Auto-set order if not provided
        if not form.instance.order:
            max_order = self.quiz.questions.aggregate(Max('order'))['order__max'] or 0
            form.instance.order = max_order + 1

        # Save the question
        self.object = form.save()

        # Handle the answer formset
        answer_formset = QuizAnswerFormSet(self.request.POST, instance=self.object)

        if answer_formset.is_valid():
            # Check exactly one answer is marked correct
            correct_count = sum(1 for form in answer_formset if form.cleaned_data.get('is_correct') and not form.cleaned_data.get('DELETE'))
            if correct_count != 1:
                messages.error(self.request, 'Exactly one answer must be marked as correct.')
                return self.form_invalid(form)

            answer_formset.save()
            messages.success(self.request, 'Question created successfully!')
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, 'Please fix the errors in the answers.')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('courses:manage_quiz', kwargs={'lesson_id': self.quiz.course_lesson.id})


class QuizQuestionUpdateView(CourseOwnershipMixin, CourseContextMixin, InstructorRequiredMixin, UpdateView):
    """
    Update a quiz question with answers (using formset). Uses CourseOwnershipMixin and CourseContextMixin.
    """
    model = QuizQuestion
    template_name = 'courses/instructor/question_form.html'
    fields = ['text', 'points', 'order']
    pk_url_kwarg = 'question_id'

    def get_context_data(self, **kwargs):
        # CourseContextMixin automatically adds quiz, lesson, course, topic
        context = super().get_context_data(**kwargs)
        from .forms import QuizAnswerFormSet

        if self.request.POST:
            context['answer_formset'] = QuizAnswerFormSet(self.request.POST, instance=self.object)
        else:
            context['answer_formset'] = QuizAnswerFormSet(instance=self.object)

        return context

    def form_valid(self, form):
        from .forms import QuizAnswerFormSet

        # Save the question
        self.object = form.save()

        # Handle the answer formset
        answer_formset = QuizAnswerFormSet(self.request.POST, instance=self.object)

        if answer_formset.is_valid():
            # Check exactly one answer is marked correct
            correct_count = sum(1 for form in answer_formset if form.cleaned_data.get('is_correct') and not form.cleaned_data.get('DELETE'))
            if correct_count != 1:
                messages.error(self.request, 'Exactly one answer must be marked as correct.')
                return self.form_invalid(form)

            answer_formset.save()
            messages.success(self.request, 'Question updated successfully!')
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, 'Please fix the errors in the answers.')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('courses:manage_quiz', kwargs={'lesson_id': self.object.quiz.course_lesson.id})


class QuizQuestionDeleteView(CourseOwnershipMixin, CourseContextMixin, InstructorRequiredMixin, DeleteView):
    """
    Delete a quiz question. Uses CourseOwnershipMixin and CourseContextMixin.
    """
    model = QuizQuestion
    template_name = 'courses/instructor/question_confirm_delete.html'
    pk_url_kwarg = 'question_id'

    def get_success_url(self):
        return reverse('courses:manage_quiz', kwargs={'lesson_id': self.object.quiz.course_lesson.id})

    def delete(self, request, *args, **kwargs):
        # Add success message before deleting
        messages.success(request, 'Question deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# PUBLIC COURSE BROWSING (Placeholder for Phase 3)
# ============================================================================

class CourseListView(SearchableListViewMixin, ListView):
    """
    Public course catalog with filtering by grade and search.
    """
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12

    # Configure SearchableListViewMixin
    search_fields = ['title', 'description']
    filter_mappings = {
        'grade': lambda qs, val: qs.filter(grade=val) if val != 'all' else qs,
    }
    sort_options = {
        'featured': ('-is_featured', 'created_at'),
    }
    default_sort = 'featured'

    def get_queryset(self):
        # Include published courses AND courses with "coming soon" enabled (regardless of status)
        # For coming soon courses, auto-hide if expected launch date is 30+ days past
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        queryset = Course.objects.filter(
            Q(status=Course.Status.PUBLISHED) |
            Q(
                show_as_coming_soon=True
            ) & (
                Q(expected_launch_date__isnull=True) |  # No launch date set
                Q(expected_launch_date__gte=thirty_days_ago)  # Launch date within last 30 days
            )
        )

        # Apply search, filters, and sorting from mixin
        queryset = self.filter_queryset(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grade_choices'] = Course.GRADE_CHOICES
        context['current_grade'] = self.request.GET.get('grade', 'all')
        context['current_search'] = self.request.GET.get('search', '')
        grade_label_map = dict(Course.GRADE_CHOICES)
        context['current_grade_label'] = grade_label_map.get(context['current_grade'], context['current_grade'])
        return context


class CourseDetailView(DetailView):
    """
    Course detail page showing course information and curriculum.
    """
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        # Show published courses AND courses with "coming soon" enabled (regardless of status)
        # Owners can see all their courses regardless of status
        if self.request.user.is_authenticated and hasattr(self, 'object'):
            if self.object.is_owned_by(self.request.user):
                return Course.objects.all()

        # For non-owners, show published + coming soon courses (with auto-hide logic)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        return Course.objects.filter(
            Q(status=Course.Status.PUBLISHED) |
            Q(
                show_as_coming_soon=True
            ) & (
                Q(expected_launch_date__isnull=True) |
                Q(expected_launch_date__gte=thirty_days_ago)
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if user is enrolled
        is_enrolled = False
        enrollment = None
        is_guardian = False
        if self.request.user.is_authenticated:
            enrollment = CourseEnrollment.objects.filter(
                course=self.object,
                student=self.request.user,
                is_active=True
            ).first()
            is_enrolled = enrollment is not None
            is_guardian = self.request.user.profile.is_guardian

        # Get course curriculum (topics with lessons)
        topics = self.object.topics.prefetch_related(
            'lessons'
        ).order_by('topic_number')

        # Calculate course stats dynamically using aggregate (PERFORMANCE FIX)
        from django.db.models import Sum, Count, Q
        stats = self.object.topics.aggregate(
            total_lessons=Count('lessons', filter=Q(lessons__status=Lesson.Status.PUBLISHED)),
            total_duration=Sum('lessons__duration_minutes', filter=Q(lessons__status=Lesson.Status.PUBLISHED))
        )
        total_lessons = stats['total_lessons'] or 0
        total_duration = stats['total_duration'] or 0

        # Find first incomplete lesson for enrolled students
        continue_url = None
        if is_enrolled and enrollment:
            completed_ids = set(LessonProgress.objects.filter(
                enrollment=enrollment, is_completed=True
            ).values_list('lesson_id', flat=True))
            for topic in self.object.topics.order_by('topic_number').prefetch_related('lessons'):
                for lesson in topic.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number'):
                    if lesson.id not in completed_ids:
                        continue_url = reverse('courses:view_lesson', kwargs={'lesson_id': lesson.id})
                        break
                if continue_url:
                    break

        context.update({
            'is_enrolled': is_enrolled,
            'enrollment': enrollment,
            'continue_url': continue_url,
            'topics': topics,
            'total_lessons': total_lessons,
            'total_duration': total_duration,
            'is_owner': self.request.user.is_authenticated and self.object.is_owned_by(self.request.user),
            'is_guardian': is_guardian,
        })

        return context


class CourseEnrollView(LoginRequiredMixin, View):
    """
    Enroll a student in a course.
    - For guardians: Show child selection page (GET) then enroll selected child (POST)
    - For regular students: Enroll directly (POST only)
    """
    def get(self, request, slug):
        """Show child selection page for guardians"""
        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)

        # If not a guardian, redirect to POST (direct enrollment)
        if not request.user.profile.is_guardian:
            # For non-guardians, POST to enroll themselves
            return self.post(request, slug)

        # Get guardian's children
        children = request.user.children.all()

        if not children:
            messages.warning(request, 'You need to add at least one child profile before enrolling in a course.')
            return redirect('accounts:add_child')

        context = {
            'course': course,
            'children': children,
        }
        return render(request, 'courses/select_child_for_enrollment.html', context)

    def post(self, request, slug):
        """Process enrollment"""
        from decimal import Decimal
        from apps.payments.voucher_service import VoucherService, VoucherValidationError

        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)
        child_id = request.POST.get('child_id')
        terms_accepted = request.POST.get('terms_accepted')
        voucher_code = request.POST.get('voucher_code', '').strip().upper()

        # Check T&Cs acceptance
        if not terms_accepted:
            messages.error(request, 'You must accept the Terms and Conditions to enroll.')
            if child_id:
                # Redirect back to child selection page
                return redirect('courses:enroll', slug=course.slug)
            else:
                return redirect('courses:detail', slug=course.slug)

        # Determine if enrolling a child or self
        child = None
        if request.user.profile.is_guardian and child_id:
            # Enrolling a child
            from apps.accounts.models import ChildProfile
            try:
                child = ChildProfile.objects.get(id=child_id, guardian=request.user)
            except ChildProfile.DoesNotExist:
                messages.error(request, 'Invalid child selected.')
                return redirect('courses:detail', slug=course.slug)

            # Check if child already enrolled
            existing_enrollment = CourseEnrollment.objects.filter(
                course=course,
                student=request.user,
                child_profile=child
            ).first()

            if existing_enrollment:
                messages.info(request, f'{child.full_name} is already enrolled in {course.title}.')
                return redirect('courses:detail', slug=course.slug)

            # CHECK AGE RATING / CONTENT APPROPRIATENESS
            requires_ack, is_blocked, rating_message = course.requires_age_acknowledgment(child.age)

            if is_blocked:
                # Hard block (18+ content for under 18)
                messages.error(request, rating_message)
                return redirect('courses:detail', slug=course.slug)

            if requires_ack:
                # Requires guardian acknowledgment (13+/16+ for under age)
                age_acknowledged = request.POST.get('age_rating_acknowledged')
                if not age_acknowledged:
                    # Redirect to acknowledgment page
                    context = {
                        'course': course,
                        'child': child,
                        'rating_message': rating_message,
                    }
                    return render(request, 'courses/age_rating_acknowledgment.html', context)

        else:
            # Enrolling self (adult student)
            existing_enrollment = CourseEnrollment.objects.filter(
                course=course,
                student=request.user,
                child_profile=None
            ).first()

            if existing_enrollment:
                messages.info(request, f'You are already enrolled in {course.title}.')
                return redirect('courses:detail', slug=course.slug)

        # Check if course requires payment
        is_paid_course = course.cost > 0

        # Validate voucher if provided
        applied_voucher = None
        discount_amount = Decimal('0.00')
        final_cost = course.cost

        if voucher_code and is_paid_course:
            try:
                applied_voucher = VoucherService.validate_voucher(
                    code=voucher_code,
                    student=request.user,
                    domain='courses',
                    cart_total=course.cost,
                    teacher=course.instructor
                )
                discount_amount, final_cost = VoucherService.calculate_discount(applied_voucher, course.cost)
            except VoucherValidationError as e:
                messages.error(request, str(e))
                return redirect('courses:detail', slug=course.slug)

        if is_paid_course and final_cost > 0:
            # PAID COURSE (with or without partial voucher): proceed to Stripe
            enrollment = CourseEnrollment.objects.create(
                course=course,
                student=request.user,
                child_profile=child,
                payment_status='pending',
                payment_amount=final_cost,
                is_active=True
            )

            # Create T&Cs acceptance record
            from .models import CourseTermsAndConditions, CourseTermsAcceptance
            current_terms = CourseTermsAndConditions.objects.filter(is_current=True).first()
            if current_terms:
                CourseTermsAcceptance.objects.create(
                    enrollment=enrollment,
                    terms_version=current_terms,
                    ip_address=request.META.get('REMOTE_ADDR')
                )

            # Create Stripe checkout session
            from apps.payments.stripe_service import create_checkout_session
            from django.urls import reverse

            success_url = request.build_absolute_uri(
                reverse('courses:checkout_success', kwargs={'enrollment_id': enrollment.id})
            )
            cancel_url = request.build_absolute_uri(
                reverse('courses:checkout_cancel', kwargs={'enrollment_id': enrollment.id})
            )

            try:
                item_name = course.title
                item_description = f"Course enrollment - {course.get_grade_display()}"

                metadata = {
                    'enrollment_id': str(enrollment.id),
                    'course_id': str(course.id),
                    'child_id': str(child.id) if child else '',
                }

                # Add voucher metadata so the webhook can record the redemption
                coupon_id = None
                if applied_voucher:
                    metadata['voucher_id'] = str(applied_voucher.id)
                    metadata['voucher_code'] = applied_voucher.code
                    metadata['original_amount'] = str(course.cost)
                    metadata['discount_amount'] = str(discount_amount)
                    coupon_id = VoucherService.create_or_get_stripe_coupon(applied_voucher)

                session = create_checkout_session(
                    amount=final_cost,
                    student=request.user,
                    teacher=course.instructor,
                    domain='courses',
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata=metadata,
                    item_name=item_name,
                    item_description=item_description,
                    coupon_id=coupon_id
                )

                # Save session ID to enrollment
                enrollment.stripe_checkout_session_id = session.id
                enrollment.save()

                # Redirect to Stripe Checkout
                return redirect(session.url, code=303)

            except Exception as e:
                # If Stripe checkout creation fails, delete the enrollment
                enrollment.delete()
                messages.error(request, f"Payment setup failed: {str(e)}. Please try again.")
                return redirect('courses:detail', slug=course.slug)

        elif is_paid_course and final_cost == 0:
            # VOUCHER MAKES COURSE FREE: bypass Stripe
            from django.utils import timezone as tz
            enrollment = CourseEnrollment.objects.create(
                course=course,
                student=request.user,
                child_profile=child,
                payment_status='completed',
                payment_amount=Decimal('0.00'),
                paid_at=tz.now(),
                is_active=True
            )

            # Create T&Cs acceptance record
            from .models import CourseTermsAndConditions, CourseTermsAcceptance
            current_terms = CourseTermsAndConditions.objects.filter(is_current=True).first()
            if current_terms:
                CourseTermsAcceptance.objects.create(
                    enrollment=enrollment,
                    terms_version=current_terms,
                    ip_address=request.META.get('REMOTE_ADDR')
                )

            # Record voucher redemption
            VoucherService.create_redemption(
                voucher=applied_voucher,
                student=request.user,
                domain='courses',
                original_amount=course.cost,
                discount_amount=discount_amount,
                final_amount=Decimal('0.00'),
                request=request,
                course_enrollment=enrollment
            )

            # Update course enrollment count
            course.total_enrollments = CourseEnrollment.objects.filter(
                course=course,
                is_active=True,
                payment_status__in=['completed', 'not_required']
            ).count()
            course.save(update_fields=['total_enrollments'])

            # Send notifications
            try:
                from .notifications import InstructorNotificationService
                InstructorNotificationService.send_new_enrollment_notification(enrollment)
            except Exception as e:
                print(f"Failed to send instructor notification: {e}")

            student_name = child.full_name if child else 'You'
            messages.success(
                request,
                f'{student_name} {"has" if child else "have"} been successfully enrolled in {course.title}!'
            )
            return redirect('courses:enrollment_confirm', enrollment_id=enrollment.id)

        else:
            # FREE COURSE: Immediate enrollment
            enrollment = CourseEnrollment.objects.create(
                course=course,
                student=request.user,
                child_profile=child,
                payment_status='not_required',
                payment_amount=0,
                is_active=True
            )

            # Create T&Cs acceptance record
            from .models import CourseTermsAndConditions, CourseTermsAcceptance
            current_terms = CourseTermsAndConditions.objects.filter(is_current=True).first()
            if current_terms:
                CourseTermsAcceptance.objects.create(
                    enrollment=enrollment,
                    terms_version=current_terms,
                    ip_address=request.META.get('REMOTE_ADDR')
                )

            # Update course enrollment count
            course.total_enrollments = CourseEnrollment.objects.filter(
                course=course,
                is_active=True
            ).count()
            course.save(update_fields=['total_enrollments'])

            # Send notification to instructor
            try:
                from .notifications import InstructorNotificationService
                InstructorNotificationService.send_new_enrollment_notification(enrollment)
            except Exception as e:
                # Don't fail the enrollment if email fails
                print(f"Failed to send instructor notification: {e}")

            student_name = child.full_name if child else 'You'
            messages.success(
                request,
                f'{student_name} {"has" if child else "have"} been successfully enrolled in {course.title}!'
            )

            return redirect('courses:enrollment_confirm', enrollment_id=enrollment.id)


class CourseCheckoutSuccessView(BaseCheckoutSuccessView):
    """Handle return from Stripe after successful checkout"""
    template_name = 'courses/checkout_success.html'

    def get_object_model(self):
        return CourseEnrollment

    def get_object_id_kwarg(self):
        return 'enrollment_id'

    def get_redirect_url_name(self):
        return 'courses:list'

    def get_object_queryset(self):
        return CourseEnrollment.objects.select_related('course', 'student', 'child_profile')

    def perform_post_checkout_actions(self, obj):
        """Confirm payment status via Stripe session as fallback if webhook hasn't fired yet"""
        if obj.payment_status == 'pending' and obj.stripe_checkout_session_id:
            try:
                from apps.payments.stripe_service import retrieve_session
                from django.utils import timezone
                session = retrieve_session(obj.stripe_checkout_session_id)
                if session and session.payment_status == 'paid':
                    obj.payment_status = 'completed'
                    obj.paid_at = timezone.now()
                    obj.save(update_fields=['payment_status', 'paid_at'])
            except Exception:
                pass  # Webhook will handle it

    def get_context_extras(self, obj):
        return {
            'enrollment': obj,
            'course': obj.course,
            'child': obj.child_profile,
        }


class CourseCheckoutCancelView(BaseCheckoutCancelView):
    """Handle cancelled checkout"""
    template_name = 'courses/checkout_cancel.html'

    def get_object_model(self):
        return CourseEnrollment

    def get_object_id_kwarg(self):
        return 'enrollment_id'

    def get_redirect_url_name(self):
        return 'courses:list'

    def get_object_queryset(self):
        return CourseEnrollment.objects.select_related('course', 'student', 'child_profile')

    def get_cancel_message(self):
        return 'Payment was cancelled. You can try again from the course page.'

    def get_context_extras(self, obj):
        return {
            'enrollment': obj,
            'course': obj.course,
            'child': obj.child_profile,
        }


class CourseEnrollmentConfirmView(LoginRequiredMixin, TemplateView):
    """Show enrollment confirmation page"""
    template_name = 'courses/enrollment_confirm.html'

    def get(self, request, *args, **kwargs):
        enrollment_id = kwargs.get('enrollment_id')

        try:
            enrollment = CourseEnrollment.objects.select_related(
                'course', 'student', 'child_profile'
            ).get(id=enrollment_id, student=request.user)

            context = self.get_context_data(**kwargs)
            context['enrollment'] = enrollment
            context['course'] = enrollment.course
            context['child'] = enrollment.child_profile

            return self.render_to_response(context)

        except CourseEnrollment.DoesNotExist:
            messages.error(request, 'Enrollment not found.')
            return redirect('courses:list')


class LessonPreviewView(DetailView):
    """
    Public preview of a lesson marked as is_preview=True.
    No authentication required - allows anonymous users to preview before enrolling.
    """
    model = Lesson
    template_name = 'courses/lesson_preview.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'

    def get_queryset(self):
        # Only allow preview of lessons that are:
        # 1. Published
        # 2. Marked as preview
        # 3. In a published course
        return Lesson.objects.filter(
            status=Lesson.Status.PUBLISHED,
            is_preview=True,
            topic__course__status=Course.Status.PUBLISHED,
            topic__course__slug=self.kwargs['slug']
        ).select_related('topic__course')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.topic.course
        context['is_preview'] = True
        return context


class StudentDashboardView(LoginRequiredMixin, TemplateView):
    """
    Student dashboard showing enrolled courses and progress.
    """
    template_name = 'courses/student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get active enrollments with course data
        enrollments = CourseEnrollment.objects.filter(
            student=self.request.user,
            is_active=True
        ).select_related('course', 'course__instructor').order_by('-enrolled_at')

        # Calculate stats for each enrollment
        total_completed_lessons = 0
        total_certificates = 0

        for enrollment in enrollments:
            # Get total lessons in course
            total_lessons = enrollment.course.topics.aggregate(
                total=Count('lessons', filter=Q(lessons__status=Lesson.Status.PUBLISHED))
            )['total'] or 0

            # Get completed lessons
            completed_lesson_ids = set(LessonProgress.objects.filter(
                enrollment=enrollment,
                is_completed=True
            ).values_list('lesson_id', flat=True))
            completed_lessons = len(completed_lesson_ids)

            # Calculate progress percentage (use custom attributes, not model properties)
            if total_lessons > 0:
                enrollment.calculated_progress = int((completed_lessons / total_lessons) * 100)
            else:
                enrollment.calculated_progress = 0

            enrollment.calculated_completed = completed_lessons
            enrollment.calculated_total = total_lessons

            total_completed_lessons += completed_lessons

            # Count certificates
            if enrollment.completed_at:
                total_certificates += 1

            # Find first incomplete published lesson for "Continue" button
            enrollment.continue_url = None
            for topic in enrollment.course.topics.order_by('topic_number').prefetch_related('lessons'):
                for lesson in topic.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number'):
                    if lesson.id not in completed_lesson_ids:
                        enrollment.continue_url = reverse('courses:view_lesson', kwargs={'lesson_id': lesson.id})
                        break
                if enrollment.continue_url:
                    break

        context.update({
            'enrollments': enrollments,
            'total_courses': enrollments.count(),
            'total_completed_lessons': total_completed_lessons,
            'total_certificates': total_certificates,
        })

        return context


class LessonViewView(LoginRequiredMixin, DetailView):
    """
    View a specific lesson (requires enrollment).
    """
    model = Lesson
    template_name = 'courses/student/lesson_view.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check if user is enrolled in the course or is the owner
        course = self.object.topic.course
        self.is_owner = course.is_owned_by(request.user)

        if not self.is_owner:
            enrollment = CourseEnrollment.objects.filter(
                course=course,
                student=request.user,
                is_active=True
            ).first()

            if not enrollment:
                messages.error(request, 'You must be enrolled in this course to view lessons.')
                return redirect('courses:detail', slug=course.slug)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course = self.object.topic.course
        topic = self.object.topic

        # Get enrollment and progress
        enrollment = CourseEnrollment.objects.filter(
            course=course,
            student=self.request.user,
            is_active=True
        ).first()

        lesson_progress = None
        if enrollment:
            lesson_progress, created = LessonProgress.objects.get_or_create(
                enrollment=enrollment,
                lesson=self.object
            )

        # Check for quiz and quiz completion
        has_quiz = hasattr(self.object, 'quiz') and self.object.quiz.status == Quiz.Status.PUBLISHED
        quiz_passed = False
        best_attempt = None

        if has_quiz and enrollment:
            # Get best passing attempt for this quiz
            best_attempt = QuizAttempt.objects.filter(
                assignment__course_enrollment=enrollment,
                assignment__quiz=self.object.quiz,
                passed=True
            ).order_by('-score').first()
            quiz_passed = best_attempt is not None

        # Get all lessons in order for navigation
        all_lessons = []
        for t in course.topics.order_by('topic_number'):
            for lesson in t.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number'):
                all_lessons.append(lesson)

        # Find current lesson index
        try:
            current_index = all_lessons.index(self.object)
            prev_lesson = all_lessons[current_index - 1] if current_index > 0 else None
            next_lesson = all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None
        except (ValueError, IndexError):
            prev_lesson = None
            next_lesson = None

        # Get all topics with lessons and progress for sidebar navigation
        topics_with_progress = []

        # Get all completed lesson IDs for efficiency (if enrolled)
        completed_lesson_ids = set()
        if enrollment:
            completed_lesson_ids = set(
                LessonProgress.objects.filter(
                    enrollment=enrollment,
                    is_completed=True
                ).values_list('lesson_id', flat=True)
            )

        # Build navigation for all users (both enrolled students and owners)
        for t in course.topics.order_by('topic_number'):
            lessons_data = []
            published_lessons = t.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number')

            for lesson in published_lessons:
                lessons_data.append({
                    'lesson': lesson,
                    'is_completed': lesson.id in completed_lesson_ids,
                    'is_current': lesson.id == self.object.id,
                })

            # Only include topics that have published lessons
            if lessons_data:
                # Calculate topic progress
                topic_completed = sum(1 for l in lessons_data if l['is_completed'])
                topic_total = len(lessons_data)
                topic_progress_pct = int((topic_completed / topic_total * 100)) if topic_total > 0 else 0

                topics_with_progress.append({
                    'topic': t,
                    'lessons': lessons_data,
                    'completed': topic_completed,
                    'total': topic_total,
                    'progress_percentage': topic_progress_pct,
                    'is_current_topic': t.id == topic.id,
                })

        context.update({
            'course': course,
            'topic': topic,
            'enrollment': enrollment,
            'lesson_progress': lesson_progress,
            'prev_lesson': prev_lesson,
            'next_lesson': next_lesson,
            'is_owner': course.is_owned_by(self.request.user),
            'has_quiz': has_quiz,
            'quiz_passed': quiz_passed,
            'best_attempt': best_attempt,
            'topics_with_progress': topics_with_progress,
        })

        return context


class MarkLessonCompleteView(LoginRequiredMixin, View):
    """
    Mark a lesson as complete (AJAX endpoint).
    """
    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        course = lesson.topic.course

        # Get enrollment
        enrollment = CourseEnrollment.objects.filter(
            course=course,
            student=request.user,
            is_active=True
        ).first()

        if not enrollment:
            return JsonResponse({'success': False, 'error': 'Not enrolled'}, status=403)

        # Check if lesson has a quiz requirement
        has_quiz = hasattr(lesson, 'quiz') and lesson.quiz.status == Quiz.Status.PUBLISHED

        if has_quiz:
            # Check if student has passed the quiz
            quiz_passed = QuizAttempt.objects.filter(
                assignment__course_enrollment=enrollment,
                assignment__quiz=lesson.quiz,
                passed=True
            ).exists()

            if not quiz_passed:
                return JsonResponse({
                    'success': False,
                    'error': 'You must complete and pass the quiz before marking this lesson as complete.'
                }, status=400)

        # Get or create lesson progress
        lesson_progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )

        # Mark as complete
        if not lesson_progress.is_completed:
            lesson_progress.is_completed = True
            lesson_progress.completed_at = timezone.now()
            lesson_progress.save()

        # Compute updated progress percentage for the response
        total_lessons = course.topics.aggregate(
            total=Count('lessons', filter=Q(lessons__status=Lesson.Status.PUBLISHED))
        )['total'] or 0
        completed_lessons = LessonProgress.objects.filter(
            enrollment=enrollment, is_completed=True
        ).count()
        progress_percentage = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

        return JsonResponse({'success': True, 'progress_percentage': progress_percentage})


class QuizTakeView(LoginRequiredMixin, DetailView):
    """
    Display quiz for a student to take.
    """
    model = Lesson
    template_name = 'courses/student/quiz_take.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        course = self.object.topic.course

        # Check if lesson has a quiz
        if not hasattr(self.object, 'quiz') or self.object.quiz.status != Quiz.Status.PUBLISHED:
            messages.error(request, 'This lesson does not have a quiz.')
            return redirect('courses:view_lesson', lesson_id=self.object.id)

        # Check enrollment
        enrollment = CourseEnrollment.objects.filter(
            course=course,
            student=request.user,
            is_active=True
        ).first()

        if not enrollment:
            messages.error(request, 'You must be enrolled in this course to take quizzes.')
            return redirect('courses:detail', slug=course.slug)

        self.enrollment = enrollment
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        quiz = self.object.quiz
        course = self.object.topic.course

        # Get quiz questions with answers
        questions = quiz.get_questions()

        # Get previous attempts
        previous_attempts = QuizAttempt.objects.filter(
            assignment__course_enrollment=self.enrollment,
            assignment__quiz=quiz,
            submitted_at__isnull=False
        ).order_by('-submitted_at')

        # Get best score
        best_attempt = previous_attempts.filter(passed=True).order_by('-score').first()

        context.update({
            'course': course,
            'quiz': quiz,
            'questions': questions,
            'previous_attempts': previous_attempts[:5],  # Show last 5 attempts
            'best_attempt': best_attempt,
        })

        return context


class QuizSubmitView(LoginRequiredMixin, View):
    """
    Submit quiz answers and grade the attempt.
    """
    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        course = lesson.topic.course

        # Check if lesson has a quiz
        if not hasattr(lesson, 'quiz') or lesson.quiz.status != Quiz.Status.PUBLISHED:
            return JsonResponse({'success': False, 'error': 'Quiz not found'}, status=404)

        quiz = lesson.quiz

        # Get enrollment
        enrollment = CourseEnrollment.objects.filter(
            course=course,
            student=request.user,
            is_active=True
        ).first()

        if not enrollment:
            return JsonResponse({'success': False, 'error': 'Not enrolled'}, status=403)

        # Parse submitted answers from request
        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)

        # Get or create quiz assignment, then create attempt
        assignment, _ = QuizAssignment.objects.get_or_create(
            quiz=quiz,
            course_enrollment=enrollment,
        )
        attempt = QuizAttempt.objects.create(
            assignment=assignment,
            answers_data=answers
        )

        # Grade the attempt
        result = attempt.grade()

        # If passed, automatically mark lesson as complete
        if attempt.passed:
            lesson_progress, created = LessonProgress.objects.get_or_create(
                enrollment=enrollment,
                lesson=lesson
            )
            if not lesson_progress.is_completed:
                lesson_progress.mark_complete()  # Use mark_complete() to trigger course completion check

        return JsonResponse({
            'success': True,
            'score': float(attempt.score),
            'passed': attempt.passed,
            'pass_percentage': quiz.pass_percentage,
            'lesson_id': str(lesson.id),
        })


# ============================================================================
# ANALYTICS VIEWS
# ============================================================================

class CourseAnalyticsView(LoginRequiredMixin, TemplateView):
    """
    High-level analytics showing all instructor's courses with aggregated statistics.
    """
    template_name = 'courses/instructor/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all courses taught by this instructor
        courses = Course.objects.filter(instructor=self.request.user).annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True), distinct=True),
            published_lessons_count=Count('topics__lessons', filter=Q(topics__lessons__status=Lesson.Status.PUBLISHED), distinct=True),
            published_quizzes_count=Count('topics__lessons__quiz', filter=Q(
                topics__lessons__status=Lesson.Status.PUBLISHED,
                topics__lessons__quiz__status=Quiz.Status.PUBLISHED
            ), distinct=True)
        ).order_by('-created_at')

        total_courses = courses.count()

        paginator = Paginator(courses, 12)
        courses_page = paginator.get_page(self.request.GET.get('page'))

        # Calculate additional metrics for each course on the current page only
        courses_data = []
        for course in courses_page.object_list:
            # Get accurate completed enrollment count
            # (avoiding Django ORM Count annotation issues with multiple filters)
            completed_count = CourseEnrollment.objects.filter(
                course=course,
                is_active=True,
                completed_at__isnull=False
            ).count()

            # Calculate average completion rate
            if course.enrollment_count > 0:
                completion_rate = int((completed_count / course.enrollment_count) * 100)
            else:
                completion_rate = 0

            # Calculate average quiz score for this course
            quiz_attempts = QuizAttempt.objects.filter(
                assignment__quiz__course_lesson__topic__course=course,
                submitted_at__isnull=False
            )
            avg_quiz_score = quiz_attempts.aggregate(Avg('score'))['score__avg'] or 0

            courses_data.append({
                'course': course,
                'enrollment_count': course.enrollment_count,
                'completed_enrollments': completed_count,
                'completion_rate': completion_rate,
                'total_lessons': course.published_lessons_count,
                'total_quizzes': course.published_quizzes_count,
                'avg_quiz_score': round(avg_quiz_score, 1) if avg_quiz_score else 0,
            })

        context['courses_data'] = courses_data
        context['page_obj'] = courses_page
        context['is_paginated'] = courses_page.has_other_pages()

        # Overall statistics
        total_students = CourseEnrollment.objects.filter(
            course__instructor=self.request.user,
            is_active=True
        ).values('student').distinct().count()

        total_enrollments = CourseEnrollment.objects.filter(
            course__instructor=self.request.user,
            is_active=True
        ).count()

        context['total_students'] = total_students
        context['total_enrollments'] = total_enrollments
        context['total_courses'] = total_courses

        return context


class CourseStudentListView(LoginRequiredMixin, InstructorRequiredMixin, DetailView):
    """
    Shows list of all students enrolled in a specific course with their progress.
    """
    model = Course
    template_name = 'courses/instructor/course_students.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        # Get all enrollments with student progress
        enrollments = CourseEnrollment.objects.filter(
            course=course,
            is_active=True
        ).select_related('student', 'child_profile').annotate(
            lessons_completed=Count(
                'lesson_progress__lesson',
                filter=Q(lesson_progress__is_completed=True),
                distinct=True
            ),
            quizzes_passed=Count(
                'quiz_assignments__quiz',
                filter=Q(
                    quiz_assignments__attempts__passed=True,
                    quiz_assignments__quiz__course_lesson__topic__course=course
                ),
                distinct=True
            )
        ).order_by('student__last_name', 'student__first_name')

        # Calculate total lessons and quizzes for the course
        total_lessons = Lesson.objects.filter(
            topic__course=course,
            status=Lesson.Status.PUBLISHED
        ).count()

        total_quizzes = Quiz.objects.filter(
            course_lesson__topic__course=course,
            course_lesson__status=Lesson.Status.PUBLISHED,
            status=Quiz.Status.PUBLISHED
        ).count()

        # Count completed students and total from the full queryset before paginating
        total_enrolled = enrollments.count()
        completed_students = enrollments.filter(completed_at__isnull=False).count()

        paginator = Paginator(enrollments, 25)
        enrollments_page = paginator.get_page(self.request.GET.get('page'))

        # Build student data for the current page only
        students_data = []
        for enrollment in enrollments_page.object_list:
            # Get best quiz scores
            quiz_attempts = QuizAttempt.objects.filter(
                assignment__course_enrollment=enrollment,
                submitted_at__isnull=False
            ).values('assignment__quiz').annotate(
                best_score=Max('score')
            )

            avg_quiz_score = quiz_attempts.aggregate(Avg('best_score'))['best_score__avg'] or 0

            students_data.append({
                'enrollment': enrollment,
                'student': enrollment.student,
                'child_profile': enrollment.child_profile,
                'student_name': enrollment.student_name,
                'progress_percentage': enrollment.progress_percentage,
                'lessons_completed': enrollment.lessons_completed,
                'total_lessons': total_lessons,
                'quizzes_passed': enrollment.quizzes_passed,
                'total_quizzes': total_quizzes,
                'avg_quiz_score': round(avg_quiz_score, 1) if avg_quiz_score else 0,
                'enrolled_at': enrollment.enrolled_at,
                'completed_at': enrollment.completed_at,
            })

        context['students_data'] = students_data
        context['page_obj'] = enrollments_page
        context['is_paginated'] = enrollments_page.has_other_pages()
        context['total_lessons'] = total_lessons
        context['total_quizzes'] = total_quizzes
        context['total_enrolled'] = total_enrolled
        context['completed_students'] = completed_students

        return context


class StudentProgressDetailView(LoginRequiredMixin, InstructorRequiredMixin, TemplateView):
    """
    Detailed view of a specific student's progress in a specific course.
    Shows topics, lessons, completion status, and quiz results.
    """
    template_name = 'courses/instructor/student_progress_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_slug = self.kwargs['course_slug']
        student_id = self.kwargs['student_id']

        # Get course and verify instructor ownership
        course = get_object_or_404(Course, slug=course_slug, instructor=self.request.user)

        # Get student and enrollment
        from django.contrib.auth import get_user_model
        User = get_user_model()
        student = get_object_or_404(User, id=student_id)

        enrollment = get_object_or_404(
            CourseEnrollment,
            course=course,
            student=student,
            is_active=True
        )

        # PERFORMANCE FIX: Prefetch all lesson progress to avoid N+1 queries
        progress_dict = {}
        if enrollment:
            progress_queryset = LessonProgress.objects.filter(
                enrollment=enrollment
            ).select_related('lesson')
            for progress in progress_queryset:
                progress_dict[progress.lesson_id] = progress

        # Get all topics with lessons and progress
        topics_data = []
        for topic in course.topics.order_by('topic_number'):
            lessons_data = []
            published_lessons = topic.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number')

            for lesson in published_lessons:
                # Get lesson progress from prefetched dict (PERFORMANCE FIX)
                lesson_progress = progress_dict.get(lesson.id)
                if lesson_progress:
                    is_completed = lesson_progress.is_completed
                    completed_at = lesson_progress.completed_at
                else:
                    is_completed = False
                    completed_at = None

                # Get quiz data if exists
                quiz_data = None
                if hasattr(lesson, 'quiz') and lesson.quiz.status == Quiz.Status.PUBLISHED:
                    quiz = lesson.quiz

                    # Get all attempts for this quiz
                    attempts = QuizAttempt.objects.filter(
                        assignment__course_enrollment=enrollment,
                        assignment__quiz=quiz,
                        submitted_at__isnull=False
                    ).order_by('-submitted_at')

                    best_attempt = attempts.order_by('-score').first()

                    quiz_data = {
                        'quiz': quiz,
                        'attempts_count': attempts.count(),
                        'best_score': best_attempt.score if best_attempt else 0,
                        'passed': best_attempt.passed if best_attempt else False,
                        'latest_attempt': attempts.first(),
                        'all_attempts': attempts,
                    }

                lessons_data.append({
                    'lesson': lesson,
                    'is_completed': is_completed,
                    'completed_at': completed_at,
                    'quiz_data': quiz_data,
                })

            # Calculate topic completion
            total_lessons_in_topic = len(lessons_data)
            completed_lessons_in_topic = sum(1 for l in lessons_data if l['is_completed'])

            topics_data.append({
                'topic': topic,
                'lessons': lessons_data,
                'total_lessons': total_lessons_in_topic,
                'completed_lessons': completed_lessons_in_topic,
                'progress_percentage': int((completed_lessons_in_topic / total_lessons_in_topic * 100)) if total_lessons_in_topic > 0 else 0,
            })

        context['course'] = course
        context['student'] = student
        context['enrollment'] = enrollment
        context['topics_data'] = topics_data

        return context


class StudentCourseProgressView(LoginRequiredMixin, TemplateView):
    """
    Detailed view of student's own progress in a specific course.
    Similar to instructor view but for the student to see their own progress.
    """
    template_name = 'courses/student/my_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_slug = self.kwargs['slug']

        # Get course
        course = get_object_or_404(Course, slug=course_slug)

        # Get student's enrollment
        enrollment = get_object_or_404(
            CourseEnrollment,
            course=course,
            student=self.request.user,
            is_active=True
        )

        # PERFORMANCE FIX: Prefetch all lesson progress to avoid N+1 queries
        progress_dict = {}
        if enrollment:
            progress_queryset = LessonProgress.objects.filter(
                enrollment=enrollment
            ).select_related('lesson')
            for progress in progress_queryset:
                progress_dict[progress.lesson_id] = progress

        # Get all topics with lessons and progress
        topics_data = []
        for topic in course.topics.order_by('topic_number'):
            lessons_data = []
            published_lessons = topic.lessons.filter(status=Lesson.Status.PUBLISHED).order_by('lesson_number')

            for lesson in published_lessons:
                # Get lesson progress from prefetched dict (PERFORMANCE FIX)
                lesson_progress = progress_dict.get(lesson.id)
                if lesson_progress:
                    is_completed = lesson_progress.is_completed
                    completed_at = lesson_progress.completed_at
                else:
                    is_completed = False
                    completed_at = None

                # Get quiz data if exists
                quiz_data = None
                if hasattr(lesson, 'quiz') and lesson.quiz.status == Quiz.Status.PUBLISHED:
                    quiz = lesson.quiz

                    # Get all attempts for this quiz
                    attempts = QuizAttempt.objects.filter(
                        assignment__course_enrollment=enrollment,
                        assignment__quiz=quiz,
                        submitted_at__isnull=False
                    ).order_by('-submitted_at')

                    best_attempt = attempts.order_by('-score').first()

                    quiz_data = {
                        'quiz': quiz,
                        'attempts_count': attempts.count(),
                        'best_score': best_attempt.score if best_attempt else 0,
                        'passed': best_attempt.passed if best_attempt else False,
                        'latest_attempt': attempts.first(),
                        'all_attempts': attempts[:5],  # Show last 5 attempts
                    }

                lessons_data.append({
                    'lesson': lesson,
                    'is_completed': is_completed,
                    'completed_at': completed_at,
                    'quiz_data': quiz_data,
                })

            # Calculate topic completion
            total_lessons_in_topic = len(lessons_data)
            completed_lessons_in_topic = sum(1 for l in lessons_data if l['is_completed'])

            topics_data.append({
                'topic': topic,
                'lessons': lessons_data,
                'total_lessons': total_lessons_in_topic,
                'completed_lessons': completed_lessons_in_topic,
                'progress_percentage': int((completed_lessons_in_topic / total_lessons_in_topic * 100)) if total_lessons_in_topic > 0 else 0,
            })

        # Calculate overall quiz performance
        all_quiz_attempts = QuizAttempt.objects.filter(
            assignment__course_enrollment=enrollment,
            submitted_at__isnull=False
        ).values('assignment__quiz').annotate(
            best_score=Max('score')
        )

        avg_quiz_score = all_quiz_attempts.aggregate(Avg('best_score'))['best_score__avg'] or 0

        context['course'] = course
        context['enrollment'] = enrollment
        context['topics_data'] = topics_data
        context['avg_quiz_score'] = round(avg_quiz_score, 1) if avg_quiz_score else 0

        return context


# ============================================================================
# MESSAGING VIEWS
# ============================================================================

class MessageInboxView(LoginRequiredMixin, TemplateView):
    """
    Inbox showing all messages for the current user (both sent and received).
    """
    template_name = 'courses/messages/inbox.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Q, Exists, OuterRef

        # Get all root messages where user is involved
        root_messages = CourseMessage.objects.filter(
            parent_message__isnull=True
        ).select_related('sender', 'recipient', 'course', 'lesson')

        # For "Received" tab: show threads where user either:
        # 1. Is the recipient of the root message, OR
        # 2. Sent the root message but has received replies
        has_replies_for_user = CourseMessage.objects.filter(
            parent_message=OuterRef('pk'),
            recipient=self.request.user
        )

        received_messages = root_messages.filter(
            Q(recipient=self.request.user) |  # User received the original message
            Q(sender=self.request.user, replies__recipient=self.request.user)  # User sent but got replies
        ).distinct().order_by('-sent_at')

        # For "Sent" tab: show threads where user sent the root message
        sent_messages = root_messages.filter(
            sender=self.request.user
        ).order_by('-sent_at')

        # Count unread messages (any message where user is recipient and not read)
        unread_count = CourseMessage.objects.filter(
            recipient=self.request.user,
            read_at__isnull=True
        ).count()

        context['received_messages'] = received_messages
        context['sent_messages'] = sent_messages
        context['unread_count'] = unread_count

        return context


class MessageComposeView(LoginRequiredMixin, CreateView):
    """
    Compose a new message to the instructor about a lesson.
    """
    model = CourseMessage
    form_class = CourseMessageForm
    template_name = 'courses/messages/compose.html'

    def dispatch(self, request, *args, **kwargs):
        # Get the lesson
        self.lesson = get_object_or_404(Lesson, id=self.kwargs['lesson_id'])
        self.course = self.lesson.topic.course

        # Check enrollment (or if user is the instructor)
        is_owner = self.course.is_owned_by(request.user)

        if not is_owner:
            self.enrollment = get_object_or_404(
                CourseEnrollment,
                course=self.course,
                student=request.user,
                is_active=True
            )
        else:
            # Instructors don't need to message themselves
            messages.warning(request, 'As the instructor, you cannot send messages to yourself.')
            return redirect('courses:view_lesson', lesson_id=self.lesson.id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson'] = self.lesson
        context['course'] = self.course
        context['topic'] = self.lesson.topic

        # Auto-generate subject
        subject = f"{self.course.title} > Topic {self.lesson.topic.topic_number}: {self.lesson.topic.topic_title} > Lesson {self.lesson.lesson_number}: {self.lesson.lesson_title}"
        context['auto_subject'] = subject

        return context

    def form_valid(self, form):
        # Set the fields that aren't in the form
        form.instance.sender = self.request.user
        form.instance.recipient = self.course.instructor
        form.instance.course = self.course
        form.instance.lesson = self.lesson

        # Generate subject
        form.instance.subject = f"{self.course.title} > Topic {self.lesson.topic.topic_number}: {self.lesson.topic.topic_title} > Lesson {self.lesson.lesson_number}: {self.lesson.lesson_title}"

        messages.success(self.request, 'Your message has been sent to the instructor.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:view_lesson', kwargs={'lesson_id': self.lesson.id})


class MessageThreadView(LoginRequiredMixin, DetailView):
    """
    View a message thread (original message + all replies).
    """
    model = CourseMessage
    template_name = 'courses/messages/thread.html'
    context_object_name = 'message'
    pk_url_kwarg = 'message_id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        # If this is a reply, get the root message
        if obj.parent_message:
            return obj.parent_message

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mark as read if user is the recipient and message is unread
        if self.object.recipient == self.request.user and not self.object.is_read:
            self.object.mark_as_read()

        # Get all replies
        replies = self.object.replies.select_related('sender').order_by('sent_at')

        # Mark unread replies as read
        for reply in replies:
            if reply.recipient == self.request.user and not reply.is_read:
                reply.mark_as_read()

        context['replies'] = replies
        context['reply_form'] = MessageReplyForm()

        # Determine if user can reply
        context['can_reply'] = (
            self.request.user == self.object.sender or
            self.request.user == self.object.recipient
        )

        return context

    def post(self, request, *args, **kwargs):
        """Handle reply submission"""
        self.object = self.get_object()
        form = MessageReplyForm(request.POST)

        if form.is_valid():
            # Create reply
            reply = CourseMessage.objects.create(
                sender=request.user,
                recipient=self.object.sender if request.user == self.object.recipient else self.object.recipient,
                course=self.object.course,
                lesson=self.object.lesson,
                subject=f"Re: {self.object.subject}",
                body=form.cleaned_data['body'],
                category=self.object.category,
                parent_message=self.object
            )

            messages.success(request, 'Your reply has been sent.')
            return redirect('courses:message_thread', message_id=self.object.id)

        # If form invalid, re-render with errors
        context = self.get_context_data()
        context['reply_form'] = form
        return self.render_to_response(context)


# ============================================================================
# CERTIFICATE VIEWS
# ============================================================================

class CertificateClaimView(LoginRequiredMixin, View):
    """
    Handle manual certificate claiming when student completes course.
    """

    def post(self, request, slug):
        from .models import CourseCertificate

        course = get_object_or_404(Course, slug=slug)
        enrollment = get_object_or_404(
            CourseEnrollment,
            course=course,
            student=request.user,
            is_active=True
        )

        # Check if already has certificate
        if hasattr(enrollment, 'certificate'):
            messages.info(request, 'You have already claimed your certificate for this course.')
            return redirect('courses:certificate_view', certificate_id=enrollment.certificate.id)

        # Verify 100% completion
        if enrollment.progress_percentage < 100:
            messages.error(request, f'You must complete 100% of the course to claim your certificate. Current progress: {enrollment.progress_percentage}%')
            return redirect('courses:my_progress', slug=course.slug)

        # Create certificate
        certificate = CourseCertificate.objects.create(enrollment=enrollment)

        messages.success(request, 'Congratulations! Your certificate has been generated.')
        return redirect('courses:certificate_view', certificate_id=certificate.id)


class CertificateViewView(LoginRequiredMixin, DetailView):
    """
    Display certificate on screen (HTML version).
    """
    model = None  # We'll get the model dynamically
    template_name = 'courses/certificates/certificate_view.html'
    context_object_name = 'certificate'
    pk_url_kwarg = 'certificate_id'

    def get_object(self):
        from .models import CourseCertificate
        certificate_id = self.kwargs.get('certificate_id')
        certificate = get_object_or_404(CourseCertificate, id=certificate_id)

        # Verify access (student who earned it or course instructor)
        is_owner = certificate.enrollment.student == self.request.user
        is_instructor = certificate.enrollment.course.instructor == self.request.user

        if not (is_owner or is_instructor):
            messages.error(self.request, 'You do not have permission to view this certificate.')
            return redirect('courses:student_dashboard')

        return certificate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.object

        context['student_name'] = certificate.enrollment.student.get_full_name() or certificate.enrollment.student.username
        context['course_title'] = certificate.enrollment.course.title
        context['certificate_number'] = certificate.certificate_number
        context['issue_date'] = certificate.issued_at.strftime('%B %d, %Y')
        context['platform_name'] = 'RECORDER-ED Learning Platform'

        return context


class CertificateDownloadView(LoginRequiredMixin, View):
    """
    Generate and download certificate as PDF.
    """

    def get(self, request, certificate_id):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        from weasyprint import HTML
        from .models import CourseCertificate
        import tempfile

        certificate = get_object_or_404(CourseCertificate, id=certificate_id)

        # Verify access
        is_owner = certificate.enrollment.student == request.user
        is_instructor = certificate.enrollment.course.instructor == request.user

        if not (is_owner or is_instructor):
            messages.error(request, 'You do not have permission to download this certificate.')
            return redirect('courses:student_dashboard')

        # Prepare context for template
        context = {
            'student_name': certificate.enrollment.student.get_full_name() or certificate.enrollment.student.username,
            'course_title': certificate.enrollment.course.title,
            'certificate_number': certificate.certificate_number,
            'issue_date': certificate.issued_at.strftime('%B %d, %Y'),
            'platform_name': 'RECORDER-ED Learning Platform',
        }

        # Render HTML template
        html_string = render_to_string('courses/certificates/certificate_template.html', context)

        # Generate PDF
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()

        # Return PDF response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f"Certificate_{certificate.certificate_number}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


class CertificateGalleryView(LoginRequiredMixin, TemplateView):
    """
    Display all certificates earned by the current user.
    """
    template_name = 'courses/certificates/certificate_gallery.html'

    def get_context_data(self, **kwargs):
        from .models import CourseCertificate
        context = super().get_context_data(**kwargs)

        # Get all certificates for current user
        certificates = CourseCertificate.objects.filter(
            enrollment__student=self.request.user
        ).select_related('enrollment__course').order_by('-issued_at')

        context['certificates'] = certificates
        context['total_certificates'] = certificates.count()

        return context


class CertificateVerifyView(TemplateView):
    """
    Public certificate verification page.
    Anyone can verify a certificate by its number or ID.
    """
    template_name = 'courses/certificates/certificate_verify.html'

    def get_context_data(self, **kwargs):
        from .models import CourseCertificate
        context = super().get_context_data(**kwargs)

        # Check if verification code provided
        verify_code = self.request.GET.get('code', '').strip()

        if verify_code:
            try:
                # Try to find by certificate number or UUID
                try:
                    certificate = CourseCertificate.objects.get(certificate_number=verify_code)
                except CourseCertificate.DoesNotExist:
                    # Try UUID
                    certificate = CourseCertificate.objects.get(id=verify_code)

                context['certificate'] = certificate
                context['student_name'] = certificate.enrollment.student.get_full_name() or certificate.enrollment.student.username
                context['course_title'] = certificate.enrollment.course.title
                context['verified'] = True

            except CourseCertificate.DoesNotExist:
                context['verified'] = False
                context['error_message'] = 'Certificate not found. Please check the code and try again.'
            except Exception as e:
                context['verified'] = False
                context['error_message'] = 'Invalid certificate code format.'

        return context


# ============================================================================
# COURSE CANCELLATION VIEWS
# ============================================================================

class CourseCancellationRequestView(LoginRequiredMixin, View):
    """
    View for students to request course cancellation and refund.
    Handles both GET (show form) and POST (submit request).
    """

    def get(self, request, enrollment_id):
        """Display cancellation request form"""
        from .models import CourseEnrollment, CourseCancellationRequest
        from datetime import timedelta
        from django.utils import timezone

        try:
            enrollment = CourseEnrollment.objects.select_related('course').get(
                id=enrollment_id,
                student=request.user,
                is_active=True
            )
        except CourseEnrollment.DoesNotExist:
            messages.error(request, 'Enrollment not found or you do not have permission to cancel it.')
            return redirect('courses:dashboard')

        # Check if there's already a pending cancellation request
        existing_request = CourseCancellationRequest.objects.filter(
            enrollment=enrollment,
            status=CourseCancellationRequest.PENDING
        ).first()

        if existing_request:
            messages.warning(request, 'You already have a pending cancellation request for this course.')
            return redirect('courses:cancellation_status', request_id=existing_request.id)

        # Calculate eligibility
        days_since_enrollment = (timezone.now() - enrollment.enrolled_at).days
        within_trial = days_since_enrollment <= 7
        progress = enrollment.progress_percentage

        context = {
            'enrollment': enrollment,
            'days_since_enrollment': days_since_enrollment,
            'within_trial': within_trial,
            'eligible_for_refund': within_trial,
            'refund_amount': enrollment.payment_amount if within_trial else 0,
            'progress': progress,
            'trial_period_days': 7,
        }

        return render(request, 'courses/cancellation_request.html', context)

    def post(self, request, enrollment_id):
        """Submit cancellation request"""
        from .models import CourseEnrollment, CourseCancellationRequest

        try:
            enrollment = CourseEnrollment.objects.select_related('course').get(
                id=enrollment_id,
                student=request.user,
                is_active=True
            )
        except CourseEnrollment.DoesNotExist:
            messages.error(request, 'Enrollment not found or you do not have permission to cancel it.')
            return redirect('courses:dashboard')

        # Check if there's already a pending cancellation request
        existing_request = CourseCancellationRequest.objects.filter(
            enrollment=enrollment,
            status=CourseCancellationRequest.PENDING
        ).first()

        if existing_request:
            messages.warning(request, 'You already have a pending cancellation request for this course.')
            return redirect('courses:cancellation_status', request_id=existing_request.id)

        # Get reason from form
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for cancellation.')
            return redirect('courses:request_cancellation', enrollment_id=enrollment_id)

        # Create cancellation request
        cancellation = CourseCancellationRequest.objects.create(
            enrollment=enrollment,
            student=request.user,
            reason=reason
        )

        # Calculate eligibility
        cancellation.calculate_refund_eligibility()
        cancellation.save()

        # If eligible for refund, process it automatically
        if cancellation.is_eligible_for_refund:
            from apps.payments.models import StripePayment
            from apps.payments.stripe_service import create_refund
            import logging

            logger = logging.getLogger(__name__)

            try:
                # Get StripePayment record
                stripe_payment = StripePayment.objects.get(
                    stripe_payment_intent_id=enrollment.stripe_payment_intent_id
                )

                # Create Stripe refund
                refund_metadata = {
                    'cancellation_request_id': str(cancellation.id),
                    'enrollment_id': str(enrollment.id),
                    'course_id': str(enrollment.course.id),
                    'student_id': str(request.user.id),
                    'refund_type': 'course_cancellation_automatic',
                }

                refund = create_refund(
                    payment_intent_id=stripe_payment.stripe_payment_intent_id,
                    amount=cancellation.refund_amount,
                    reason='requested_by_customer',
                    metadata=refund_metadata
                )

                # Mark as approved and completed
                cancellation.status = CourseCancellationRequest.COMPLETED
                cancellation.reviewed_by = request.user  # Self-approved (automatic)
                cancellation.reviewed_at = timezone.now()
                cancellation.refund_processed_at = timezone.now()
                cancellation.admin_notes = 'Automatic refund - within 7-day trial period'
                cancellation.save()

                # Deactivate enrollment
                enrollment.is_active = False
                enrollment.save()

                # Update course enrollment count
                course = enrollment.course
                course.total_enrollments = CourseEnrollment.objects.filter(
                    course=course,
                    is_active=True
                ).count()
                course.save(update_fields=['total_enrollments'])

                messages.success(
                    request,
                    f'Your course has been cancelled and a full refund of £{cancellation.refund_amount} has been processed. '
                    f'The refund will appear in your payment method within 5-10 business days.'
                )

            except StripePayment.DoesNotExist:
                logger.error(f"StripePayment not found for enrollment {enrollment.id}")
                # Keep as pending for manual processing
                messages.warning(
                    request,
                    'Your cancellation request has been submitted. Due to a payment record issue, '
                    'your refund will be processed manually within 24 hours.'
                )
            except Exception as e:
                logger.error(f"Error processing automatic refund for cancellation {cancellation.id}: {e}")
                # Keep as pending for manual processing
                messages.warning(
                    request,
                    'Your cancellation request has been submitted. Your refund will be processed shortly.'
                )
        else:
            # Not eligible for refund
            cancellation.status = CourseCancellationRequest.COMPLETED
            cancellation.reviewed_at = timezone.now()
            cancellation.admin_notes = 'Outside 7-day trial period - no refund applicable'
            cancellation.save()

            # Deactivate enrollment
            enrollment.is_active = False
            enrollment.save()

            # Update course enrollment count
            course = enrollment.course
            course.total_enrollments = CourseEnrollment.objects.filter(
                course=course,
                is_active=True
            ).count()
            course.save(update_fields=['total_enrollments'])

            messages.info(
                request,
                'Your course enrollment has been cancelled. This cancellation is outside the 7-day trial period, '
                'so no refund is applicable.'
            )

        return redirect('courses:cancellation_status', request_id=cancellation.id)


class CourseCancellationStatusView(LoginRequiredMixin, DetailView):
    """View for students to check status of their cancellation request"""
    model = CourseCancellationRequest
    template_name = 'courses/cancellation_status.html'
    context_object_name = 'cancellation'
    pk_url_kwarg = 'request_id'

    def get_queryset(self):
        """Ensure students can only view their own cancellation requests"""
        from .models import CourseCancellationRequest
        return CourseCancellationRequest.objects.filter(
            student=self.request.user
        ).select_related('enrollment', 'enrollment__course', 'reviewed_by')


class AdminCourseCancellationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View to list cancellation requests - for staff or instructors"""
    model = CourseCancellationRequest
    template_name = 'courses/admin_cancellation_list.html'
    context_object_name = 'cancellations'
    paginate_by = 20

    def test_func(self):
        """Staff or instructors can access"""
        return self.request.user.is_staff or self.request.user.profile.is_teacher

    def get_queryset(self):
        """Get cancellations - all for staff, own courses for instructors"""
        from .models import CourseCancellationRequest
        status_filter = self.request.GET.get('status', CourseCancellationRequest.PENDING)

        qs = CourseCancellationRequest.objects.filter(status=status_filter)

        # If instructor (not staff), only show their own courses
        if not self.request.user.is_staff and self.request.user.profile.is_teacher:
            qs = qs.filter(enrollment__course__instructor=self.request.user)

        return qs.select_related(
            'student', 'enrollment', 'enrollment__course'
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', CourseCancellationRequest.PENDING)
        return context


class AdminCourseCancellationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to review and process a cancellation request - for staff or instructors"""
    model = CourseCancellationRequest
    template_name = 'courses/admin_cancellation_detail.html'
    context_object_name = 'cancellation'
    pk_url_kwarg = 'request_id'

    def test_func(self):
        """Staff or course instructor can access"""
        from .models import CourseCancellationRequest
        if self.request.user.is_staff:
            return True
        if self.request.user.profile.is_teacher:
            # Check if this cancellation is for their course
            request_id = self.kwargs.get('request_id')
            return CourseCancellationRequest.objects.filter(
                id=request_id,
                enrollment__course__instructor=self.request.user
            ).exists()
        return False

    def get_queryset(self):
        from .models import CourseCancellationRequest
        qs = CourseCancellationRequest.objects.select_related(
            'student', 'enrollment', 'enrollment__course', 'reviewed_by'
        )
        # If instructor (not staff), only show their own courses
        if not self.request.user.is_staff and self.request.user.profile.is_teacher:
            qs = qs.filter(enrollment__course__instructor=self.request.user)
        return qs


class AdminApproveCancellationView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to approve a cancellation and process refund - for staff or instructors"""

    def test_func(self):
        """Staff or course instructor can access"""
        from .models import CourseCancellationRequest
        if self.request.user.is_staff:
            return True
        if self.request.user.profile.is_teacher:
            # Check if this cancellation is for their course
            request_id = self.kwargs.get('request_id')
            return CourseCancellationRequest.objects.filter(
                id=request_id,
                enrollment__course__instructor=self.request.user
            ).exists()
        return False

    def post(self, request, request_id):
        """Approve cancellation and process Stripe refund"""
        from .models import CourseCancellationRequest
        from apps.payments.models import StripePayment
        from apps.payments.stripe_service import create_refund
        import logging

        logger = logging.getLogger(__name__)

        try:
            cancellation = CourseCancellationRequest.objects.select_related(
                'enrollment', 'enrollment__course'
            ).get(id=request_id)
        except CourseCancellationRequest.DoesNotExist:
            messages.error(request, 'Cancellation request not found.')
            return redirect('courses:admin_cancellation_list')

        if cancellation.status != CourseCancellationRequest.PENDING:
            messages.warning(request, f'This request has already been {cancellation.get_status_display().lower()}.')
            return redirect('courses:admin_cancellation_detail', request_id=request_id)

        admin_notes = request.POST.get('admin_notes', '')

        # Approve the request
        cancellation.approve(request.user, admin_notes)

        # Process refund if eligible
        if cancellation.is_eligible_for_refund and cancellation.refund_amount:
            enrollment = cancellation.enrollment

            try:
                # Get StripePayment record
                stripe_payment = StripePayment.objects.get(
                    stripe_payment_intent_id=enrollment.stripe_payment_intent_id
                )

                # Create Stripe refund
                refund_metadata = {
                    'cancellation_request_id': str(cancellation.id),
                    'enrollment_id': str(enrollment.id),
                    'course_id': str(enrollment.course.id),
                    'student_id': str(cancellation.student.id),
                    'refund_type': 'course_cancellation',
                }

                refund = create_refund(
                    payment_intent_id=stripe_payment.stripe_payment_intent_id,
                    amount=cancellation.refund_amount,
                    reason='requested_by_customer',
                    metadata=refund_metadata
                )

                # Mark refund as processed
                cancellation.mark_refund_processed()

                # Deactivate enrollment
                enrollment.is_active = False
                enrollment.save()

                messages.success(
                    request,
                    f'Cancellation approved and refund of £{cancellation.refund_amount} processed successfully.'
                )

            except StripePayment.DoesNotExist:
                logger.error(f"StripePayment not found for enrollment {enrollment.id}")
                messages.warning(
                    request,
                    'Cancellation approved but payment record not found. Please process refund manually in Stripe.'
                )
            except Exception as e:
                logger.error(f"Error processing refund for cancellation {cancellation.id}: {e}")
                messages.error(
                    request,
                    f'Cancellation approved but refund failed: {str(e)}. Please process manually in Stripe.'
                )
        else:
            # No refund needed
            enrollment = cancellation.enrollment
            enrollment.is_active = False
            enrollment.save()
            messages.success(request, 'Cancellation approved (no refund applicable).')

        return redirect('courses:admin_cancellation_detail', request_id=request_id)


class AdminRejectCancellationView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admin view to reject a cancellation request"""

    def test_func(self):
        """Only staff can access"""
        return self.request.user.is_staff

    def post(self, request, request_id):
        """Reject cancellation"""
        from .models import CourseCancellationRequest

        try:
            cancellation = CourseCancellationRequest.objects.get(id=request_id)
        except CourseCancellationRequest.DoesNotExist:
            messages.error(request, 'Cancellation request not found.')
            return redirect('courses:admin_cancellation_list')

        if cancellation.status != CourseCancellationRequest.PENDING:
            messages.warning(request, f'This request has already been {cancellation.get_status_display().lower()}.')
            return redirect('courses:admin_cancellation_detail', request_id=request_id)

        admin_notes = request.POST.get('admin_notes', '')
        if not admin_notes:
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('courses:admin_cancellation_detail', request_id=request_id)

        # Reject the request
        cancellation.reject(request.user, admin_notes)

        messages.success(request, 'Cancellation request rejected.')
        return redirect('courses:admin_cancellation_detail', request_id=request_id)


# ============================================================================
# COURSE TERMS & CONDITIONS VIEW
# ============================================================================

class CourseTermsView(TemplateView):
    """Public view of current Course Terms and Conditions"""
    template_name = 'courses/terms_and_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import CourseTermsAndConditions
        current_terms = CourseTermsAndConditions.objects.filter(is_current=True).first()
        context['terms'] = current_terms
        return context
