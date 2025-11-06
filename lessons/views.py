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
from django.db.models import Q
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views import View
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied

from apps.private_teaching.models import LessonRequest

from .models import Lesson, LessonOrder
from .forms import LessonForm, DocumentFormSet, LessonUrlsFormSet


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
            if self.request.user.profile.is_private_teacher:
                # Teachers see their lessons
                lessons = lessons.filter(teacher=self.request.user)
            elif self.request.user.profile.is_student:
                # Students see their lessons
                lessons = lessons.filter(student=self.request.user)
            else:
                lessons = lessons.none()
        else:
            lessons = lessons.none()

        # Convert lessons to calendar events
        calendar_events = []
        for lesson in lessons:
            # Determine color based on status hierarchy:
            # Pending (yellow), Accepted + Not Paid (green), Paid (blue), Assigned (darker)
            if lesson.status == 'Assigned':
                color = '#1e40af'  # Dark blue for assigned
            elif lesson.payment_status == 'Paid':
                color = '#3b82f6'  # Blue for paid
            elif lesson.approved_status == 'Accepted':
                color = '#10b981'  # Green for accepted but not paid
            elif lesson.approved_status == 'Rejected':
                color = '#ef4444'  # Red for rejected
            else:
                color = '#f59e0b'  # Yellow/orange for pending

            event = {
                'id': str(lesson.id),
                'title': f"{lesson.subject.subject}",
                'start': f"{lesson.lesson_date}T{lesson.lesson_time}",
                'color': color,
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
                               self.request.user.profile.is_private_teacher)
        context['is_student'] = (hasattr(self.request.user, 'profile') and
                               self.request.user.profile.is_student)

        return context


class LessonInline:
    """Mixin for handling inline formsets in lesson forms"""
    form_class = LessonForm
    model = Lesson

    def form_valid(self, form):
        named_formsets = self.get_named_formsets()

        if not all((x.is_valid() for x in named_formsets.values())):
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
                formset.save()

        # Send email if lesson was just published (Draft -> Assigned)
        new_status = self.object.status
        if old_status == 'Draft' and new_status == 'Assigned':
            if self.object.student and self.object.student.email:
                try:
                    teacher_name = self.request.user.get_full_name() or self.request.user.username
                    student_name = self.object.student.get_full_name() or self.object.student.username
                    subject = f"Your lesson is ready to view - {self.object.subject.subject}"

                    # Build email body
                    email_body = f"Hello {student_name},\n\n"
                    email_body += f"Great news! {teacher_name} has published your lesson and it's now ready to view.\n\n"
                    email_body += f"LESSON DETAILS:\n"
                    email_body += f"Subject: {self.object.subject.subject}\n"
                    email_body += f"Date: {self.object.lesson_date.strftime('%d %B %Y')}\n"
                    email_body += f"Time: {self.object.lesson_time.strftime('%H:%M')}\n"

                    if self.object.location:
                        email_body += f"Location: {self.object.location}\n"

                    email_body += f"\nYou can now access your lesson materials, documents, and links.\n\n"
                    email_body += f"View your lesson: {self.request.build_absolute_uri(reverse('lessons:lesson_detail', args=[self.object.pk]))}\n\n"
                    email_body += "Best regards,\nRECORDERED Team"

                    send_mail(
                        subject,
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [self.object.student.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    # Log error but don't fail the update
                    print(f"Error sending lesson assignment email: {e}")

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

    def get_object(self):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['pk'])
        # Check permissions - teacher or student can view
        user_can_view = False
        error_message = "You don't have permission to view this lesson."

        if hasattr(self.request.user, 'profile'):
            if self.request.user.profile.is_private_teacher:
                # Teacher can view lessons for their subjects if approved
                if lesson.teacher == self.request.user:
                    if lesson.approved_status == 'Accepted':
                        user_can_view = True
                    else:
                        error_message = "This lesson has not been approved yet."
            elif self.request.user.profile.is_student:
                # Student can view their own lessons if approved and paid
                if lesson.student == self.request.user:
                    if lesson.approved_status != 'Accepted':
                        error_message = "This lesson is still awaiting teacher approval."
                    elif lesson.payment_status != 'Paid':
                        error_message = "This lesson needs to be paid for before you can access it."
                    else:
                        # Allow access to approved and paid lessons regardless of Draft/Assigned status
                        user_can_view = True

        if not user_can_view:
            raise PermissionDenied(error_message)
        return lesson


class LessonUpdateView(LoginRequiredMixin, LessonInline, UpdateView):
    """Update lesson content and details - teacher only"""
    template_name = "lessons/lesson_update.html"
    login_url = 'private_teaching:login'

    def get_object(self):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['pk'])
        # Only teacher can edit lessons
        user_can_edit = False
        
        if hasattr(self.request.user, 'profile'):
            if self.request.user.profile.is_private_teacher:
                user_can_edit = lesson.subject.teacher == self.request.user
        
        if not user_can_edit:
            raise PermissionDenied()
        return lesson

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['named_formsets'] = self.get_named_formsets()
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

        if self.request.user.profile.is_private_teacher:
            # Teachers see their lessons
            return Lesson.objects.filter(
                teacher=self.request.user,
                is_deleted=False
            ).select_related('subject', 'student', 'lesson_request')
        elif self.request.user.profile.is_student:
            # Students see their lessons
            return Lesson.objects.filter(
                student=self.request.user,
                is_deleted=False
            ).select_related('subject', 'teacher', 'lesson_request')
        else:
            return Lesson.objects.none()


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
        if request.user.profile.is_private_teacher:
            lessons = lessons.filter(teacher=request.user)
        elif request.user.profile.is_student:
            lessons = lessons.filter(student=request.user)
        else:
            lessons = lessons.none()
    else:
        lessons = lessons.none()

    events = []
    for lesson in lessons:
        # Color based on status hierarchy
        if lesson.status == 'Assigned':
            color = '#1e40af'  # Dark blue
        elif lesson.payment_status == 'Paid':
            color = '#3b82f6'  # Blue
        elif lesson.approved_status == 'Accepted':
            color = '#10b981'  # Green
        elif lesson.approved_status == 'Rejected':
            color = '#ef4444'  # Red
        else:
            color = '#f59e0b'  # Yellow/orange

        event = {
            'id': str(lesson.id),
            'title': f"{lesson.subject.subject}",
            'start': f"{lesson.lesson_date}T{lesson.lesson_time}",
            'color': color,
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
