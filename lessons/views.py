from django.http import Http404, HttpResponse, JsonResponse
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views import View
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied

from apps.private_teaching.models import LessonRequest

from .models import Lesson, LessonOrder
from .forms import LessonForm, DocumentFormSet, LessonUrlsFormSet, LessonAssignmentFormSet


class LessonAccessBlocked(Exception):
    """Raised when a student cannot access a lesson but should see a friendly message."""
    def __init__(self, message, lesson):
        self.message = message
        self.lesson = lesson


class CalendarView(LoginRequiredMixin, TemplateView):
    """Enhanced calendar view that shows lessons and integrates with lesson creation"""
    template_name = 'lessons/calendar.html'
    login_url = 'private_teaching:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all lessons for the calendar (filter by user permissions)
        # Show all lessons regardless of status, but exclude soft-deleted ones
        lessons = Lesson.objects.filter(
            is_deleted=False,
            lesson_request__isnull=False
        ).select_related('subject', 'student', 'teacher', 'lesson_request')

        # Filter lessons based on user permissions
        if hasattr(self.request.user, 'profile'):
            if self.request.user.profile.is_teacher:
                # Teachers see their lessons
                lessons = lessons.filter(teacher=self.request.user)
            elif self.request.user.profile.is_student or getattr(self.request.user.profile, 'is_guardian', False):
                # Students and guardians see their lessons
                lessons = lessons.filter(student=self.request.user)
            else:
                lessons = lessons.none()
        else:
            lessons = lessons.none()

        # Convert lessons to calendar events
        calendar_events = []
        for lesson in lessons:
            event = {
                'id': str(lesson.id),
                'title': f"{lesson.subject.subject}",
                'start': f"{lesson.lesson_date}T{lesson.lesson_time}",
                'color': lesson.calendar_color,
                'extendedProps': {
                    'subject': lesson.subject.subject,
                    'student': lesson.student.get_full_name() if lesson.student else 'Unknown',
                    'teacher': lesson.teacher.get_full_name() if lesson.teacher else 'Unknown',
                    'duration': lesson.duration_in_minutes,
                    'location': lesson.location,
                    'approvedStatus': lesson.approved_status,
                    'paymentStatus': lesson.payment_status,
                    'status': lesson.status,
                    'fee': str(lesson.fee) if lesson.fee else 'Not set',
                    'lessonId': str(lesson.id),
                }
            }
            calendar_events.append(event)

        context['calendar_events'] = calendar_events

        # Add user role information for client-side routing
        context['is_teacher'] = (hasattr(self.request.user, 'profile') and
                               self.request.user.profile.is_teacher)
        context['is_student'] = (hasattr(self.request.user, 'profile') and
                               self.request.user.profile.is_student)

        return context


class LessonInline:
    """Mixin for handling inline formsets in lesson forms"""
    form_class = LessonForm
    model = Lesson

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)

        named_formsets = self.get_named_formsets()

        if not all((x.is_valid() for x in named_formsets.values())):
            # Debug: Log which formsets are invalid
            for name, formset in named_formsets.items():
                if not formset.is_valid():
                    logger.error(f"Formset '{name}' is invalid:")
                    logger.error(f"  Errors: {formset.errors}")
                    logger.error(f"  Non-form errors: {formset.non_form_errors()}")
                    messages.error(self.request, f"Error in {name}: {formset.errors}")
            return self.render_to_response(self.get_context_data(form=form))

        # Store the old status before saving
        old_status = None
        if self.object and self.object.pk:
            old_lesson = Lesson.objects.get(pk=self.object.pk)
            old_status = old_lesson.status

        self.object = form.save()

        for name, formset in named_formsets.items():
            formset_save_func = getattr(self, 'formset_{0}_valid'.format(name), None)
            if formset_save_func is not None:
                formset_save_func(formset)
            else:
                saved_instances = formset.save()
                # Debug: Log what was saved
                logger.info(f"Formset '{name}' saved {len(saved_instances)} instances")
                for instance in saved_instances:
                    logger.info(f"  - Saved: {instance}")

        # Send email if lesson was just published (Draft -> Assigned)
        new_status = self.object.status
        if old_status == Lesson.Status.DRAFT and new_status == Lesson.Status.ASSIGNED:
            from lessons.notifications import LessonNotificationService
            teacher_name = self.request.user.get_full_name() or self.request.user.username
            LessonNotificationService.send_lesson_assigned_notification(
                self.object,
                teacher_name
            )

        messages.success(self.request, 'Lesson updated successfully!')
        return redirect('lessons:lesson_update', pk=self.object.pk)

    def formset_documents_valid(self, formset):
        documents = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for document in documents:
            document.lesson = self.object
            document.save()

    def formset_lesson_attached_urls_valid(self, formset):
        urls = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for url in urls:
            url.lesson = self.object
            url.save()


