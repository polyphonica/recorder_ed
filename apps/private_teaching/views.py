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

from apps.core.views import BaseCheckoutSuccessView, BaseCheckoutCancelView, UserFilterMixin
from .models import LessonRequest, Subject, LessonRequestMessage, Cart, CartItem, Order, OrderItem, TeacherStudentApplication, ExamRegistration, ExamPiece, ExamBoard, LessonCancellationRequest
from .notifications import TeacherNotificationService, StudentNotificationService
from lessons.models import Lesson, Document, LessonAttachedUrl
from .forms import LessonRequestForm, ProfileCompleteForm, StudentSignupForm, StudentLessonFormSet, TeacherProfileCompleteForm, TeacherLessonFormSet, TeacherResponseForm, SubjectForm, ExamRegistrationForm, ExamPieceFormSet, ExamResultsForm
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
                    TeacherNotificationService.send_new_lesson_request_notification(
                        lesson_request=lesson_request,
                        lessons=lessons,
                        teacher=teacher
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

        # Get pending student applications (initial applications to study with teacher)
        pending_applications = TeacherStudentApplication.objects.filter(
            teacher=self.request.user,
            status='pending'
        ).select_related('applicant', 'child_profile').order_by('-created_at')

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
            'pending_applications': pending_applications,
            'pending_applications_count': pending_applications.count(),
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

        # Get student's teacher applications
        my_applications = TeacherStudentApplication.objects.filter(
            applicant=self.request.user
        ).select_related('teacher', 'child_profile').order_by('-created_at')

        # Count applications by status
        pending_applications = my_applications.filter(status='pending')
        accepted_applications = my_applications.filter(status='accepted')
        waitlist_applications = my_applications.filter(status='waitlist')
        declined_applications = my_applications.filter(status='declined')

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
            'my_applications': my_applications,
            'pending_applications': pending_applications,
            'accepted_applications': accepted_applications,
            'waitlist_applications': waitlist_applications,
            'declined_applications': declined_applications,
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
                    StudentNotificationService.send_lesson_request_response_notification(
                        lesson_request=lesson_request,
                        teacher=request.user,
                        accepted_lessons=accepted_lessons,
                        rejected_lessons=rejected_lessons,
                        message_text=message_text
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


class CheckoutSuccessView(StudentProfileCompletedMixin, BaseCheckoutSuccessView):
    """Handle return from Stripe after successful checkout"""
    template_name = 'private_teaching/payment_success.html'

    def get_object_model(self):
        return Order

    def get_object_id_kwarg(self):
        return 'order_id'

    def get_redirect_url_name(self):
        return 'private_teaching:home'

    def perform_post_checkout_actions(self, obj):
        """Clear the cart after successful checkout"""
        cart_manager = CartManager(self.request)
        cart_manager.clear_cart()

    def get_context_extras(self, obj):
        order_items = obj.items.select_related(
            'lesson__subject',
            'lesson__teacher',
            'lesson__student'
        ).all()

        return {
            'order': obj,
            'order_items': order_items,
            'payment_pending': obj.payment_status == 'pending',
        }


class CheckoutCancelView(StudentProfileCompletedMixin, BaseCheckoutCancelView):
    """Handle return from Stripe when payment is cancelled"""
    redirect_on_cancel = True

    def get_object_model(self):
        return Order

    def get_object_id_kwarg(self):
        return 'order_id'

    def get_redirect_url_name(self):
        return 'private_teaching:cart'

    def get_cancel_message(self):
        return "Payment was cancelled. Your cart items are still available."

    def get_object_filter_kwargs(self, object_id):
        """Override to add payment_status filter"""
        return {
            'id': object_id,
            'student': self.request.user,
            'payment_status': 'pending'
        }


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
                'teacher': lesson.teacher.get_full_name() if lesson.teacher else 'Not assigned',
                'lesson_request_id': lesson.lesson_request.id if lesson.lesson_request else None,
                'student_id': lesson.student.id if lesson.student else None
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

        # Get current terms for T&Cs modal
        from .models import PrivateLessonTermsAndConditions
        current_terms = PrivateLessonTermsAndConditions.objects.filter(is_current=True).first()

        context['teacher'] = teacher
        context['existing_application'] = existing_application
        context['accepted_count'] = accepted_count
        context['max_students'] = teacher.profile.max_private_students
        context['is_accepting'] = teacher.profile.accepting_new_private_students
        context['current_terms'] = current_terms

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

        # Create terms acceptance record
        from .models import PrivateLessonTermsAndConditions, PrivateLessonTermsAcceptance
        current_terms = PrivateLessonTermsAndConditions.objects.filter(is_current=True).first()
        if current_terms:
            PrivateLessonTermsAcceptance.objects.create(
                student=request.user,
                terms_version=current_terms,
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
                # Note: lesson field will remain null - this tracks application-level acceptance
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
                TeacherNotificationService.send_new_application_notification(
                    application=application,
                    teacher=teacher,
                    initial_message=initial_message
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

class TeacherApplicationsListView(UserFilterMixin, TeacherProfileCompletedMixin, ListView):
    """Teacher view of all student applications. Uses UserFilterMixin for automatic teacher filtering."""
    model = TeacherStudentApplication
    template_name = 'private_teaching/teacher_applications_list.html'
    context_object_name = 'applications'
    paginate_by = 20
    user_field_name = 'teacher'

    def get_queryset(self):
        status_filter = self.request.GET.get('status', 'pending')

        # UserFilterMixin automatically filters by teacher=self.request.user
        queryset = super().get_queryset().select_related('applicant', 'applicant__profile', 'child_profile')

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
                        StudentNotificationService.send_application_status_notification(
                            application=application,
                            teacher=request.user,
                            new_status=new_status,
                            teacher_notes=teacher_notes
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


# ============================================================================
# EXAM REGISTRATION VIEWS
# ============================================================================

class ExamRegistrationListView(UserFilterMixin, PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, ListView):
    """List all exam registrations for a teacher. Uses UserFilterMixin."""
    model = ExamRegistration
    template_name = 'private_teaching/exams/list.html'
    context_object_name = 'exams'
    paginate_by = 20
    user_field_name = 'teacher'

    def get_queryset(self):
        # UserFilterMixin automatically filters by teacher=self.request.user
        queryset = super().get_queryset().select_related(
            'student', 'child_profile', 'subject', 'exam_board'
        ).prefetch_related('pieces')

        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-exam_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter:
            context['status_filter'] = status_filter

        # Get all exams for this teacher (not paginated)
        all_exams = ExamRegistration.objects.filter(
            teacher=self.request.user
        ).select_related(
            'student', 'child_profile', 'subject', 'exam_board'
        ).prefetch_related('pieces')

        # Group exams for sidebar/stats
        context['upcoming_exams'] = all_exams.filter(
            exam_date__gte=timezone.now().date(),
            status=ExamRegistration.REGISTERED
        ).order_by('exam_date')[:5]

        context['pending_results'] = all_exams.filter(
            status=ExamRegistration.SUBMITTED
        ).order_by('-exam_date')[:5]

        return context


class ExamRegistrationCreateView(PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, View):
    """Create a new exam registration"""
    template_name = 'private_teaching/exams/create.html'

    def get(self, request):
        # Get student from query parameter if provided
        student_id = request.GET.get('student')
        form = ExamRegistrationForm(teacher=request.user, student=student_id)
        piece_formset = ExamPieceFormSet()

        return render(request, self.template_name, {
            'form': form,
            'piece_formset': piece_formset,
        })

    def post(self, request):
        form = ExamRegistrationForm(request.POST, teacher=request.user)
        piece_formset = ExamPieceFormSet(request.POST)

        if form.is_valid() and piece_formset.is_valid():
            with transaction.atomic():
                exam = form.save()

                # Save pieces
                pieces = piece_formset.save(commit=False)
                for piece in pieces:
                    piece.exam_registration = exam
                    piece.save()

                # Delete removed pieces
                for obj in piece_formset.deleted_objects:
                    obj.delete()

                messages.success(request, f'Exam registration created for {exam.student_name}!')

                # Send notification to student/parent
                StudentNotificationService.send_exam_registration_notification(exam)

                return redirect('private_teaching:exam_detail', pk=exam.id)

        return render(request, self.template_name, {
            'form': form,
            'piece_formset': piece_formset,
        })


class ExamRegistrationDetailView(PrivateTeachingLoginRequiredMixin, View):
    """View exam registration details"""
    template_name = 'private_teaching/exams/detail.html'

    def get(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk)

        # Check permissions
        if request.user == exam.teacher:
            # Teacher view
            is_teacher = True
        elif request.user == exam.student or (exam.child_profile and request.user == exam.child_profile.guardian):
            # Student/parent view
            is_teacher = False
        else:
            messages.error(request, 'You do not have permission to view this exam.')
            return redirect('private_teaching:home')

        pieces = exam.pieces.all().order_by('piece_number')
        preparation_lessons = exam.preparation_lessons.all().order_by('-lesson_date')[:10] if is_teacher else None

        return render(request, self.template_name, {
            'exam': exam,
            'pieces': pieces,
            'preparation_lessons': preparation_lessons,
            'is_teacher': is_teacher,
        })


class ExamRegistrationUpdateView(PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, View):
    """Update exam registration"""
    template_name = 'private_teaching/exams/edit.html'

    def get(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)
        form = ExamRegistrationForm(instance=exam, teacher=request.user)
        piece_formset = ExamPieceFormSet(instance=exam)

        return render(request, self.template_name, {
            'exam': exam,
            'form': form,
            'piece_formset': piece_formset,
        })

    def post(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)
        form = ExamRegistrationForm(request.POST, instance=exam, teacher=request.user)
        piece_formset = ExamPieceFormSet(request.POST, instance=exam)

        if form.is_valid() and piece_formset.is_valid():
            with transaction.atomic():
                exam = form.save()

                # Save pieces
                pieces = piece_formset.save(commit=False)
                for piece in pieces:
                    piece.exam_registration = exam
                    piece.save()

                # Delete removed pieces
                for obj in piece_formset.deleted_objects:
                    obj.delete()

                messages.success(request, 'Exam registration updated!')
                return redirect('private_teaching:exam_detail', pk=exam.id)

        return render(request, self.template_name, {
            'exam': exam,
            'form': form,
            'piece_formset': piece_formset,
        })


class ExamRegistrationDeleteView(PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, View):
    """Delete exam registration"""

    def post(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)

        student_name = exam.student_name
        exam.delete()

        messages.success(request, f'Exam registration for {student_name} has been deleted.')
        return redirect('private_teaching:exam_list')


class ExamResultsUpdateView(PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, View):
    """Update exam results"""
    template_name = 'private_teaching/exams/results.html'

    def get(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)
        form = ExamResultsForm(instance=exam)

        return render(request, self.template_name, {
            'exam': exam,
            'form': form,
        })

    def post(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)
        form = ExamResultsForm(request.POST, instance=exam)

        if form.is_valid():
            exam = form.save()
            messages.success(request, 'Exam results updated!')

            # Send notification to student/parent
            StudentNotificationService.send_exam_results_notification(exam)

            return redirect('private_teaching:exam_detail', pk=exam.id)

        return render(request, self.template_name, {
            'exam': exam,
            'form': form,
        })


class StudentExamListView(PrivateTeachingLoginRequiredMixin, StudentProfileCompletedMixin, ListView):
    """List all exams for a student"""
    model = ExamRegistration
    template_name = 'private_teaching/exams/student_list.html'
    context_object_name = 'exams'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Get exams where user is the student or guardian
        return ExamRegistration.objects.filter(
            Q(student=user) | Q(child_profile__guardian=user)
        ).select_related(
            'teacher', 'subject', 'exam_board', 'child_profile'
        ).prefetch_related('pieces').order_by('-exam_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all exams for this user (not paginated)
        user = self.request.user
        all_exams = ExamRegistration.objects.filter(
            Q(student=user) | Q(child_profile__guardian=user)
        ).select_related(
            'teacher', 'subject', 'exam_board', 'child_profile'
        ).prefetch_related('pieces')

        # Group exams for stats
        context['upcoming_exams'] = all_exams.filter(
            exam_date__gte=timezone.now().date(),
            status__in=[ExamRegistration.REGISTERED, ExamRegistration.SUBMITTED]
        ).order_by('exam_date')

        context['completed_exams'] = all_exams.filter(
            status=ExamRegistration.RESULTS_RECEIVED
        ).order_by('-exam_date')

        context['unpaid_exams'] = all_exams.filter(
            payment_status='pending'
        ).order_by('exam_date')

        return context


class ExamPaymentView(PrivateTeachingLoginRequiredMixin, View):
    """Handle exam payment via Stripe"""

    def post(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk)

        # Check permissions (student or guardian can pay)
        if not (request.user == exam.student or
                (exam.child_profile and request.user == exam.child_profile.guardian)):
            messages.error(request, 'You do not have permission to pay for this exam.')
            return redirect('private_teaching:home')

        # Check if already paid
        if exam.is_paid:
            messages.info(request, 'This exam has already been paid for.')
            return redirect('private_teaching:exam_detail', pk=exam.id)

        # Check if payment is required
        if not exam.requires_payment or exam.fee_amount <= 0:
            messages.error(request, 'No payment is required for this exam.')
            return redirect('private_teaching:exam_detail', pk=exam.id)

        # Create Stripe checkout session
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gbp',
                        'unit_amount': int(exam.fee_amount * 100),  # Convert to pence
                        'product_data': {
                            'name': f'Exam Registration: {exam.display_name}',
                            'description': f'{exam.student_name} - {exam.exam_board} {exam.get_grade_type_display()} Grade {exam.grade_level}',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('private_teaching:exam_payment_success', kwargs={'pk': exam.id})
                ),
                cancel_url=request.build_absolute_uri(
                    reverse('private_teaching:exam_payment_cancel', kwargs={'pk': exam.id})
                ),
                client_reference_id=str(exam.id),
                metadata={
                    'exam_id': str(exam.id),
                    'student_id': str(exam.student.id),
                    'teacher_id': str(exam.teacher.id),
                }
            )

            # Save checkout session ID
            exam.stripe_checkout_session_id = checkout_session.id
            exam.payment_status = 'pending'
            exam.save()

            return redirect(checkout_session.url)

        except Exception as e:
            messages.error(request, f'Error creating payment session: {str(e)}')
            return redirect('private_teaching:exam_detail', pk=exam.id)


class ExamPaymentSuccessView(BaseCheckoutSuccessView):
    """Handle successful exam payment"""
    template_name = 'core/checkout_success.html'

    def get_object_model(self):
        return ExamRegistration

    def get_object_id_kwarg(self):
        return 'pk'

    def get_redirect_url_name(self):
        return 'private_teaching:student_exams'

    def perform_post_checkout_actions(self, exam):
        """Mark exam as paid after successful checkout"""
        if exam.payment_status != 'completed':
            exam.payment_status = 'completed'
            exam.paid_at = timezone.now()
            exam.save(update_fields=['payment_status', 'paid_at'])

    def get_context_extras(self, exam):
        return {
            'exam': exam,
            'student_name': exam.student_name,
            'success_message': f'Payment successful! Your exam registration for {exam.display_name} is confirmed.',
            'detail_url': reverse('private_teaching:exam_detail', kwargs={'pk': exam.id}),
            'detail_button_text': 'View Exam Details',
        }


class ExamPaymentCancelView(BaseCheckoutCancelView):
    """Handle cancelled exam payment"""
    template_name = 'core/checkout_cancel.html'

    def get_object_model(self):
        return ExamRegistration

    def get_object_id_kwarg(self):
        return 'pk'

    def get_redirect_url_name(self):
        return 'private_teaching:exam_detail'


class PrivateLessonTermsView(TemplateView):
    """Display current Private Lesson Terms and Conditions"""
    template_name = 'private_teaching/terms_and_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import PrivateLessonTermsAndConditions

        current_terms = PrivateLessonTermsAndConditions.objects.filter(is_current=True).first()
        context['current_terms'] = current_terms

        return context


# ============================================================================
# LESSON CANCELLATION VIEWS
# ============================================================================

class RequestLessonCancellationView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """Student submits cancellation/reschedule request for a lesson"""
    template_name = 'private_teaching/request_cancellation.html'

    def get_lesson(self):
        """Get the lesson being cancelled"""
        lesson_id = self.kwargs.get('lesson_id')
        return get_object_or_404(
            Lesson,
            id=lesson_id,
            student=self.request.user,
            is_deleted=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.get_lesson()

        # Calculate hours until lesson and check policy
        from datetime import datetime
        lesson_datetime = datetime.combine(lesson.lesson_date, lesson.lesson_time)
        lesson_datetime = timezone.make_aware(lesson_datetime)
        time_until_lesson = lesson_datetime - timezone.now()
        hours_before_lesson = time_until_lesson.total_seconds() / 3600
        is_within_policy = hours_before_lesson >= 48

        # Calculate potential refund amount (lesson fee minus platform fee)
        # Platform fee is typically 10% - adjust as needed
        PLATFORM_FEE_PERCENTAGE = 0.10
        if lesson.fee and lesson.payment_status == 'Paid':
            platform_fee = lesson.fee * PLATFORM_FEE_PERCENTAGE
            refund_amount = lesson.fee - platform_fee
        else:
            platform_fee = 0
            refund_amount = 0

        # Check if existing cancellation request exists
        existing_request = LessonCancellationRequest.objects.filter(
            lesson=lesson,
            status__in=[LessonCancellationRequest.PENDING, LessonCancellationRequest.APPROVED]
        ).first()

        context['lesson'] = lesson
        context['hours_before_lesson'] = hours_before_lesson
        context['is_within_policy'] = is_within_policy
        context['refund_amount'] = refund_amount
        context['platform_fee'] = platform_fee
        context['existing_request'] = existing_request
        context['reason_choices'] = LessonCancellationRequest.REASON_CHOICES

        return context

    def post(self, request, *args, **kwargs):
        """Handle cancellation request submission"""
        lesson = self.get_lesson()

        # Check for existing pending/approved request
        existing_request = LessonCancellationRequest.objects.filter(
            lesson=lesson,
            status__in=[LessonCancellationRequest.PENDING, LessonCancellationRequest.APPROVED]
        ).first()

        if existing_request:
            messages.error(request, 'A cancellation request for this lesson is already pending.')
            return redirect('private_teaching:my_lessons')

        # Get form data
        request_type = request.POST.get('request_type')
        cancellation_reason = request.POST.get('cancellation_reason')
        student_message = request.POST.get('student_message', '').strip()
        proposed_new_date = request.POST.get('proposed_new_date', '').strip() if request_type == 'reschedule' else None
        proposed_new_time = request.POST.get('proposed_new_time', '').strip() if request_type == 'reschedule' else None

        # Validation
        if not request_type or request_type not in ['cancel_refund', 'reschedule']:
            messages.error(request, 'Please select a valid request type.')
            return redirect('private_teaching:request_cancellation', lesson_id=lesson.id)

        if not cancellation_reason:
            messages.error(request, 'Please select a cancellation reason.')
            return redirect('private_teaching:request_cancellation', lesson_id=lesson.id)

        if not student_message:
            messages.error(request, 'Please provide an explanation for your request.')
            return redirect('private_teaching:request_cancellation', lesson_id=lesson.id)

        # Create cancellation request
        cancellation_request = LessonCancellationRequest.objects.create(
            lesson=lesson,
            student=request.user,
            teacher=lesson.teacher,
            request_type=request_type,
            cancellation_reason=cancellation_reason,
            student_message=student_message,
            proposed_new_date=proposed_new_date if proposed_new_date else None,
            proposed_new_time=proposed_new_time if proposed_new_time else None
        )

        # Calculate refund amounts if eligible
        if cancellation_request.can_receive_refund:
            PLATFORM_FEE_PERCENTAGE = 0.10
            platform_fee = lesson.fee * PLATFORM_FEE_PERCENTAGE
            refund_amount = lesson.fee - platform_fee

            cancellation_request.refund_amount = refund_amount
            cancellation_request.platform_fee_retained = platform_fee
            cancellation_request.save(update_fields=['refund_amount', 'platform_fee_retained'])

        # Send notification to teacher
        if lesson.teacher and lesson.teacher.email:
            try:
                TeacherNotificationService.send_cancellation_request_notification(
                    cancellation_request=cancellation_request,
                    lesson=lesson,
                    student=request.user
                )
            except Exception as e:
                print(f"Error sending cancellation notification to teacher: {e}")

        if request_type == 'reschedule':
            messages.success(request, 'Reschedule request submitted! Your teacher will review it shortly.')
        else:
            messages.success(request, 'Cancellation request submitted! Your teacher will review it shortly.')

        return redirect('private_teaching:cancellation_request_detail', request_id=cancellation_request.id)


class CancellationRequestDetailView(PrivateTeachingLoginRequiredMixin, TemplateView):
    """View details of a cancellation request (for both student and teacher)"""
    template_name = 'private_teaching/cancellation_request_detail.html'

    def get_cancellation_request(self):
        """Get the cancellation request"""
        request_id = self.kwargs.get('request_id')
        cancellation_request = get_object_or_404(LessonCancellationRequest, id=request_id)

        # Check permissions
        if self.request.user not in [cancellation_request.student, cancellation_request.teacher]:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this cancellation request.")

        return cancellation_request

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cancellation_request = self.get_cancellation_request()

        context['cancellation_request'] = cancellation_request
        context['lesson'] = cancellation_request.lesson
        context['is_teacher'] = self.request.user == cancellation_request.teacher
        context['is_student'] = self.request.user == cancellation_request.student

        return context


class TeacherCancellationRequestsView(TeacherProfileCompletedMixin, ListView):
    """Teacher view of all cancellation requests"""
    template_name = 'private_teaching/teacher_cancellation_requests.html'
    context_object_name = 'cancellation_requests'
    paginate_by = 20

    def get_queryset(self):
        status_filter = self.request.GET.get('status', 'pending')

        queryset = LessonCancellationRequest.objects.filter(
            teacher=self.request.user
        ).select_related('lesson', 'student', 'lesson__subject')

        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get counts for each status
        context['pending_count'] = LessonCancellationRequest.objects.filter(
            teacher=self.request.user, status=LessonCancellationRequest.PENDING
        ).count()
        context['approved_count'] = LessonCancellationRequest.objects.filter(
            teacher=self.request.user, status=LessonCancellationRequest.APPROVED
        ).count()
        context['rejected_count'] = LessonCancellationRequest.objects.filter(
            teacher=self.request.user, status=LessonCancellationRequest.REJECTED
        ).count()
        context['completed_count'] = LessonCancellationRequest.objects.filter(
            teacher=self.request.user, status=LessonCancellationRequest.COMPLETED
        ).count()

        context['status_filter'] = self.request.GET.get('status', 'pending')

        return context


class TeacherRespondToCancellationView(TeacherProfileCompletedMixin, View):
    """Teacher approves or rejects a cancellation request"""

    def post(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id')
        cancellation_request = get_object_or_404(
            LessonCancellationRequest,
            id=request_id,
            teacher=request.user,
            status=LessonCancellationRequest.PENDING
        )

        action = request.POST.get('action')
        teacher_response = request.POST.get('teacher_response', '').strip()

        if action == 'approve':
            cancellation_request.status = LessonCancellationRequest.APPROVED
            cancellation_request.teacher_response = teacher_response
            cancellation_request.teacher_responded_at = timezone.now()
            cancellation_request.save()

            # Process refund if eligible
            if cancellation_request.can_receive_refund and cancellation_request.refund_amount:
                lesson = cancellation_request.lesson

                # Find the StripePayment record for this lesson
                from apps.payments.models import StripePayment
                from apps.payments.stripe_service import create_refund

                try:
                    # Get the order for this lesson
                    order_item = OrderItem.objects.filter(lesson=lesson).select_related('order').first()
                    if order_item and order_item.order.stripe_payment_intent_id:
                        # Get StripePayment record
                        stripe_payment = StripePayment.objects.get(
                            stripe_payment_intent_id=order_item.order.stripe_payment_intent_id
                        )

                        # Create Stripe refund (partial refund - lesson fee minus platform fee)
                        refund_metadata = {
                            'cancellation_request_id': str(cancellation_request.id),
                            'lesson_id': str(lesson.id),
                            'student_id': str(cancellation_request.student.id),
                            'teacher_id': str(cancellation_request.teacher.id),
                            'refund_type': 'cancellation',
                        }

                        refund = create_refund(
                            payment_intent_id=stripe_payment.stripe_payment_intent_id,
                            amount=cancellation_request.refund_amount,
                            reason='requested_by_customer',
                            metadata=refund_metadata
                        )

                        # Mark cancellation as completed
                        cancellation_request.status = LessonCancellationRequest.COMPLETED
                        cancellation_request.refund_processed_at = timezone.now()
                        cancellation_request.save()

                        # Soft delete the lesson
                        if cancellation_request.request_type == LessonCancellationRequest.CANCEL_WITH_REFUND:
                            lesson.is_deleted = True
                            lesson.save()

                        messages.success(request, f'Cancellation approved and refund of £{cancellation_request.refund_amount} processed successfully.')

                    else:
                        messages.warning(request, 'Cancellation approved but payment record not found. Please process refund manually.')

                except StripePayment.DoesNotExist:
                    messages.warning(request, 'Cancellation approved but payment record not found. Please process refund manually.')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing refund: {e}")
                    messages.error(request, f'Cancellation approved but refund failed: {str(e)}. Please process manually in Stripe.')
            else:
                # Not eligible for refund or reschedule request
                messages.success(request, 'Cancellation/reschedule request approved.')

            # Send notification to student
            if cancellation_request.student and cancellation_request.student.email:
                try:
                    StudentNotificationService.send_cancellation_approved_notification(
                        cancellation_request=cancellation_request,
                        lesson=cancellation_request.lesson
                    )
                except Exception as e:
                    print(f"Error sending cancellation approval email: {e}")

        elif action == 'reject':
            cancellation_request.status = LessonCancellationRequest.REJECTED
            cancellation_request.teacher_response = teacher_response
            cancellation_request.teacher_responded_at = timezone.now()
            cancellation_request.save()

            # Send notification to student
            if cancellation_request.student and cancellation_request.student.email:
                try:
                    StudentNotificationService.send_cancellation_rejected_notification(
                        cancellation_request=cancellation_request,
                        lesson=cancellation_request.lesson
                    )
                except Exception as e:
                    print(f"Error sending cancellation rejection email: {e}")

            messages.info(request, 'Cancellation request rejected.')
        else:
            messages.error(request, 'Invalid action.')

        return redirect('private_teaching:teacher_cancellation_requests')