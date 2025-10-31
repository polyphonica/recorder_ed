from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, ListView, View
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from .models import LessonRequest, Subject, LessonRequestMessage, Cart, CartItem, Order, OrderItem
from lessons.models import Lesson, Document, LessonAttachedUrl
from .forms import LessonRequestForm, ProfileCompleteForm, StudentSignupForm, StudentLessonFormSet, TeacherProfileCompleteForm, TeacherLessonFormSet, TeacherResponseForm, SubjectForm
from .cart import CartManager
from .mixins import (
    StudentProfileCompletedMixin,
    StudentProfileNotCompletedMixin,
    StudentOnlyMixin,
    TeacherProfileCompletedMixin,
    TeacherProfileNotCompletedMixin,
    PrivateTeachingLoginRequiredMixin,
    AcceptedStudentRequiredMixin
)


class PrivateTeachingLoginView(LoginView):
    """Custom login view that redirects to private teaching after login"""
    template_name = 'private_teaching/login.html'
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('private_teaching:home')


class PrivateTeachingHomeView(TemplateView):
    """Home page for private teaching section"""
    template_name = 'private_teaching/home.html'
    
    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated and has a profile, check for appropriate redirects
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if teacher needs to complete profile
            if profile.is_private_teacher and not profile.profile_completed:
                messages.info(request, 'Please complete your teacher profile to access teaching features.')
                return redirect('private_teaching:teacher_profile_complete')
                
            # Check if student needs to complete profile  
            elif profile.is_student and not profile.profile_completed:
                messages.info(request, 'Please complete your profile to request lessons.')
                return redirect('private_teaching:profile_complete')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.all()

        # Get teachers offering private lessons
        from django.contrib.auth.models import User
        context['teachers'] = User.objects.filter(
            profile__is_private_teacher=True,
            profile__profile_completed=True
        ).select_related('profile')[:6]  # Limit to 6 teachers

        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            context['user_profile'] = self.request.user.profile
            if self.request.user.profile.is_student and self.request.user.profile.profile_completed:
                context['recent_requests'] = LessonRequest.objects.filter(
                    student=self.request.user
                ).prefetch_related('lessons__subject').order_by('-created_at')[:3]

        return context


class ProfileCompleteView(StudentProfileNotCompletedMixin, TemplateView):
    """View for completing user profile"""
    template_name = 'private_teaching/profile_complete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProfileCompleteForm(
            instance=self.request.user,
            user_profile=self.request.user.profile
        )
        return context
    
    def post(self, request, *args, **kwargs):
        form = ProfileCompleteForm(
            request.POST,
            instance=request.user,
            user_profile=request.user.profile
        )
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile completed successfully!')
            return redirect('private_teaching:home')
        
        return render(request, self.template_name, {'form': form})


class TeacherProfileCompleteView(TeacherProfileNotCompletedMixin, TemplateView):
    """View for completing teacher profile"""
    template_name = 'private_teaching/teacher_profile_complete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TeacherProfileCompleteForm(
            instance=self.request.user,
            user_profile=self.request.user.profile
        )
        return context
    
    def post(self, request, *args, **kwargs):
        form = TeacherProfileCompleteForm(
            request.POST,
            instance=request.user,
            user_profile=request.user.profile
        )
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Teacher profile completed successfully!')
            return redirect('private_teaching:teacher_dashboard')
        
        return render(request, self.template_name, {'form': form})