class LessonDetailView(LoginRequiredMixin, DetailView):
    """Display lesson details with all content"""
    model = Lesson
    template_name = 'lessons/lesson_detail.html'
    context_object_name = 'lesson'
    login_url = 'private_teaching:login'

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except LessonAccessBlocked as e:
            return render(request, 'lessons/lesson_access_blocked.html', {
                'message': e.message,
                'lesson': e.lesson,
            })

    def get_object(self):
        lesson = get_object_or_404(
            Lesson.objects.select_related(
                'lesson_request',
                'lesson_request__child_profile',
                'lesson_request__student',
                'subject',
                'subject__teacher',
                'student'
            ).prefetch_related(
                'lesson_assignments',
                'lesson_assignments__assignment'
            ),
            pk=self.kwargs['pk']
        )
        # Check permissions - teacher or student can view
        user_can_view = False
        error_message = "You don't have permission to view this lesson."

        if hasattr(self.request.user, 'profile'):
            if self.request.user.profile.is_teacher:
                # Teacher can view lessons for their subjects if approved
                if lesson.teacher == self.request.user:
                    if lesson.approved_status == Lesson.ApprovalStatus.ACCEPTED:
                        user_can_view = True
                    else:
                        error_message = "This lesson has not been approved yet."
            elif self.request.user.profile.is_student or getattr(self.request.user.profile, 'is_guardian', False):
                # Students and guardians can only view their own lessons if approved, paid, and assigned
                if lesson.student == self.request.user:
                    if lesson.approved_status != Lesson.ApprovalStatus.ACCEPTED:
                        error_message = "This lesson is still awaiting teacher approval."
                    elif lesson.payment_status != 'completed':
                        raise LessonAccessBlocked(
                            "Please submit payment for this lesson.",
                            lesson,
                        )
                    elif lesson.status != Lesson.Status.ASSIGNED:
                        error_message = "Your teacher is still preparing the lesson content. You will be notified when it's ready."
                    else:
                        user_can_view = True

        if not user_can_view:
            raise PermissionDenied(error_message)
        return lesson


class LessonUpdateView(LoginRequiredMixin, LessonInline, UpdateView):
    """Update lesson content and details - teacher only"""
    template_name = "lessons/lesson_update.html"
    login_url = 'private_teaching:login'

    def get_object(self):
        lesson = get_object_or_404(
            Lesson.objects.select_related(
                'lesson_request',
                'lesson_request__child_profile',
                'lesson_request__student',
                'subject',
                'subject__teacher',
                'student'
            ),
            pk=self.kwargs['pk']
        )
        # Only teacher can edit lessons
        user_can_edit = False
        
        if hasattr(self.request.user, 'profile'):
            if self.request.user.profile.is_teacher:
                user_can_edit = lesson.subject.teacher == self.request.user
        
        if not user_can_edit:
            raise PermissionDenied()
        return lesson

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['named_formsets'] = self.get_named_formsets()

        # Add available assignments for dropdown
        from assignments.models import Assignment
        ctx['available_assignments'] = Assignment.objects.filter(
            created_by=self.request.user,
            is_active=True
        ).order_by('title')

        return ctx

    def get_named_formsets(self):
        return {
            'documents': DocumentFormSet(
                self.request.POST or None,
                self.request.FILES or None,
                instance=self.object,
                prefix='documents'
            ),
            'lesson_attached_urls': LessonUrlsFormSet(
                self.request.POST or None,
                self.request.FILES or None,
                instance=self.object,
                prefix='lesson_attached_urls'
            ),
            'assignments': LessonAssignmentFormSet(
                self.request.POST or None,
                instance=self.object,
                prefix='assignments'
            ),
        }

    def get_success_url(self):
        """Redirect back to the edit page after successful save"""
        from django.urls import reverse
        return reverse('lessons:lesson_update', kwargs={'pk': self.object.pk})


class LessonListView(LoginRequiredMixin, ListView):
    """List all lessons for the current user"""
    model = Lesson
    template_name = 'lessons/lesson_list.html'
    context_object_name = 'lessons'
    paginate_by = 20
    login_url = 'private_teaching:login'

    def get_queryset(self):
        if not hasattr(self.request.user, 'profile'):
            return Lesson.objects.none()

        if self.request.user.profile.is_teacher:
            # Teachers see their lessons
            return Lesson.objects.filter(
                teacher=self.request.user,
                is_deleted=False
            ).select_related('subject', 'student', 'lesson_request')
        elif self.request.user.profile.is_student or getattr(self.request.user.profile, 'is_guardian', False):
            # Students and guardians see their lessons
            return Lesson.objects.filter(
                student=self.request.user,
                is_deleted=False
            ).select_related('subject', 'teacher', 'lesson_request')
        else:
            return Lesson.objects.none()


class PrivateLessonAIAssistView(LoginRequiredMixin, View):
    login_url = 'private_teaching:login'

    def post(self, request, *args, **kwargs):
        from anthropic import Anthropic

        ai_mode = request.POST.get('mode', '').strip()
        description = request.POST.get('description', '').strip()
        if not description and ai_mode != 'reformat':
            return JsonResponse({'error': 'No description provided.'}, status=400)

        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            return JsonResponse({'error': 'AI assistant is not configured.'}, status=503)

        lesson_id = request.POST.get('lesson_id', '').strip()
        if not lesson_id:
            return JsonResponse({'error': 'Lesson ID required.'}, status=400)

        lesson = get_object_or_404(Lesson, pk=lesson_id)

        if not (hasattr(request.user, 'profile') and request.user.profile.is_teacher
                and lesson.subject.teacher == request.user):
            return JsonResponse({'error': 'Permission denied.'}, status=403)

        if ai_mode == 'reformat' and not lesson.lesson_content:
            return JsonResponse({'error': 'No existing content to reformat.'}, status=400)

        # Build context for the prompt
        subject_name = lesson.subject.subject if lesson.subject else 'recorder'
        student_name = None
        if lesson.lesson_request and lesson.lesson_request.child_profile:
            student_name = lesson.lesson_request.child_profile.full_name
        if not student_name:
            student_name = lesson.student.get_full_name() if lesson.student else 'the student'
        lesson_date = lesson.lesson_date.strftime('%B %-d, %Y') if lesson.lesson_date else ''

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
            prompt = f"""You are reformatting an existing private recorder lesson to match the platform's visual style guide.

EXISTING LESSON CONTENT (full HTML):
{lesson.lesson_content}

YOUR TASK: Reformat the HTML using the style guide below. Apply the exact inline styles specified to every element.

STRICT RULES — YOU MUST FOLLOW THESE EXACTLY:
- Do NOT change any words, sentences, paragraphs, or educational content
- Do NOT add, remove, or reorder any sections
- ONLY replace the HTML markup and inline styles to match the style guide
- PRESERVE MEDIA VERBATIM: copy every <img>, <figure>, <svg>, <picture>, <audio>, <video>, and <source> element exactly character-for-character
- The IMAGE/NOTATION PLACEHOLDERS shown in the style guide are ONLY for use when drafting NEW lessons — do NOT apply them to existing images or figures
{LESSON_STYLE_GUIDE}
Use the generate_lesson_content tool to return your response."""

        elif lesson.lesson_content:
            prompt = f"""You are an expert recorder music teacher and editor. You are revising an existing private lesson.

Subject: {subject_name}
Student: {student_name}
Lesson date: {lesson_date}

EXISTING LESSON CONTENT (full HTML):
{lesson.lesson_content}

TEACHER'S REVISION INSTRUCTIONS:
{description}

YOUR TASK: Revise the lesson content according to the teacher's instructions above.

CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY:
- Preserve the existing text, structure, and HTML of sections you are NOT changing
- For any new sections or content you add, apply the style guide below precisely
- Do NOT reformat or restyle existing content that the teacher did not ask you to change
- Return the complete revised HTML — not a summary or partial content
{LESSON_STYLE_GUIDE}
Use the generate_lesson_content tool to return your response."""

        else:
            prompt = f"""You are an expert recorder music teacher creating new content for a private lesson.

Subject: {subject_name}
Student: {student_name}
Lesson date: {lesson_date}

TEACHER'S NOTES FOR THIS LESSON:
{description}

YOUR TASK: Draft complete lesson content based on the teacher's notes. Apply the style guide below to every element — use the exact inline styles specified, no exceptions.

Write 300–600 words covering: learning objective, explanation of the concept, practical exercises, and a summary. Tailor language and complexity to the student.
{LESSON_STYLE_GUIDE}
Use the generate_lesson_content tool to return your response."""

        tools = [{
            'name': 'generate_lesson_content',
            'description': 'Generate lesson content for the teacher to review before applying.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'content': {
                        'type': 'string',
                        'description': 'Complete lesson content as valid HTML with inline styles per the style guide.',
                    },
                    'summary': {
                        'type': 'string',
                        'description': 'One sentence describing what this lesson covers.',
                    },
                },
                'required': ['content', 'summary'],
            },
        }]

        if ai_mode == 'reformat' or lesson.lesson_content:
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
                tool_choice={'type': 'tool', 'name': 'generate_lesson_content'},
                messages=[{'role': 'user', 'content': prompt}],
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error('Private lesson AI assist failed: %s', e)
            return JsonResponse({'error': 'AI service unavailable. Please try again later.'}, status=503)

        if message.stop_reason == 'max_tokens':
            return JsonResponse({'error': 'The lesson is too long to process in one request. Try splitting it into shorter sections.'}, status=500)

        try:
            data = message.content[0].input
        except (IndexError, AttributeError) as e:
            import logging
            logging.getLogger(__name__).error('Private lesson AI assist unexpected response: %s', e)
            return JsonResponse({'error': 'Unexpected AI response. Please try again.'}, status=500)

        return JsonResponse(data)