class LessonRequestCreateView(AcceptedStudentRequiredMixin, StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """View for students to create lesson requests with multiple lessons"""
    template_name = 'private_teaching/request_lesson.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = LessonRequestForm(user=self.request.user)
        context['formset'] = StudentLessonFormSet()
        context['subjects'] = Subject.objects.filter(is_active=True)
        return context

    def post(self, request, *args, **kwargs):
        form = LessonRequestForm(request.POST, user=request.user)
        formset = StudentLessonFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Create the lesson request container
            lesson_request = form.save(commit=False)
            lesson_request.student = request.user

            # Handle child profile if guardian
            if request.user.profile.is_guardian:
                child_id = form.cleaned_data.get('child_profile')
                if child_id:
                    from apps.accounts.models import ChildProfile
                    try:
                        child = ChildProfile.objects.get(id=child_id, guardian=request.user)
                        lesson_request.child_profile = child
                    except ChildProfile.DoesNotExist:
                        messages.error(request, 'Invalid child selected.')
                        return render(request, self.template_name, {
                            'form': form,
                            'formset': formset,
                            'subjects': Subject.objects.filter(is_active=True)
                        })

            lesson_request.save()

            # Save the lessons and populate student/teacher/lesson_request
            lessons = formset.save(commit=False)
            for lesson in lessons:
                lesson.lesson_request = lesson_request
                lesson.student = request.user
                # Teacher will be auto-populated from subject in Lesson.save()
                lesson.save()

            # Handle deleted lessons
            for lesson in formset.deleted_objects:
                lesson.delete()

            # Create initial message if provided in POST
            initial_message = request.POST.get('initial_message', '').strip()
            if initial_message:
                LessonRequestMessage.objects.create(
                    lesson_request=lesson_request,
                    author=request.user,
                    message=initial_message
                )

            # Send email notification to teacher(s)
            # Get unique teachers from all lessons
            teachers = set()
            for lesson in lessons:
                if lesson.teacher and lesson.teacher.email:
                    teachers.add(lesson.teacher)

            for teacher in teachers:
                try:
                    student_display_name = lesson_request.student_name
                    subject = f"New Lesson Request from {student_display_name}"

                    # Build email body
                    email_body = f"Hello {teacher.get_full_name() or teacher.username},\n\n"
                    email_body += f"You have received a new lesson request from {student_display_name}.\n\n"
                    email_body += f"REQUESTED LESSONS ({len(lessons)}):\n"

                    for lesson in lessons:
                        if lesson.teacher == teacher:
                            email_body += f"- {lesson.subject.subject} on {lesson.lesson_date} at {lesson.lesson_time}\n"

                    if initial_message:
                        email_body += f"\nMessage from student:\n{initial_message}\n\n"

                    email_body += f"\nView and respond to this request: {request.build_absolute_uri('/private-teaching/incoming-requests/')}\n\n"
                    email_body += "Best regards,\nRECORDERED Team"

                    send_mail(
                        subject,
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [teacher.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Error sending notification email to teacher: {e}")

            lesson_count = len(lessons)
            student_name = lesson_request.student_name
            messages.success(request, f'Lesson request for {student_name} submitted successfully with {lesson_count} lesson{"s" if lesson_count != 1 else ""}! The teacher will respond soon.')
            return redirect('private_teaching:my_requests')

        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'subjects': Subject.objects.filter(is_active=True)
        })


class MyLessonRequestsView(StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """View for students to see their lesson requests"""
    model = LessonRequest
    template_name = 'private_teaching/my_requests.html'
    context_object_name = 'lesson_requests'
    paginate_by = 10

    def get_queryset(self):
        return LessonRequest.objects.filter(
            student=self.request.user
        ).prefetch_related('messages', 'lessons__subject').order_by('-created_at')


class StudentLessonRequestDetailView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """Student view of their lesson request with message thread"""
    template_name = 'private_teaching/student_lesson_request_detail.html'

    def get_lesson_request(self):
        lesson_request = get_object_or_404(
            LessonRequest,
            id=self.kwargs['request_id'],
            student=self.request.user
        )
        return lesson_request

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson_request = self.get_lesson_request()

        context.update({
            'lesson_request': lesson_request,
            'lessons': lesson_request.lessons.filter(is_deleted=False).select_related('subject'),
            'messages': lesson_request.messages.select_related('author').order_by('created_at'),
        })
        return context

    def post(self, request, *args, **kwargs):
        """Handle student adding a message to the thread"""
        lesson_request = self.get_lesson_request()
        message_text = request.POST.get('message', '').strip()

        if message_text:
            LessonRequestMessage.objects.create(
                lesson_request=lesson_request,
                author=request.user,
                message=message_text
            )
            messages.success(request, 'Message sent successfully!')
        else:
            messages.error(request, 'Message cannot be empty.')

        return redirect('private_teaching:student_request_detail', request_id=lesson_request.id)


# Function-based view for student registration
def student_register(request):
    """Registration view specifically for students with guardian support"""
    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('private_teaching:profile_complete')
    else:
        form = StudentSignupForm()
    
    return render(request, 'private_teaching/register.html', {'form': form})


# ==========================================
# PHASE 2: TEACHER AND STUDENT DASHBOARDS
# ==========================================

class TeacherOnlyMixin:
    """Mixin to restrict access to private teachers only"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('private_teaching:login')
        if not hasattr(request.user, 'profile') or not request.user.profile.is_private_teacher:
            messages.error(request, 'Access denied. Teacher privileges required.')
            return redirect('private_teaching:home')
        return super().dispatch(request, *args, **kwargs)


class TeacherDashboardView(TeacherProfileCompletedMixin, TemplateView):
    """Dashboard for private teachers showing pending requests and today's lessons"""
    template_name = 'private_teaching/teacher_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date, timedelta

        # Get lesson requests for this teacher's subjects with pending lessons
        teacher_subjects = Subject.objects.filter(teacher=self.request.user)
        pending_requests = LessonRequest.objects.filter(
            lessons__subject__in=teacher_subjects,
            lessons__approved_status='Pending'
        ).distinct().prefetch_related('lessons__subject')

        # Get today's lessons for this teacher
        today = date.today()
        today_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            lesson_date=today,
            is_deleted=False
        ).select_related('student', 'subject', 'lesson_request', 'lesson_request__child_profile').order_by('lesson_time')

        # Get upcoming lessons (next 7 days)
        upcoming_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            lesson_date__gte=today,
            lesson_date__lte=today + timedelta(days=7),
            is_deleted=False
        ).select_related('student', 'subject', 'lesson_request', 'lesson_request__child_profile').order_by('lesson_date', 'lesson_time')[:10]

        context.update({
            'pending_requests': pending_requests,
            'pending_count': pending_requests.count(),
            'today_lessons': today_lessons,
            'upcoming_lessons': upcoming_lessons,
            'today': today,
        })
        return context


class StudentDashboardView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """Dashboard for students showing their lesson requests and upcoming lessons"""
    template_name = 'private_teaching/student_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date

        # Get student's recent requests
        recent_requests = LessonRequest.objects.filter(
            student=self.request.user
        ).prefetch_related('lessons__subject')[:5]

        # Get upcoming lessons (approved and paid lessons in the future)
        today = date.today()
        upcoming_lessons = Lesson.objects.filter(
            student=self.request.user,
            lesson_date__gte=today,
            approved_status='Accepted',
            is_deleted=False
        ).select_related('subject', 'teacher').order_by('lesson_date', 'lesson_time')[:5]

        # Get lessons awaiting payment (approved but not paid)
        awaiting_payment = Lesson.objects.filter(
            student=self.request.user,
            approved_status='Accepted',
            payment_status='Not Paid',
            is_deleted=False
        ).select_related('subject', 'teacher').order_by('lesson_date', 'lesson_time')[:5]

        context.update({
            'recent_requests': recent_requests,
            'upcoming_lessons': upcoming_lessons,
            'awaiting_payment': awaiting_payment,
            'today': today,
        })
        return context


class IncomingRequestsView(TeacherProfileCompletedMixin, ListView):
    """View for teachers to see and action incoming lesson requests"""
    template_name = 'private_teaching/incoming_requests.html'
    context_object_name = 'lesson_requests'
    paginate_by = 10

    def get_queryset(self):
        # Get all lesson requests for this teacher with at least one lesson
        from lessons.models import Lesson
        teacher_lesson_requests = LessonRequest.objects.filter(
            lessons__teacher=self.request.user,
            lessons__is_deleted=False
        ).distinct().prefetch_related('lessons__subject', 'messages').select_related('child_profile', 'student').order_by('-created_at')

        return teacher_lesson_requests