# AJAX endpoint for calendar integration
@csrf_exempt
def calendar_events_api(request):
    """API endpoint to provide calendar events as JSON"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    lessons = Lesson.objects.filter(
        is_deleted=False,
        lesson_request__isnull=False
    ).select_related('subject', 'student', 'teacher', 'lesson_request')

    # Filter by user permissions
    if hasattr(request.user, 'profile'):
        if request.user.profile.is_teacher:
            lessons = lessons.filter(teacher=request.user)
        elif request.user.profile.is_student or getattr(request.user.profile, 'is_guardian', False):
            lessons = lessons.filter(student=request.user)
        else:
            lessons = lessons.none()
    else:
        lessons = lessons.none()

    events = []
    for lesson in lessons:
        event = {
            'id': str(lesson.id),
            'title': f"{lesson.subject.subject}",
            'start': f"{lesson.lesson_date}T{lesson.lesson_time}",
            'color': lesson.calendar_color,
            'url': reverse('lessons:lesson_detail', args=[lesson.id]),
            'extendedProps': {
                'subject': lesson.subject.subject,
                'student': lesson.student.get_full_name() if lesson.student else 'Unknown',
                'teacher': lesson.teacher.get_full_name() if lesson.teacher else 'Unknown',
                'duration': lesson.duration_in_minutes,
                'location': lesson.location,
                'paymentStatus': lesson.payment_status.lower().replace(' ', ''),
                'price': str(lesson.price) if lesson.price else 'Not set',
                'lessonId': str(lesson.id),
            }
        }
        events.append(event)
    
    return JsonResponse(events, safe=False)


def get_previous_homework(request, lesson_id):
    """AJAX endpoint to fetch previous lessons' homework for the same student"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required', 'lessons': []}, status=401)

        # Get the current lesson
        try:
            lesson = get_object_or_404(Lesson, pk=lesson_id)
        except Exception as e:
            return JsonResponse({'error': 'Lesson not found', 'lessons': []}, status=404)

        # Verify teacher permission
        if not (hasattr(request.user, 'profile') and
                request.user.profile.is_teacher and
                lesson.teacher == request.user):
            return JsonResponse({'error': 'Permission denied', 'lessons': []}, status=403)

        # Get previous lessons for the same student with homework
        previous_lessons = Lesson.objects.filter(
            student=lesson.student,
            lesson_date__lt=lesson.lesson_date,
            is_deleted=False
        ).exclude(
            homework__isnull=True
        ).exclude(
            homework=''
        ).select_related('subject').order_by('-lesson_date')[:5]

        # Format the data
        data = [{
            'id': l.id,
            'date': l.lesson_date.strftime('%b %d, %Y'),
            'subject': l.subject.subject,
            'homework': l.homework,
            'preview': (l.homework[:60] + '...') if len(l.homework) > 60 else l.homework
        } for l in previous_lessons]

        return JsonResponse({'lessons': data, 'count': len(data)})

    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_previous_homework: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred', 'lessons': []}, status=500)


def notation_editor_poc(request):
    """
    Proof of Concept for VexFlow-based music notation editor
    Simple standalone page to test notation GUI
    """
    return render(request, 'lessons/notation_editor_poc.html')