class LessonRequestDetailView(TeacherProfileCompletedMixin, TemplateView):
    """Detailed view for teachers to review and respond to a specific lesson request"""
    template_name = 'private_teaching/lesson_request_detail.html'

    def get_lesson_request(self):
        return get_object_or_404(LessonRequest, id=self.kwargs['request_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson_request = self.get_lesson_request()

        context.update({
            'lesson_request': lesson_request,
            'response_form': TeacherResponseForm(),
            'formset': TeacherLessonFormSet(instance=lesson_request),
        })
        return context

    def post(self, request, *args, **kwargs):
        lesson_request = self.get_lesson_request()
        response_form = TeacherResponseForm(request.POST)
        formset = TeacherLessonFormSet(request.POST, instance=lesson_request)

        if response_form.is_valid() and formset.is_valid():
            # Save the formset changes (lessons with updated approved_status)
            lessons = formset.save(commit=False)

            # Track changes for notifications
            accepted_lessons = []
            rejected_lessons = []

            for lesson in lessons:
                # Mark rejected lessons as deleted (soft delete)
                if lesson.approved_status == 'Rejected':
                    lesson.is_deleted = True
                    rejected_lessons.append(lesson)
                elif lesson.approved_status == 'Accepted':
                    accepted_lessons.append(lesson)
                lesson.save()

            # Handle deleted lessons from formset
            for lesson in formset.deleted_objects:
                lesson.is_deleted = True
                lesson.save()
                rejected_lessons.append(lesson)

            # Create a message if there's one
            message_text = response_form.cleaned_data.get('message')
            if message_text:
                LessonRequestMessage.objects.create(
                    lesson_request=lesson_request,
                    author=request.user,
                    message=message_text
                )

            # Send email notification to student
            if lesson_request.student and lesson_request.student.email:
                try:
                    teacher_name = request.user.get_full_name() or request.user.username
                    subject = f"Update on Your Lesson Request from {teacher_name}"

                    # Build email body
                    email_body = f"Hello {lesson_request.student.get_full_name() or lesson_request.student.username},\n\n"
                    email_body += f"Your lesson request has been updated by {teacher_name}.\n\n"

                    if accepted_lessons:
                        email_body += "ACCEPTED LESSONS:\n"
                        for lesson in accepted_lessons:
                            email_body += f"- {lesson.subject.subject} on {lesson.lesson_date} at {lesson.lesson_time}\n"
                        email_body += "\nYou can now proceed to payment for these lessons.\n\n"

                    if rejected_lessons:
                        email_body += "REJECTED LESSONS:\n"
                        for lesson in rejected_lessons:
                            email_body += f"- {lesson.subject.subject} on {lesson.lesson_date} at {lesson.lesson_time}\n"
                        email_body += "\n"

                    if message_text:
                        email_body += f"\nMessage from {teacher_name}:\n{message_text}\n\n"

                    email_body += f"\nView your lesson request: {request.build_absolute_uri('/private-teaching/my-requests/')}\n\n"
                    email_body += "Best regards,\nRECORDERED Team"

                    send_mail(
                        subject,
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [lesson_request.student.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Error sending notification email: {e}")

            messages.success(request, 'Lesson request updated and student notified!')
            return redirect('private_teaching:incoming_requests')

        return render(request, self.template_name, {
            'lesson_request': lesson_request,
            'response_form': response_form,
            'formset': formset,
        })


class TeacherScheduleView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher's schedule view showing approved lessons"""
    template_name = 'private_teaching/teacher_schedule.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date, timedelta

        # Get lessons for next 30 days
        today = date.today()
        end_date = today + timedelta(days=30)

        scheduled_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            lesson_date__range=[today, end_date],
            is_deleted=False
        ).select_related('student', 'subject', 'lesson_request', 'lesson_request__child_profile').order_by('lesson_date', 'lesson_time')

        context.update({
            'scheduled_lessons': scheduled_lessons,
            'today': today,
            'end_date': end_date,
        })
        return context


class MyLessonsView(StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """Student view of their approved/scheduled lessons"""
    template_name = 'private_teaching/my_lessons.html'
    context_object_name = 'lessons'
    paginate_by = 10

    def get_queryset(self):
        return Lesson.objects.filter(
            student=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).select_related('subject', 'teacher').order_by('lesson_date', 'lesson_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Separate paid and unpaid lessons
        lessons = self.get_queryset()
        context['paid_lessons'] = lessons.filter(payment_status='Paid')
        context['unpaid_lessons'] = lessons.filter(payment_status='Not Paid')

        return context


class CalendarView(PrivateTeachingLoginRequiredMixin, TemplateView):
    """Shared calendar view for both teachers and students"""
    template_name = 'private_teaching/calendar_simple.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import datetime, timedelta
        import json

        # Determine if user is a teacher
        try:
            is_teacher = self.request.user.profile.is_private_teacher
        except:
            is_teacher = False

        # Get lessons for calendar based on user role
        if is_teacher:
            # Teacher view - show all their lessons
            lessons = Lesson.objects.filter(
                teacher=self.request.user,
                lesson_date__isnull=False,
                lesson_time__isnull=False,
                is_deleted=False
            ).select_related('student', 'subject', 'lesson_request', 'lesson_request__child_profile')
        else:
            # Student view - show only their lessons
            lessons = Lesson.objects.filter(
                student=self.request.user,
                lesson_date__isnull=False,
                lesson_time__isnull=False,
                is_deleted=False
            ).select_related('student', 'teacher', 'subject', 'lesson_request', 'lesson_request__child_profile')

        # Convert lessons to calendar events
        calendar_events = []
        for lesson in lessons:
            # Combine date and time for event datetime
            lesson_datetime = datetime.combine(lesson.lesson_date, lesson.lesson_time)

            # Calculate end time (add duration) - convert to int in case it's a string
            duration_minutes = int(lesson.duration_in_minutes) if lesson.duration_in_minutes else 60
            end_datetime = lesson_datetime + timedelta(minutes=duration_minutes)

            # Determine color based on status hierarchy
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

            text_color = 'white'

            # Get subject name safely
            subject_name = lesson.subject.subject if lesson.subject else 'Unknown Subject'

            # Get student name - use child's name if lesson is for a child
            student_display_name = 'Unknown'
            if lesson.lesson_request and lesson.lesson_request.child_profile:
                # Lesson is for a child - show child's name
                student_display_name = lesson.lesson_request.child_profile.full_name
            elif lesson.student:
                # Regular student lesson
                student_display_name = lesson.student.get_full_name()

            # Determine title based on user role
            if is_teacher:
                title = f"{subject_name} - {student_display_name}"
            else:
                teacher_name = lesson.teacher.get_full_name() if lesson.teacher else 'Not assigned'
                title = f"{subject_name} - {teacher_name}"

            # Create event data
            event = {
                'id': str(lesson.id),
                'title': title,
                'start': lesson_datetime.isoformat(),
                'end': end_datetime.isoformat(),
                'backgroundColor': color,
                'borderColor': color,
                'textColor': text_color,
                'extendedProps': {
                    'lessonId': str(lesson.id),
                    'actualLessonId': str(lesson.id),  # Add actualLessonId for calendar navigation
                    'subject': subject_name,
                    'duration': lesson.duration_in_minutes,
                    'location': lesson.location or 'Not specified',
                    'paymentStatus': lesson.payment_status,
                    'approvedStatus': lesson.approved_status,
                    'status': lesson.status,
                    'student': student_display_name,
                    'teacher': lesson.teacher.get_full_name() if lesson.teacher else 'Not assigned',
                    'price': str(lesson.fee) if lesson.fee else 'Not set'
                }
            }
            calendar_events.append(event)

        context['calendar_events'] = json.dumps(calendar_events)
        context['is_teacher'] = is_teacher

        return context


class ActionRequestView(TeacherProfileCompletedMixin, View):
    """Handle individual lesson request approval/rejection"""
    
    def post(self, request, request_id):
        try:
            lesson_request = LessonRequest.objects.get(id=request_id, status='pending')
            action = request.POST.get('action')
            
            if action == 'approve':
                lesson_request.status = 'approved'
                lesson_request.save()
                messages.success(request, f'Lesson request from {lesson_request.student.get_full_name()} approved!')
                
            elif action == 'reject':
                lesson_request.status = 'rejected'
                lesson_request.save()
                messages.info(request, f'Lesson request from {lesson_request.student.get_full_name()} rejected.')
                
            else:
                messages.error(request, 'Invalid action.')
                
        except LessonRequest.DoesNotExist:
            messages.error(request, 'Lesson request not found or already processed.')
            
        return redirect('private_teaching:incoming_requests')


class BulkActionView(TeacherProfileCompletedMixin, View):
    """Handle bulk approval/rejection of lesson requests"""
    
    def post(self, request):
        selected_ids = request.POST.getlist('selected_requests')
        action = request.POST.get('action')
        
        if not selected_ids:
            messages.warning(request, 'No requests selected.')
            return redirect('private_teaching:incoming_requests')
            
        try:
            requests_to_update = LessonRequest.objects.filter(
                id__in=selected_ids, 
                status='pending'
            )
            
            if action == 'approve':
                updated_count = requests_to_update.update(status='approved')
                messages.success(request, f'Successfully approved {updated_count} lesson request{"s" if updated_count != 1 else ""}!')
                
            elif action == 'reject':
                updated_count = requests_to_update.update(status='rejected')
                messages.info(request, f'Successfully rejected {updated_count} lesson request{"s" if updated_count != 1 else ""}.')
                
            else:
                messages.error(request, 'Invalid bulk action.')
                
        except Exception as e:
            messages.error(request, f'Error processing bulk action: {str(e)}')
            
        return redirect('private_teaching:incoming_requests')


class TeacherSettingsView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher settings page for managing subjects and pricing"""
    template_name = 'private_teaching/teacher_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'subjects': Subject.objects.filter(teacher=self.request.user).order_by('subject'),
            'subject_form': SubjectForm(teacher=self.request.user),
        })
        return context


class SubjectCreateView(TeacherProfileCompletedMixin, View):
    """Create new subject for teacher"""
    
    def post(self, request, *args, **kwargs):
        form = SubjectForm(request.POST, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{form.cleaned_data["subject"]}" created successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('private_teaching:teacher_settings')


class SubjectUpdateView(TeacherProfileCompletedMixin, View):
    """Update existing subject for teacher"""
    
    def get_subject(self):
        return get_object_or_404(Subject, id=self.kwargs['subject_id'], teacher=self.request.user)
    
    def post(self, request, *args, **kwargs):
        subject = self.get_subject()
        form = SubjectForm(request.POST, instance=subject, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{subject.subject}" updated successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('private_teaching:teacher_settings')


class SubjectDeleteView(TeacherProfileCompletedMixin, View):
    """Delete subject for teacher"""

    def post(self, request, *args, **kwargs):
        subject = get_object_or_404(Subject, id=kwargs['subject_id'], teacher=request.user)
        subject_name = subject.subject
        subject.delete()
        messages.success(request, f'Subject "{subject_name}" deleted successfully!')
        return redirect('private_teaching:teacher_settings')


class UpdateZoomLinkView(TeacherProfileCompletedMixin, View):
    """Update teacher's default Zoom link"""

    def post(self, request, *args, **kwargs):
        default_zoom_link = request.POST.get('default_zoom_link', '').strip()
        request.user.profile.default_zoom_link = default_zoom_link
        request.user.profile.save()

        if default_zoom_link:
            messages.success(request, 'Default Zoom link saved successfully!')
        else:
            messages.success(request, 'Default Zoom link cleared successfully!')

        return redirect('private_teaching:teacher_settings')


# Cart Views
class AddToCartView(StudentProfileCompletedMixin, View):
    """Add individual lesson to cart"""

    def post(self, request, *args, **kwargs):
        lesson_id = kwargs.get('lesson_id')
        cart_manager = CartManager(request)

        success, message = cart_manager.add_lesson(lesson_id)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect(request.META.get('HTTP_REFERER', 'private_teaching:my_requests'))


class AddAllToCartView(StudentProfileCompletedMixin, View):
    """Add all approved lessons from a lesson request to cart"""
    
    def post(self, request, *args, **kwargs):
        lesson_request_id = kwargs.get('lesson_request_id')
        lesson_request = get_object_or_404(
            LessonRequest, 
            id=lesson_request_id, 
            student=request.user
        )
        
        cart_manager = CartManager(request)
        success, message = cart_manager.add_all_lessons_from_request(lesson_request)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect(request.META.get('HTTP_REFERER', 'private_teaching:my_requests'))


class CartView(StudentProfileCompletedMixin, TemplateView):
    """Display shopping cart"""
    template_name = 'private_teaching/cart.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_manager = CartManager(self.request)
        context.update(cart_manager.get_cart_context())
        return context


class RemoveFromCartView(StudentProfileCompletedMixin, View):
    """Remove lesson from cart"""

    def post(self, request, *args, **kwargs):
        lesson_id = kwargs.get('lesson_id')
        cart_manager = CartManager(request)

        success, message = cart_manager.remove_lesson(lesson_id)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('private_teaching:cart')


class ClearCartView(StudentProfileCompletedMixin, View):
    """Clear all items from cart"""
    
    def post(self, request, *args, **kwargs):
        cart_manager = CartManager(request)
        success, message = cart_manager.clear_cart()
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect('private_teaching:cart')


class CheckoutView(StudentProfileCompletedMixin, TemplateView):
    """Checkout page - placeholder for now"""
    template_name = 'private_teaching/checkout.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_manager = CartManager(self.request)
        context.update(cart_manager.get_cart_context())
        return context


class ProcessPaymentView(StudentProfileCompletedMixin, View):
    """Create Stripe checkout session and redirect to payment"""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from apps.payments.stripe_service import create_checkout_session

        cart_manager = CartManager(request)
        cart_context = cart_manager.get_cart_context()

        if not cart_context['cart_items']:
            messages.error(request, "Your cart is empty. Add lessons before checkout.")
            return redirect('private_teaching:cart')

        # Clean up ANY existing OrderItems for these lessons first
        lesson_ids_to_checkout = [cart_item.lesson.id for cart_item in cart_context['cart_items']]

        # Find ALL OrderItems for these lessons (regardless of order status)
        # This handles cases where orders are marked complete but lessons aren't paid
        orphaned_order_items = OrderItem.objects.filter(
            lesson_id__in=lesson_ids_to_checkout
        )

        # Delete the existing orders (will cascade delete OrderItems)
        orphaned_order_ids = list(orphaned_order_items.values_list('order_id', flat=True).distinct())
        if orphaned_order_ids:
            deleted_count = Order.objects.filter(id__in=orphaned_order_ids).delete()
            print(f"Cleaned up {deleted_count[0]} existing orders for these lessons")

        # Create order with pending status
        order = Order.objects.create(
            student=request.user,
            total_amount=cart_context['cart_total'],
            payment_status='pending',
            payment_method='stripe'
        )

        # Create order items (but don't mark lessons as paid yet)
        lesson_ids = []
        teacher = None
        for cart_item in cart_context['cart_items']:
            OrderItem.objects.create(
                order=order,
                lesson=cart_item.lesson,
                price_paid=cart_item.price
            )
            lesson_ids.append(str(cart_item.lesson.id))
            if not teacher and cart_item.lesson.teacher:
                teacher = cart_item.lesson.teacher

        # Prepare success and cancel URLs
        success_url = request.build_absolute_uri(
            reverse('private_teaching:checkout_success', kwargs={'order_id': order.id})
        )
        cancel_url = request.build_absolute_uri(
            reverse('private_teaching:checkout_cancel', kwargs={'order_id': order.id})
        )

        # Create Stripe checkout session
        try:
            session = create_checkout_session(
                amount=order.total_amount,
                student=request.user,
                teacher=teacher,
                domain='private_teaching',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'order_id': str(order.id),
                    'lesson_ids': ','.join(lesson_ids),
                }
            )

            # Save session ID to order
            order.stripe_checkout_session_id = session.id
            order.save()

            # Redirect to Stripe Checkout
            return redirect(session.url, code=303)

        except Exception as e:
            # If Stripe checkout creation fails, delete the order and show error
            order.delete()
            messages.error(request, f"Payment setup failed: {str(e)}. Please try again.")
            return redirect('private_teaching:cart')


class CheckoutSuccessView(StudentProfileCompletedMixin, TemplateView):
    """Handle return from Stripe after successful checkout"""
    template_name = 'private_teaching/payment_success.html'

    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id')

        try:
            order = Order.objects.get(
                id=order_id,
                student=request.user
            )

            # Clear the cart now that we've returned from Stripe
            cart_manager = CartManager(request)
            cart_manager.clear_cart()

            # The webhook will handle marking the order as completed
            # For now, just show the order details

            return self.render_to_response(self.get_context_data(**kwargs))

        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('private_teaching:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')

        try:
            order = Order.objects.get(
                id=order_id,
                student=self.request.user
            )
            context['order'] = order
            context['order_items'] = order.items.select_related(
                'lesson__subject',
                'lesson__teacher',
                'lesson__student'
            ).all()

            # Check if payment is still pending (webhook hasn't processed yet)
            context['payment_pending'] = order.payment_status == 'pending'

        except Order.DoesNotExist:
            context['order'] = None

        return context


class CheckoutCancelView(StudentProfileCompletedMixin, View):
    """Handle return from Stripe when payment is cancelled"""

    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id')

        try:
            order = Order.objects.get(
                id=order_id,
                student=request.user,
                payment_status='pending'
            )

            # Mark order as failed
            order.payment_status = 'failed'
            order.save()

            messages.warning(request, "Payment was cancelled. Your cart items are still available.")
            return redirect('private_teaching:cart')

        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('private_teaching:home')


class PaymentSuccessView(StudentProfileCompletedMixin, TemplateView):
    """Legacy payment success view - redirects to checkout success"""

    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id')
        return redirect('private_teaching:checkout_success', order_id=order_id)


class LessonDetailView(PrivateTeachingLoginRequiredMixin, View):
    """Get lesson details for calendar modal"""

    def get(self, request, *args, **kwargs):
        lesson_id = kwargs.get('lesson_id')

        try:
            # Get lesson based on user role
            if hasattr(request.user, 'profile') and request.user.profile.is_private_teacher:
                lesson = Lesson.objects.select_related(
                    'subject', 'student', 'teacher', 'lesson_request', 'lesson_request__child_profile'
                ).get(
                    id=lesson_id,
                    teacher=request.user,
                    approved_status='Accepted'
                )
            else:
                lesson = Lesson.objects.select_related(
                    'subject', 'student', 'teacher', 'lesson_request', 'lesson_request__child_profile'
                ).get(
                    id=lesson_id,
                    student=request.user,
                    approved_status='Accepted'
                )

            # Get student name - use child's name if lesson is for a child
            if lesson.lesson_request and lesson.lesson_request.child_profile:
                student_name = lesson.lesson_request.child_profile.full_name
            else:
                student_name = lesson.student.get_full_name() if lesson.student else 'Unknown'

            lesson_data = {
                'id': str(lesson.id),
                'subject': lesson.subject.subject if lesson.subject else 'Unknown',
                'date': lesson.lesson_date.strftime('%Y-%m-%d') if lesson.lesson_date else None,
                'time': lesson.lesson_time.strftime('%H:%M') if lesson.lesson_time else None,
                'duration': lesson.duration_in_minutes,
                'location': lesson.location or 'Not specified',
                'payment_status': lesson.payment_status,
                'approval_status': lesson.approved_status.lower(),
                'price': str(lesson.fee) if lesson.fee else 'Not set',
                'student': student_name,
                'teacher': lesson.teacher.get_full_name() if lesson.teacher else 'Not assigned'
            }

            return JsonResponse(lesson_data)

        except Lesson.DoesNotExist:
            return JsonResponse({'error': 'Lesson not found'}, status=404)


class StudentDocumentLibraryView(StudentProfileCompletedMixin, TemplateView):
    """Student document library - shows all documents and URLs from paid & assigned lessons"""
    template_name = 'private_teaching/student_document_library.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get search query
        search_query = self.request.GET.get('search', '').strip()

        # Get student's lessons that are paid AND assigned (published)
        student_lessons = Lesson.objects.filter(
            student=self.request.user,
            approved_status='Accepted',
            payment_status='Paid',
            status='Assigned',
            is_deleted=False
        ).select_related('subject', 'teacher')

        # Get documents from these lessons
        documents = Document.objects.filter(
            lesson__in=student_lessons
        ).select_related('lesson__subject', 'lesson__teacher').order_by('-lesson__lesson_date', '-uploaded_at')

        # Get URLs from these lessons
        urls = LessonAttachedUrl.objects.filter(
            lesson__in=student_lessons
        ).select_related('lesson__subject', 'lesson__teacher').order_by('-lesson__lesson_date', '-created_at')

        # Apply search filter if provided
        if search_query:
            # Search in document title, URL name, and lesson subject
            documents = documents.filter(
                Q(title__icontains=search_query) |
                Q(lesson__subject__subject__icontains=search_query)
            )

            urls = urls.filter(
                Q(name__icontains=search_query) |
                Q(lesson__subject__subject__icontains=search_query)
            )

        context['documents'] = documents
        context['urls'] = urls
        context['search_query'] = search_query
        context['total_items'] = documents.count() + urls.count()

        return context


class TeacherDocumentLibraryView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher document library - shows all uploaded documents and URLs with filters"""
    template_name = 'private_teaching/teacher_document_library.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get search query and filters
        search_query = self.request.GET.get('search', '').strip()
        student_filter = self.request.GET.get('student', '').strip()
        subject_filter = self.request.GET.get('subject', '').strip()

        # Get teacher's lessons (all approved lessons they teach)
        teacher_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).select_related('subject', 'student', 'teacher')

        # Apply filters
        if student_filter:
            teacher_lessons = teacher_lessons.filter(student__id=student_filter)

        if subject_filter:
            teacher_lessons = teacher_lessons.filter(subject__id=subject_filter)

        # Get documents from these lessons
        documents = Document.objects.filter(
            lesson__in=teacher_lessons
        ).select_related('lesson__subject', 'lesson__student', 'lesson__teacher').order_by('-lesson__lesson_date', '-uploaded_at')

        # Get URLs from these lessons
        urls = LessonAttachedUrl.objects.filter(
            lesson__in=teacher_lessons
        ).select_related('lesson__subject', 'lesson__student', 'lesson__teacher').order_by('-lesson__lesson_date', '-created_at')

        # Apply search filter if provided
        if search_query:
            documents = documents.filter(
                Q(title__icontains=search_query) |
                Q(lesson__subject__subject__icontains=search_query) |
                Q(lesson__student__first_name__icontains=search_query) |
                Q(lesson__student__last_name__icontains=search_query)
            )

            urls = urls.filter(
                Q(name__icontains=search_query) |
                Q(lesson__subject__subject__icontains=search_query) |
                Q(lesson__student__first_name__icontains=search_query) |
                Q(lesson__student__last_name__icontains=search_query)
            )

        # Get unique students and subjects for filter dropdowns
        # Get distinct student IDs first, then get the User objects
        student_ids = Lesson.objects.filter(
            teacher=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).values_list('student__id', flat=True).distinct()

        students = User.objects.filter(id__in=student_ids).select_related('profile').order_by('profile__first_name', 'profile__last_name', 'first_name', 'last_name')

        subjects = Subject.objects.filter(teacher=self.request.user, is_active=True)

        context['documents'] = documents
        context['urls'] = urls
        context['search_query'] = search_query
        context['student_filter'] = student_filter
        context['subject_filter'] = subject_filter
        context['students'] = students
        context['subjects'] = subjects
        context['total_items'] = documents.count() + urls.count()

        return context


class TeacherStudentsListView(TeacherProfileCompletedMixin, ListView):
    """Teacher view showing all their students in surname alphabetical order"""
    template_name = 'private_teaching/teacher_students_list.html'
    context_object_name = 'students'
    paginate_by = 20

    def get_queryset(self):
        # Get all distinct students who have lessons with this teacher
        from lessons.models import Lesson
        student_ids = Lesson.objects.filter(
            teacher=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).values_list('student__id', flat=True).distinct()

        # Get students ordered by surname (last_name)
        students = User.objects.filter(id__in=student_ids).select_related('profile')

        # Order by profile last_name if available, otherwise User last_name, then first_name
        from django.db.models import Case, When, Value, CharField, F
        students = students.annotate(
            effective_last_name=Case(
                When(profile__last_name__isnull=False, then=F('profile__last_name')),
                default=F('last_name'),
                output_field=CharField()
            ),
            effective_first_name=Case(
                When(profile__first_name__isnull=False, then=F('profile__first_name')),
                default=F('first_name'),
                output_field=CharField()
            )
        ).order_by('effective_last_name', 'effective_first_name')

        return students

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add lesson counts and subjects for each student
        from lessons.models import Lesson
        student_data = []
        for student in context['students']:
            lessons = Lesson.objects.filter(
                teacher=self.request.user,
                student=student,
                approved_status='Accepted',
                is_deleted=False
            ).select_related('subject')

            # Get unique subjects for this student
            subjects = Subject.objects.filter(
                teacher=self.request.user,
                lesson__student=student,
                lesson__approved_status='Accepted',
                lesson__is_deleted=False
            ).distinct()

            student_data.append({
                'user': student,
                'total_lessons': lessons.count(),
                'subjects': subjects
            })

        context['student_data'] = student_data
        return context


class StudentContactDetailView(TeacherProfileCompletedMixin, View):
    """AJAX view for getting student contact details"""

    def get(self, request, *args, **kwargs):
        student_id = kwargs.get('student_id')

        try:
            # Verify this teacher has lessons with this student
            from lessons.models import Lesson
            lesson_exists = Lesson.objects.filter(
                teacher=request.user,
                student_id=student_id,
                approved_status='Accepted',
                is_deleted=False
            ).exists()

            if not lesson_exists:
                return JsonResponse({'error': 'Access denied'}, status=403)

            # Get student details
            student = User.objects.select_related('profile').get(id=student_id)

            # Get profile data
            profile = student.profile

            # Build full address from components
            address_parts = [
                profile.address_line_1,
                profile.address_line_2,
                profile.city,
                profile.state_province,
                profile.postal_code,
                profile.country
            ]
            full_address = ', '.join([part for part in address_parts if part])

            # Build contact data
            contact_data = {
                'full_name': profile.full_name if hasattr(profile, 'full_name') else student.get_full_name(),
                'email': student.email,
                'phone': profile.phone if hasattr(profile, 'phone') else None,
                'address': full_address if full_address else None,
                'is_guardian': profile.is_guardian if hasattr(profile, 'is_guardian') else False,
            }

            # If guardian, get children
            if contact_data['is_guardian']:
                from apps.accounts.models import ChildProfile
                children = ChildProfile.objects.filter(guardian=student)
                contact_data['children'] = [
                    {
                        'full_name': child.full_name,
                        'date_of_birth': child.date_of_birth.strftime('%Y-%m-%d') if child.date_of_birth else None
                    }
                    for child in children
                ]

            return JsonResponse(contact_data)

        except User.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)


# ==========================================
# TEACHER-STUDENT APPLICATION SYSTEM
# ==========================================

class ApplyToTeacherView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """Student applies to study with a specific teacher"""
    template_name = 'private_teaching/apply_to_teacher.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher_id = self.kwargs.get('teacher_id')
        teacher = get_object_or_404(User, id=teacher_id, profile__is_private_teacher=True)

        # Check if already applied
        from apps.private_teaching.models import TeacherStudentApplication
        existing_application = TeacherStudentApplication.objects.filter(
            applicant=self.request.user,
            teacher=teacher,
            child_profile=None  # Adult application
        ).first()

        # Check teacher capacity and settings
        accepted_count = TeacherStudentApplication.objects.filter(
            teacher=teacher,
            status='accepted'
        ).count()

        context['teacher'] = teacher
        context['existing_application'] = existing_application
        context['accepted_count'] = accepted_count
        context['max_students'] = teacher.profile.max_private_students
        context['is_accepting'] = teacher.profile.accepting_new_private_students

        # Get child profiles if guardian
        if self.request.user.profile.is_guardian:
            from apps.accounts.models import ChildProfile
            context['children'] = ChildProfile.objects.filter(guardian=self.request.user)

        return context

    def post(self, request, *args, **kwargs):
        from apps.private_teaching.models import TeacherStudentApplication, ApplicationMessage

        teacher_id = kwargs.get('teacher_id')
        teacher = get_object_or_404(User, id=teacher_id, profile__is_private_teacher=True)

        # Check if teacher is accepting applications
        if not teacher.profile.accepting_new_private_students:
            messages.error(request, 'This teacher is not currently accepting new students.')
            return redirect('private_teaching:home')

        # Get child profile if guardian
        child_profile = None
        child_id = request.POST.get('child_profile')
        if request.user.profile.is_guardian and child_id:
            from apps.accounts.models import ChildProfile
            try:
                child_profile = ChildProfile.objects.get(id=child_id, guardian=request.user)
            except ChildProfile.DoesNotExist:
                messages.error(request, 'Invalid child profile selected.')
                return redirect('private_teaching:apply_to_teacher', teacher_id=teacher_id)

        # Check if already applied
        existing = TeacherStudentApplication.objects.filter(
            applicant=request.user,
            teacher=teacher,
            child_profile=child_profile
        ).first()

        if existing:
            messages.info(request, 'You have already applied to study with this teacher.')
            return redirect('private_teaching:student_application_detail', application_id=existing.id)

        # Create application
        application = TeacherStudentApplication.objects.create(
            applicant=request.user,
            teacher=teacher,
            child_profile=child_profile,
            status='pending'
        )

        # Add initial message if provided
        initial_message = request.POST.get('message', '').strip()
        if initial_message:
            ApplicationMessage.objects.create(
                application=application,
                author=request.user,
                message=initial_message
            )

        # Send email notification to teacher
        if teacher.email:
            try:
                student_name = child_profile.full_name if child_profile else request.user.get_full_name()
                applicant_email = request.user.email
                subject = f"New Student Application from {student_name}"

                # Build email body
                email_body = f"Hello {teacher.get_full_name() or teacher.username},\n\n"
                email_body += f"You have received a new application to study with you.\n\n"
                email_body += f"STUDENT DETAILS:\n"
                email_body += f"Name: {student_name}\n"

                if child_profile:
                    email_body += f"Guardian: {request.user.get_full_name() or request.user.username}\n"
                    email_body += f"Guardian Email: {applicant_email}\n"
                else:
                    email_body += f"Email: {applicant_email}\n"

                if initial_message:
                    email_body += f"\nMessage from student:\n{initial_message}\n\n"

                email_body += f"\nView and respond to this application: {request.build_absolute_uri(reverse('private_teaching:teacher_applications'))}\n\n"
                email_body += "Best regards,\nRECORDERED Team"

                send_mail(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [teacher.email],
                    fail_silently=True,
                )
            except Exception as e:
                # Log error but don't fail the application
                print(f"Error sending application notification email to teacher: {e}")

        student_name = child_profile.full_name if child_profile else request.user.get_full_name()
        messages.success(request, f'Application submitted for {student_name}!')
        return redirect('private_teaching:student_application_detail', application_id=application.id)


class StudentApplicationsListView(StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """List all applications for the student"""
    template_name = 'private_teaching/student_applications_list.html'
    context_object_name = 'applications'
    paginate_by = 10

    def get_queryset(self):
        from apps.private_teaching.models import TeacherStudentApplication
        return TeacherStudentApplication.objects.filter(
            applicant=self.request.user
        ).select_related('teacher', 'teacher__profile', 'child_profile').order_by('-created_at')


class StudentApplicationDetailView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """View single application with messaging"""
    template_name = 'private_teaching/student_application_detail.html'

    def get_application(self):
        from apps.private_teaching.models import TeacherStudentApplication
        return get_object_or_404(
            TeacherStudentApplication,
            id=self.kwargs['application_id'],
            applicant=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application()

        context['application'] = application
        context['app_messages'] = application.messages.select_related('author').order_by('created_at')

        return context

    def post(self, request, *args, **kwargs):
        """Handle sending a message"""
        from apps.private_teaching.models import ApplicationMessage

        application = self.get_application()
        message_text = request.POST.get('message', '').strip()

        if message_text:
            ApplicationMessage.objects.create(
                application=application,
                author=request.user,
                message=message_text
            )
            messages.success(request, 'Message sent!')
        else:
            messages.error(request, 'Message cannot be empty.')

        return redirect('private_teaching:student_application_detail', application_id=application.id)


# Teacher Application Management Views

class TeacherApplicationsListView(TeacherProfileCompletedMixin, ListView):
    """Teacher view of all student applications"""
    template_name = 'private_teaching/teacher_applications_list.html'
    context_object_name = 'applications'
    paginate_by = 20

    def get_queryset(self):
        from apps.private_teaching.models import TeacherStudentApplication
        status_filter = self.request.GET.get('status', 'pending')

        queryset = TeacherStudentApplication.objects.filter(
            teacher=self.request.user
        ).select_related('applicant', 'applicant__profile', 'child_profile')

        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('created_at')  # Oldest first (waiting longest)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.private_teaching.models import TeacherStudentApplication

        # Get counts for each status
        context['pending_count'] = TeacherStudentApplication.objects.filter(
            teacher=self.request.user, status='pending'
        ).count()
        context['accepted_count'] = TeacherStudentApplication.objects.filter(
            teacher=self.request.user, status='accepted'
        ).count()
        context['waitlist_count'] = TeacherStudentApplication.objects.filter(
            teacher=self.request.user, status='waitlist'
        ).count()
        context['declined_count'] = TeacherStudentApplication.objects.filter(
            teacher=self.request.user, status='declined'
        ).count()

        context['status_filter'] = self.request.GET.get('status', 'pending')
        context['max_students'] = self.request.user.profile.max_private_students
        context['accepting_new'] = self.request.user.profile.accepting_new_private_students

        return context


class TeacherApplicationDetailView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher view of single application with messaging and status management"""
    template_name = 'private_teaching/teacher_application_detail.html'

    def get_application(self):
        from apps.private_teaching.models import TeacherStudentApplication
        return get_object_or_404(
            TeacherStudentApplication,
            id=self.kwargs['application_id'],
            teacher=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application()

        context['application'] = application
        context['app_messages'] = application.messages.select_related('author').order_by('created_at')

        return context

    def post(self, request, *args, **kwargs):
        """Handle sending a message or changing status"""
        from apps.private_teaching.models import ApplicationMessage

        application = self.get_application()
        action = request.POST.get('action')

        if action == 'send_message':
            message_text = request.POST.get('message', '').strip()
            if message_text:
                ApplicationMessage.objects.create(
                    application=application,
                    author=request.user,
                    message=message_text
                )
                messages.success(request, 'Message sent!')
            else:
                messages.error(request, 'Message cannot be empty.')

        elif action == 'update_status':
            new_status = request.POST.get('status')
            teacher_notes = request.POST.get('teacher_notes', '').strip()

            if new_status in ['accepted', 'waitlist', 'declined']:
                old_status = application.status
                application.status = new_status
                application.teacher_notes = teacher_notes
                application.status_changed_at = timezone.now()
                application.save()

                # Create a message in the thread if teacher provided notes
                if teacher_notes:
                    ApplicationMessage.objects.create(
                        application=application,
                        author=request.user,
                        message=teacher_notes
                    )

                # Send email notification to student
                if application.applicant and application.applicant.email:
                    try:
                        teacher_name = request.user.get_full_name() or request.user.username
                        student_name = application.student_name
                        subject = f"Update on Your Application to Study with {teacher_name}"

                        # Build email body based on status
                        email_body = f"Hello {student_name},\n\n"

                        if new_status == 'accepted':
                            email_body += f"Great news! {teacher_name} has accepted your application to study with them.\n\n"
                            email_body += f"You can now request lessons from {teacher_name}.\n\n"
                        elif new_status == 'waitlist':
                            email_body += f"{teacher_name} has placed you on their waiting list.\n\n"
                        elif new_status == 'declined':
                            email_body += f"{teacher_name} has reviewed your application.\n\n"

                        if teacher_notes:
                            email_body += f"Message from {teacher_name}:\n{teacher_notes}\n\n"

                        if new_status == 'accepted':
                            email_body += f"Request lessons: {request.build_absolute_uri(reverse('private_teaching:request_lesson'))}\n\n"
                        else:
                            email_body += f"View your application: {request.build_absolute_uri(reverse('private_teaching:student_applications'))}\n\n"

                        email_body += "Best regards,\nRECORDERED Team"

                        send_mail(
                            subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [application.applicant.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        # Log error but don't fail the status update
                        print(f"Error sending application status email: {e}")

                messages.success(request, f'Application status updated to {application.get_status_display()}!')

                # If accepted from waitlist, check if we should notify next in line
                if new_status == 'accepted' and old_status == 'waitlist':
                    # No additional action needed - student already notified above
                    pass

            else:
                messages.error(request, 'Invalid status selected.')

        return redirect('private_teaching:teacher_application_detail', application_id=application.id)


class UpdateTeacherCapacityView(TeacherProfileCompletedMixin, View):
    """Update teacher's capacity settings"""

    def post(self, request, *args, **kwargs):
        max_students = request.POST.get('max_private_students', '').strip()
        accepting_new = request.POST.get('accepting_new_private_students') == 'on'

        profile = request.user.profile

        # Update max students
        if max_students:
            try:
                profile.max_private_students = int(max_students)
            except ValueError:
                messages.error(request, 'Invalid number for max students.')
                return redirect('private_teaching:teacher_applications')
        else:
            profile.max_private_students = None

        profile.accepting_new_private_students = accepting_new
        profile.save()

        messages.success(request, 'Capacity settings updated!')
        return redirect('private_teaching:teacher_applications')