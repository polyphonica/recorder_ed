from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, ListView, View, UpdateView, DeleteView
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
from .models import (
    LessonRequest, Subject, LessonRequestMessage, Cart, CartItem, Order, OrderItem,
    TeacherStudentApplication, ExamRegistration, ExamPiece, ExamBoard,
    LessonCancellationRequest, PracticeEntry,
    PrivateLessonQuiz, PrivateLessonQuizQuestion, PrivateLessonQuizAnswer,
    PrivateLessonQuizAssignment, PrivateLessonQuizAttempt
)
from .notifications import TeacherNotificationService, StudentNotificationService
from .availability_engine import check_slot_availability
from lessons.models import Lesson, Document, LessonAttachedUrl, LessonAssignment
from .forms import LessonRequestForm, ProfileCompleteForm, StudentSignupForm, StudentLessonFormSet, TeacherProfileCompleteForm, TeacherLessonFormSet, TeacherResponseForm, SubjectForm, ExamRegistrationForm, ExamPieceFormSet, ExamResultsForm, PracticeEntryForm, RescheduleForm
from .quiz_forms import (
    PrivateLessonQuizForm, PrivateLessonQuizQuestionForm, PrivateLessonQuizAnswerFormSet,
    PrivateLessonQuizAssignmentForm
)
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


# ============================================================================
# GENERIC BASE VIEWS FOR CRUD OPERATIONS
# ============================================================================

class PrivateTeachingCreateView(TeacherProfileCompletedMixin, View):
    """
    Generic base view for creating objects (POST-only pattern).

    Subclasses should define:
    - form_class: Form class to use
    - success_message: Message template (use {object_name} placeholder)
    - redirect_url_name: Named URL to redirect to after success

    Optional:
    - get_form_kwargs(): Customize form initialization
    - get_object_name(): Return display name for the created object
    """
    form_class = None
    success_message = '{object_name} created successfully!'
    redirect_url_name = None

    def get_form_kwargs(self):
        """Override to customize form kwargs"""
        return {}

    def get_object_name(self, form):
        """Override to customize the object name in success message"""
        return self.form_class._meta.model._meta.verbose_name

    def post(self, request, *args, **kwargs):
        form_kwargs = {'data': request.POST}
        form_kwargs.update(self.get_form_kwargs())
        form = self.form_class(**form_kwargs)

        if form.is_valid():
            try:
                obj = form.save()
                object_name = self.get_object_name(form)
                messages.success(request, self.success_message.format(object_name=object_name))
            except Exception as e:
                # Handle unique constraint violations gracefully
                if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                    messages.error(
                        request,
                        'An item with this information already exists. Please use different values.'
                    )
                else:
                    # Re-raise unexpected errors
                    raise
        else:
            # Display form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

        return redirect(self.redirect_url_name)


class PrivateTeachingUpdateView(TeacherProfileCompletedMixin, View):
    """
    Generic base view for updating objects (POST-only pattern).

    Subclasses should define:
    - model: Model class
    - form_class: Form class to use
    - success_message: Message template (use {object_name} placeholder)
    - redirect_url_name: Named URL to redirect to after success
    - pk_url_kwarg: URL kwarg name for object ID (default: 'pk')

    Optional:
    - get_queryset(): Customize queryset (e.g., filter by teacher)
    - get_form_kwargs(): Customize form initialization
    - get_object_name(): Return display name for the updated object
    """
    model = None
    form_class = None
    success_message = '{object_name} updated successfully!'
    redirect_url_name = None
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        """Override to add additional filters (e.g., teacher=self.request.user)"""
        return self.model.objects.all()

    def get_object(self):
        """Get the object to update"""
        pk = self.kwargs[self.pk_url_kwarg]
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_form_kwargs(self):
        """Override to customize form kwargs"""
        return {}

    def get_object_name(self, obj):
        """Override to customize the object name in success message"""
        return str(obj)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        form_kwargs = {'data': request.POST, 'instance': obj}
        form_kwargs.update(self.get_form_kwargs())
        form = self.form_class(**form_kwargs)

        if form.is_valid():
            try:
                obj = form.save()
                object_name = self.get_object_name(obj)
                messages.success(request, self.success_message.format(object_name=object_name))
            except Exception as e:
                # Handle unique constraint violations gracefully
                if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                    messages.error(
                        request,
                        'An item with this information already exists. Please use different values.'
                    )
                else:
                    # Re-raise unexpected errors
                    raise
        else:
            # Display form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

        return redirect(self.redirect_url_name)


class PrivateTeachingDeleteView(TeacherProfileCompletedMixin, View):
    """
    Generic base view for deleting objects (POST-only pattern).

    Subclasses should define:
    - model: Model class
    - success_message: Message template (use {object_name} placeholder)
    - redirect_url_name: Named URL to redirect to after success
    - pk_url_kwarg: URL kwarg name for object ID (default: 'pk')

    Optional:
    - get_queryset(): Customize queryset (e.g., filter by teacher)
    - get_object_name(): Return display name for the deleted object
    """
    model = None
    success_message = '{object_name} deleted successfully!'
    redirect_url_name = None
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        """Override to add additional filters (e.g., teacher=self.request.user)"""
        return self.model.objects.all()

    def get_object(self):
        """Get the object to delete"""
        pk = self.kwargs[self.pk_url_kwarg]
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_object_name(self, obj):
        """Override to customize the object name in success message"""
        return str(obj)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        object_name = self.get_object_name(obj)
        obj.delete()
        messages.success(request, self.success_message.format(object_name=object_name))
        return redirect(self.redirect_url_name)


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
            if profile.is_teacher and not profile.profile_completed:
                messages.info(request, 'Please complete your teacher profile to access teaching features.')
                return redirect('private_teaching:teacher_profile_complete')

            # Redirect teachers with completed profiles to their dashboard
            elif profile.is_teacher and profile.profile_completed:
                return redirect('private_teaching:teacher_dashboard')

            # Check if student/guardian needs to complete profile
            # Use getattr for safety in case is_guardian field doesn't exist yet
            is_student = getattr(profile, 'is_student', True)
            is_guardian = getattr(profile, 'is_guardian', False)

            if (is_student or is_guardian) and not profile.profile_completed:
                messages.info(request, 'Please complete your profile to request lessons.')
                return redirect('private_teaching:profile_complete')

            # Redirect students/guardians with accepted teachers to their dashboard
            if (is_student or is_guardian) and profile.profile_completed:
                has_accepted_teacher = TeacherStudentApplication.objects.filter(
                    applicant=request.user,
                    status='accepted'
                ).exists()
                if has_accepted_teacher:
                    return redirect('private_teaching:student_dashboard')

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.all()

        # Get teachers offering private lessons
        from django.contrib.auth.models import User
        context['teachers'] = User.objects.filter(
            profile__is_teacher=True,
            profile__profile_completed=True
        ).select_related('profile')[:6]  # Limit to 6 teachers

        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            context['user_profile'] = self.request.user.profile
            is_student = self.request.user.profile.is_student
            is_guardian = getattr(self.request.user.profile, 'is_guardian', False)
            if (is_student or is_guardian) and self.request.user.profile.profile_completed:
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


class RedirectToMyTeachersView(View):
    """
    Redirect old request_lesson URL to new my_teachers page.
    Maintains backward compatibility for bookmarks and links.
    """
    def get(self, request, *args, **kwargs):
        return redirect('private_teaching:my_teachers', permanent=True)


class MyLessonRequestsView(UserFilterMixin, StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """View for students to see their lesson requests. Uses UserFilterMixin."""
    model = LessonRequest
    template_name = 'private_teaching/my_requests.html'
    context_object_name = 'lesson_requests'
    paginate_by = 10
    user_field_name = 'student'

    def get_queryset(self):
        from django.db.models import Count, Q
        # UserFilterMixin automatically filters by student=self.request.user
        # Add count of eligible lessons (accepted and unpaid) to each request
        queryset = super().get_queryset().prefetch_related('messages', 'lessons__subject').annotate(
            eligible_lessons_count=Count(
                'lessons',
                filter=Q(
                    lessons__approved_status='Accepted',
                    lessons__payment_status='Not Paid',
                    lessons__is_deleted=False
                )
            ),
            total_active_lessons=Count(
                'lessons',
                filter=Q(lessons__is_deleted=False)
            )
        ).order_by('-created_at')

        # Exclude requests with no active lessons
        return queryset.exclude(total_active_lessons=0)


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
        lessons = lesson_request.lessons.filter(is_deleted=False).select_related('subject')

        # Count eligible lessons (accepted and unpaid)
        eligible_lessons_count = lessons.filter(
            approved_status='Accepted',
            payment_status='Not Paid'
        ).count()

        context.update({
            'lesson_request': lesson_request,
            'lessons': lessons,
            'conversation_messages': lesson_request.messages.select_related('author').order_by('created_at'),
            'eligible_lessons_count': eligible_lessons_count,
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


@login_required
def delete_lesson_from_request(request, lesson_id):
    """Student deletes a lesson from their request (if not paid)"""
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        student=request.user
    )

    # Only allow deleting lessons that haven't been paid
    if lesson.payment_status == 'Paid':
        messages.error(request, 'Cannot delete a lesson that has already been paid for.')
        return redirect('private_teaching:student_request_detail', request_id=lesson.lesson_request.id)

    lesson_request = lesson.lesson_request

    # Check if this is the last active lesson in the request
    active_lessons_count = lesson_request.lessons.filter(is_deleted=False).count()

    if active_lessons_count == 1:
        # This is the last lesson - delete the entire request
        lesson_request_id = lesson_request.id
        # First delete all lessons (both active and soft-deleted)
        lesson_request.lessons.all().delete()
        # Then delete the request
        lesson_request.delete()
        messages.success(request, 'Lesson request deleted successfully (it was the last lesson in the request).')
        return redirect('private_teaching:my_requests')
    else:
        # Soft delete the lesson
        lesson.is_deleted = True
        lesson.save()
        messages.success(request, f'Lesson on {lesson.lesson_date} deleted successfully.')
        return redirect('private_teaching:student_request_detail', request_id=lesson_request.id)


# ==========================================
# PHASE 2: TEACHER AND STUDENT DASHBOARDS
# ==========================================

class TeacherOnlyMixin:
    """Mixin to restrict access to private teachers only"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('private_teaching:login')
        if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
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

        # Get waitlist applications
        waitlist_applications = TeacherStudentApplication.objects.filter(
            teacher=self.request.user,
            status='waitlist'
        ).select_related('applicant', 'child_profile').order_by('created_at')

        # Get lesson requests for this teacher's subjects with pending lessons
        # PERFORMANCE FIX: Use direct join instead of subquery
        from django.db.models import Prefetch, Q
        pending_requests = LessonRequest.objects.filter(
            lessons__subject__teacher=self.request.user,
            lessons__approved_status='Pending'
        ).distinct().select_related('student', 'child_profile').prefetch_related(
            Prefetch('lessons',
                     queryset=Lesson.objects.select_related('subject').filter(approved_status='Pending'))
        )

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

        # Get paid lessons waiting to be assigned (payment_status='Paid' and status='Draft')
        # These are lessons that have been paid for but the teacher hasn't scheduled them yet
        paid_unassigned_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            payment_status='Paid',
            status='Draft',
            is_deleted=False
        ).select_related('student', 'subject', 'lesson_request', 'lesson_request__child_profile').order_by('created_at')

        # Active exam registrations (REGISTERED or SUBMITTED, not yet RESULTS_RECEIVED)
        active_exams = ExamRegistration.objects.filter(
            teacher=self.request.user,
            status__in=[ExamRegistration.REGISTERED, ExamRegistration.SUBMITTED]
        ).count()

        # Get pending cancellation requests from students
        pending_cancellations = LessonCancellationRequest.objects.filter(
            teacher=self.request.user,
            status='pending'
        ).select_related('student', 'lesson', 'lesson__subject').order_by('-created_at')

        # Get assignment stats
        from assignments.models import Assignment, AssignmentSubmission
        my_assignments_count = Assignment.objects.filter(created_by=self.request.user, is_active=True).count()
        pending_assignment_submissions_count = AssignmentSubmission.objects.filter(
            assignment__created_by=self.request.user,
            status='submitted'
        ).count()

        # Get quiz stats
        my_quizzes_count = PrivateLessonQuiz.objects.filter(created_by=self.request.user).count()
        quiz_assignments_pending = PrivateLessonQuizAssignment.objects.filter(
            teacher=self.request.user,
            status='assigned'
        ).count()

        context.update({
            'pending_applications': pending_applications,
            'pending_applications_count': pending_applications.count(),
            'waitlist_applications': waitlist_applications,
            'waitlist_applications_count': waitlist_applications.count(),
            'pending_requests': pending_requests,
            'pending_count': pending_requests.count(),
            'today_lessons': today_lessons,
            'upcoming_lessons': upcoming_lessons,
            'paid_unassigned_lessons': paid_unassigned_lessons,
            'paid_unassigned_count': paid_unassigned_lessons.count(),
            'active_exams_count': active_exams,
            'pending_cancellations': pending_cancellations,
            'pending_cancellations_count': pending_cancellations.count(),
            'my_assignments_count': my_assignments_count,
            'pending_assignment_submissions_count': pending_assignment_submissions_count,
            'my_quizzes_count': my_quizzes_count,
            'quiz_assignments_pending': quiz_assignments_pending,
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

        # Get upcoming exams (REGISTERED or SUBMITTED, with upcoming or flexible dates)
        from django.db.models import Q
        upcoming_exams = ExamRegistration.objects.filter(
            student=self.request.user,
            status__in=[ExamRegistration.REGISTERED, ExamRegistration.SUBMITTED]
        ).filter(
            Q(exam_date__gte=today) | Q(exam_date__isnull=True)
        ).select_related('subject', 'exam_board').order_by('exam_date')

        # Get pending assignments (draft or not yet submitted)
        from assignments.models import AssignmentSubmission

        # Get all lessons for this student
        student_lessons = Lesson.objects.filter(
            student=self.request.user,
            status='Assigned'
        )

        # Get all assignment links from these lessons
        lesson_ids = student_lessons.values_list('id', flat=True)
        assignment_links = LessonAssignment.objects.filter(
            lesson_id__in=lesson_ids
        )

        # Count pending assignments (not submitted or in draft status)
        pending_assignments_count = 0
        for link in assignment_links:
            try:
                submission = AssignmentSubmission.objects.get(
                    student=self.request.user,
                    assignment=link.assignment
                )
                if not submission or submission.status == 'draft':
                    pending_assignments_count += 1
            except AssignmentSubmission.DoesNotExist:
                pending_assignments_count += 1

        # Get quiz stats
        pending_quizzes = PrivateLessonQuizAssignment.objects.filter(
            student=self.request.user,
            status='assigned'
        ).count()
        completed_quizzes = PrivateLessonQuizAssignment.objects.filter(
            student=self.request.user,
            status='completed'
        ).count()

        context.update({
            'my_applications': my_applications,
            'pending_applications': pending_applications,
            'accepted_applications': accepted_applications,
            'waitlist_applications': waitlist_applications,
            'declined_applications': declined_applications,
            'recent_requests': recent_requests,
            'upcoming_lessons': upcoming_lessons,
            'awaiting_payment': awaiting_payment,
            'upcoming_exams': upcoming_exams,
            'pending_assignments_count': pending_assignments_count,
            'pending_quizzes': pending_quizzes,
            'completed_quizzes': completed_quizzes,
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
        # PERFORMANCE FIX: Optimize prefetch with Prefetch object to limit messages
        from lessons.models import Lesson
        from django.db.models import Prefetch

        teacher_lesson_requests = LessonRequest.objects.filter(
            lessons__teacher=self.request.user,
            lessons__is_deleted=False
        ).distinct().select_related('child_profile', 'student').prefetch_related(
            Prefetch('lessons',
                     queryset=Lesson.objects.filter(
                         is_deleted=False, teacher=self.request.user
                     ).select_related('subject')),
            'messages'  # Prefetch all messages (pagination handles limiting display)
        ).order_by('-created_at')

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


class MyLessonsView(UserFilterMixin, StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """Student view of their approved/scheduled lessons. Uses UserFilterMixin."""
    model = Lesson
    template_name = 'private_teaching/my_lessons.html'
    context_object_name = 'lessons'
    paginate_by = 10
    user_field_name = 'student'

    def get_queryset(self):
        # UserFilterMixin automatically filters by student=self.request.user
        return super().get_queryset().filter(
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
            is_teacher = self.request.user.profile.is_teacher
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
            if lesson.payment_status == 'Paid':
                color = '#10b981'  # Green for paid lessons
            elif lesson.approved_status == 'Accepted':
                color = '#f59e0b'  # Yellow/amber for approved but not paid
            elif lesson.approved_status == 'Rejected':
                color = '#ef4444'  # Red for rejected
            else:
                color = '#9ca3af'  # Gray for pending/draft

            text_color = 'white'

            # Get subject name safely
            subject_name = lesson.subject.subject if lesson.subject else 'Unknown Subject'

            # Get student name - use child's name if lesson is for a child
            student_display_name = lesson.lesson_request.student_display_name if lesson.lesson_request else (
                lesson.student.get_full_name() if lesson.student else 'Unknown'
            )

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


class SubjectCreateView(PrivateTeachingCreateView):
    """Create new subject for teacher"""
    form_class = SubjectForm
    redirect_url_name = 'private_teaching:teacher_settings'

    def get_form_kwargs(self):
        return {'teacher': self.request.user}

    def get_object_name(self, form):
        return f'Subject "{form.cleaned_data["subject"]}"'


class SubjectUpdateView(PrivateTeachingUpdateView):
    """Update existing subject for teacher"""
    model = Subject
    form_class = SubjectForm
    redirect_url_name = 'private_teaching:teacher_settings'
    pk_url_kwarg = 'subject_id'

    def get_queryset(self):
        return Subject.objects.filter(teacher=self.request.user)

    def get_form_kwargs(self):
        return {'teacher': self.request.user}

    def get_object_name(self, obj):
        return f'Subject "{obj.subject}"'


class SubjectReorderView(TeacherProfileCompletedMixin, View):
    """Reorder subjects via AJAX"""

    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            subject_ids = data.get('subject_ids', [])

            # Update display_order for each subject
            for index, subject_id in enumerate(subject_ids):
                Subject.objects.filter(
                    id=subject_id,
                    teacher=request.user
                ).update(display_order=index)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class SubjectDeleteView(PrivateTeachingDeleteView):
    """Delete subject for teacher"""
    model = Subject
    redirect_url_name = 'private_teaching:teacher_settings'
    pk_url_kwarg = 'subject_id'

    def get_queryset(self):
        return Subject.objects.filter(teacher=self.request.user)

    def get_object_name(self, obj):
        return f'Subject "{obj.subject}"'


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


class TeacherAvailabilityEditorView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher availability calendar editor"""
    template_name = 'private_teaching/teacher_availability_editor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # All data will be loaded via API, but we pass the user ID for API calls
        context['teacher_id'] = self.request.user.id
        return context


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

        # Only display message if one is provided
        if message:
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
            if hasattr(request.user, 'profile') and request.user.profile.is_teacher:
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
            if lesson.lesson_request:
                student_name = lesson.lesson_request.student_display_name
                guardian_name = lesson.lesson_request.guardian_name
            else:
                student_name = lesson.student.get_full_name() if lesson.student else 'Unknown'
                guardian_name = None

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
                'guardian': guardian_name,
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
        # Build list of students with proper display names (showing child names, not guardian names)
        lessons_for_students = Lesson.objects.filter(
            teacher=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).select_related('student__profile', 'lesson_request__child_profile').order_by('student').distinct('student')

        students_list = []
        seen_students = set()

        for lesson in lessons_for_students:
            student_id = lesson.student.id
            if student_id not in seen_students:
                seen_students.add(student_id)
                # Check if this is a child profile lesson
                if lesson.lesson_request and lesson.lesson_request.is_child_lesson:
                    # Show child's name with guardian in parentheses
                    display_name = lesson.lesson_request.student_display_name
                    guardian_name = lesson.lesson_request.guardian_name
                    full_display = f"{display_name} ({guardian_name})"
                else:
                    # Show adult student's name
                    display_name = f"{lesson.student.profile.first_name} {lesson.student.profile.last_name}" if hasattr(lesson.student, 'profile') else lesson.student.get_full_name()
                    full_display = display_name

                students_list.append({
                    'id': student_id,
                    'name': full_display,
                    'sort_key': display_name.lower()
                })

        # Sort by the actual student/child name
        students_list.sort(key=lambda x: x['sort_key'])
        students = students_list

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
        from apps.accounts.models import ChildProfile

        student_data = []
        for student in context['students']:
            lessons = Lesson.objects.filter(
                teacher=self.request.user,
                student=student,
                approved_status='Accepted',
                is_deleted=False
            ).select_related('subject', 'lesson_request', 'lesson_request__child_profile')

            # Get unique subjects for this student
            subjects = Subject.objects.filter(
                teacher=self.request.user,
                lesson__student=student,
                lesson__approved_status='Accepted',
                lesson__is_deleted=False
            ).distinct()

            # Check if any lessons are for a child
            # Get all unique child profiles for this guardian
            child_profiles = []
            for lesson in lessons:
                if lesson.lesson_request and lesson.lesson_request.child_profile:
                    child_profile = lesson.lesson_request.child_profile
                    if child_profile not in child_profiles:
                        child_profiles.append(child_profile)

            student_data.append({
                'user': student,
                'total_lessons': lessons.count(),
                'subjects': subjects,
                'child_profiles': child_profiles,  # List of children this guardian has lessons for
                'is_guardian': len(child_profiles) > 0,
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
        teacher = get_object_or_404(User, id=teacher_id, profile__is_teacher=True)

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
        teacher = get_object_or_404(User, id=teacher_id, profile__is_teacher=True)

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

        student_name = application.student_name
        messages.success(request, f'Application submitted for {student_name}!')
        return redirect('private_teaching:student_application_detail', application_id=application.id)


class StudentApplicationsListView(UserFilterMixin, StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """List all applications for the student. Uses UserFilterMixin."""
    model = TeacherStudentApplication
    template_name = 'private_teaching/student_applications_list.html'
    context_object_name = 'applications'
    paginate_by = 10
    user_field_name = 'applicant'

    def get_queryset(self):
        # UserFilterMixin automatically filters by applicant=self.request.user
        return super().get_queryset().select_related('teacher', 'teacher__profile', 'child_profile').order_by('-created_at')


class MyTeachersView(UserFilterMixin, StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """
    List teachers who have accepted the student.
    Students can book lessons only with accepted teachers.
    """
    model = TeacherStudentApplication
    template_name = 'private_teaching/my_teachers.html'
    context_object_name = 'accepted_applications'
    user_field_name = 'applicant'

    def get_queryset(self):
        # Get only accepted applications
        return super().get_queryset().filter(
            status='accepted'
        ).select_related(
            'teacher',
            'teacher__profile',
            'child_profile'
        ).prefetch_related(
            'teacher__subjects'  # Prefetch teacher's subjects to show what they teach
        ).order_by('teacher__first_name', 'teacher__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Also get pending/declined applications for status display
        all_applications = TeacherStudentApplication.objects.filter(
            applicant=self.request.user
        ).exclude(
            status='accepted'
        ).select_related('teacher', 'teacher__profile')

        context['other_applications'] = all_applications
        context['has_accepted_teachers'] = self.get_queryset().exists()

        return context


class BookWithTeacherView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """
    Teacher-specific lesson booking page.
    Students can only book with teachers who have accepted them.
    Filters subjects to only show that teacher's subjects.
    """
    template_name = 'private_teaching/book_with_teacher.html'

    def dispatch(self, request, *args, **kwargs):
        """Check if student has accepted application with this teacher"""
        teacher_id = kwargs.get('teacher_id')
        teacher = get_object_or_404(User, id=teacher_id, profile__is_teacher=True)

        # Check for accepted application
        accepted_application = TeacherStudentApplication.objects.filter(
            applicant=request.user,
            teacher=teacher,
            status='accepted'
        ).first()

        if not accepted_application:
            messages.error(
                request,
                f'You need to be accepted by {teacher.get_full_name()} before you can book lessons. '
                f'Please apply first or wait for your application to be accepted.'
            )
            return redirect('private_teaching:my_teachers')

        # Store teacher and application for use in get/post
        self.teacher = teacher
        self.accepted_application = accepted_application

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['teacher'] = self.teacher
        context['application'] = self.accepted_application
        context['form'] = LessonRequestForm(user=self.request.user)
        context['formset'] = StudentLessonFormSet(form_kwargs={'teacher': self.teacher})
        # IMPORTANT: Only show this teacher's subjects
        context['subjects'] = Subject.objects.filter(
            teacher=self.teacher,
            is_active=True
        )

        # Check if teacher has availability calendar enabled
        context['calendar_enabled'] = (
            hasattr(self.teacher, 'availability_settings') and
            self.teacher.availability_settings.use_availability_calendar
        )

        return context

    def post(self, request, *args, **kwargs):
        form = LessonRequestForm(request.POST, user=request.user)
        formset = StudentLessonFormSet(request.POST, form_kwargs={'teacher': self.teacher})

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
                        return self.render_to_response(self.get_context_data(
                            form=form,
                            formset=formset
                        ))

            lesson_request.save()

            # Save the lessons - all should be with this teacher
            lessons = formset.save(commit=False)
            for lesson in lessons:
                lesson.lesson_request = lesson_request
                lesson.student = request.user
                # Verify subject belongs to this teacher
                if lesson.subject and lesson.subject.teacher != self.teacher:
                    messages.error(
                        request,
                        f'Subject "{lesson.subject}" does not belong to {self.teacher.get_full_name()}. '
                        f'Please select only subjects taught by this teacher.'
                    )
                    lesson_request.delete()
                    return self.render_to_response(self.get_context_data(
                        form=form,
                        formset=formset
                    ))
                # Teacher will be auto-populated from subject in Lesson.save()
                lesson.save()

            # Handle deleted lessons
            for lesson in formset.deleted_objects:
                lesson.delete()

            # Create initial message if provided
            initial_message = request.POST.get('initial_message', '').strip()
            if initial_message:
                LessonRequestMessage.objects.create(
                    lesson_request=lesson_request,
                    author=request.user,
                    message=initial_message
                )

            # Send email notification to THIS teacher only
            try:
                TeacherNotificationService.send_new_lesson_request_notification(
                    lesson_request=lesson_request,
                    lessons=lessons,
                    teacher=self.teacher
                )
            except Exception as e:
                # Log error but don't fail the request
                print(f"Error sending notification email to teacher: {e}")

            lesson_count = len(lessons)
            student_name = lesson_request.student_name
            messages.success(
                request,
                f'Lesson request for {student_name} with {self.teacher.get_full_name()} submitted successfully '
                f'with {lesson_count} lesson{"s" if lesson_count != 1 else ""}! The teacher will respond soon.'
            )
            return redirect('private_teaching:my_requests')

        # If form invalid, re-render with errors
        return self.render_to_response(self.get_context_data(
            form=form,
            formset=formset
        ))


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

        # PERFORMANCE FIX: Consolidate 4 count queries into 1 aggregate
        from django.db.models import Count, Q
        status_counts = TeacherStudentApplication.objects.filter(
            teacher=self.request.user
        ).aggregate(
            pending=Count('id', filter=Q(status='pending')),
            accepted=Count('id', filter=Q(status='accepted')),
            waitlist=Count('id', filter=Q(status='waitlist')),
            declined=Count('id', filter=Q(status='declined'))
        )
        context['pending_count'] = status_counts['pending']
        context['accepted_count'] = status_counts['accepted']
        context['waitlist_count'] = status_counts['waitlist']
        context['declined_count'] = status_counts['declined']

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

        # Create Stripe checkout session using centralized service
        from apps.payments.stripe_service import create_checkout_session

        try:
            # Build URLs
            success_url = request.build_absolute_uri(
                reverse('private_teaching:exam_payment_success', kwargs={'pk': exam.id})
            )
            cancel_url = request.build_absolute_uri(
                reverse('private_teaching:exam_payment_cancel', kwargs={'pk': exam.id})
            )

            # Prepare metadata
            metadata = {
                'exam_id': str(exam.id),
                'student_id': str(exam.student.id),
                'teacher_id': str(exam.teacher.id),
            }

            # Create checkout session
            checkout_session = create_checkout_session(
                amount=exam.fee_amount,
                student=exam.student,
                teacher=exam.teacher,
                domain='private_teaching',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
                item_name=f'Exam Registration: {exam.display_name}',
                item_description=f'{exam.student_name} - {exam.exam_board} {exam.get_grade_type_display()} Grade {exam.grade_level}'
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
# PRACTICE DIARY VIEWS
# ============================================================================

class LogPracticeView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """Student logs a new practice session"""
    template_name = 'private_teaching/practice/log_practice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PracticeEntryForm(user=self.request.user)

        # Get teacher options for this student
        # Find teachers student has lessons with
        teacher_ids = Lesson.objects.filter(
            student=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).values_list('teacher__id', flat=True).distinct()

        context['teachers'] = User.objects.filter(id__in=teacher_ids).select_related('profile')

        return context

    def post(self, request, *args, **kwargs):
        form = PracticeEntryForm(request.POST, user=request.user)

        if form.is_valid():
            practice_entry = form.save(commit=False)
            practice_entry.student = request.user

            # Get selected teacher
            teacher_id = request.POST.get('teacher')
            if teacher_id:
                try:
                    teacher = User.objects.get(id=teacher_id)
                    # Verify student has lessons with this teacher
                    has_lessons = Lesson.objects.filter(
                        student=request.user,
                        teacher=teacher,
                        approved_status='Accepted',
                        is_deleted=False
                    ).exists()

                    if has_lessons:
                        practice_entry.teacher = teacher
                    else:
                        messages.error(request, 'Invalid teacher selected.')
                        return render(request, self.template_name, {
                            'form': form,
                            'teachers': User.objects.filter(
                                id__in=Lesson.objects.filter(
                                    student=request.user,
                                    approved_status='Accepted',
                                    is_deleted=False
                                ).values_list('teacher__id', flat=True).distinct()
                            ).select_related('profile')
                        })
                except User.DoesNotExist:
                    messages.error(request, 'Teacher not found.')
                    return render(request, self.template_name, {
                        'form': form,
                        'teachers': User.objects.filter(
                            id__in=Lesson.objects.filter(
                                student=request.user,
                                approved_status='Accepted',
                                is_deleted=False
                            ).values_list('teacher__id', flat=True).distinct()
                        ).select_related('profile')
                    })

            practice_entry.save()

            # Show success message emphasizing exam/performance prep if applicable
            success_msg = 'Practice session logged successfully!'
            if practice_entry.preparing_for_exam:
                success_msg += ' Keep up the great exam preparation work!'
            elif practice_entry.preparing_for_performance:
                success_msg += ' Excellent performance preparation!'

            messages.success(request, success_msg)
            return redirect('private_teaching:practice_log')

        return render(request, self.template_name, {
            'form': form,
            'teachers': User.objects.filter(
                id__in=Lesson.objects.filter(
                    student=request.user,
                    approved_status='Accepted',
                    is_deleted=False
                ).values_list('teacher__id', flat=True).distinct()
            ).select_related('profile')
        })


class PracticeLogView(StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """Student views their practice log history with statistics"""
    model = PracticeEntry
    template_name = 'private_teaching/practice/practice_log.html'
    context_object_name = 'practice_entries'
    paginate_by = 20

    def get_queryset(self):
        queryset = PracticeEntry.objects.filter(
            student=self.request.user
        ).select_related('teacher', 'teacher__profile', 'child_profile', 'lesson_request').order_by('-practice_date', '-created_at')

        # Filter by child if guardian
        child_id = self.request.GET.get('child')
        if child_id:
            queryset = queryset.filter(child_profile__id=child_id)

        # Filter by teacher
        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher__id=teacher_id)

        # Filter by exam prep
        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            queryset = queryset.filter(preparing_for_exam=True)

        # Filter by performance prep
        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            queryset = queryset.filter(preparing_for_performance=True)

        # Filter by date range
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(practice_date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(practice_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import timedelta
        from django.db.models import Sum, Avg, Count

        # Get all practice entries for stats (not filtered by pagination)
        all_entries = PracticeEntry.objects.filter(student=self.request.user)

        # Apply same filters as queryset
        child_id = self.request.GET.get('child')
        if child_id:
            all_entries = all_entries.filter(child_profile__id=child_id)

        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            all_entries = all_entries.filter(teacher__id=teacher_id)

        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            all_entries = all_entries.filter(preparing_for_exam=True)

        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            all_entries = all_entries.filter(preparing_for_performance=True)

        # Apply date range filters
        start_date = self.request.GET.get('start_date')
        if start_date:
            all_entries = all_entries.filter(practice_date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            all_entries = all_entries.filter(practice_date__lte=end_date)

        # Calculate statistics
        stats = all_entries.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes'),
            avg_enjoyment=Avg('enjoyment_rating')
        )

        # Calculate last 7 days stats
        from datetime import date
        seven_days_ago = date.today() - timedelta(days=7)
        last_week_entries = all_entries.filter(practice_date__gte=seven_days_ago)
        last_week_stats = last_week_entries.aggregate(
            sessions=Count('id'),
            minutes=Sum('duration_minutes')
        )

        # PERFORMANCE FIX: Consolidate 2 count queries into 1 aggregate
        prep_counts = all_entries.aggregate(
            exam_prep=Count('id', filter=Q(preparing_for_exam=True)),
            performance_prep=Count('id', filter=Q(preparing_for_performance=True))
        )
        exam_prep_count = prep_counts['exam_prep']
        performance_prep_count = prep_counts['performance_prep']

        context.update({
            'total_sessions': stats['total_sessions'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'total_hours': round((stats['total_minutes'] or 0) / 60, 1),
            'avg_duration': round(stats['avg_duration'] or 0),
            'avg_enjoyment': round(stats['avg_enjoyment'] or 0, 1) if stats['avg_enjoyment'] else None,
            'last_week_sessions': last_week_stats['sessions'] or 0,
            'last_week_minutes': last_week_stats['minutes'] or 0,
            'last_week_hours': round((last_week_stats['minutes'] or 0) / 60, 1),
            'exam_prep_count': exam_prep_count,
            'performance_prep_count': performance_prep_count,
        })

        # Get filter options
        if self.request.user.profile.is_guardian:
            from apps.accounts.models import ChildProfile
            context['children'] = ChildProfile.objects.filter(guardian=self.request.user)

        teacher_ids = PracticeEntry.objects.filter(
            student=self.request.user
        ).values_list('teacher__id', flat=True).distinct()
        context['teachers'] = User.objects.filter(id__in=teacher_ids).select_related('profile')

        # Pass current filters
        context['child_filter'] = child_id
        context['teacher_filter'] = teacher_id
        context['exam_prep_filter'] = exam_prep
        context['performance_prep_filter'] = performance_prep
        context['start_date_filter'] = start_date
        context['end_date_filter'] = end_date

        return context


class PracticeLogPrintView(StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """Print-friendly view of practice log with all entries (no pagination)"""
    model = PracticeEntry
    template_name = 'private_teaching/practice/practice_log_print.html'
    context_object_name = 'practice_entries'
    # No pagination - show all filtered entries

    def get_queryset(self):
        queryset = PracticeEntry.objects.filter(
            student=self.request.user
        ).select_related('teacher', 'teacher__profile', 'child_profile', 'lesson_request').order_by('-practice_date', '-created_at')

        # Filter by child if guardian
        child_id = self.request.GET.get('child')
        if child_id:
            queryset = queryset.filter(child_profile__id=child_id)

        # Filter by teacher
        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher__id=teacher_id)

        # Filter by exam prep
        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            queryset = queryset.filter(preparing_for_exam=True)

        # Filter by performance prep
        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            queryset = queryset.filter(preparing_for_performance=True)

        # Filter by date range
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(practice_date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(practice_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import timedelta
        from django.db.models import Sum, Avg, Count

        # Get all practice entries for stats (same as filtered queryset)
        all_entries = self.get_queryset()

        # Calculate statistics
        stats = all_entries.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes'),
            avg_enjoyment=Avg('enjoyment_rating')
        )

        # PERFORMANCE FIX: Consolidate 2 count queries into 1 aggregate
        prep_counts = all_entries.aggregate(
            exam_prep=Count('id', filter=Q(preparing_for_exam=True)),
            performance_prep=Count('id', filter=Q(preparing_for_performance=True))
        )
        exam_prep_count = prep_counts['exam_prep']
        performance_prep_count = prep_counts['performance_prep']

        context.update({
            'total_sessions': stats['total_sessions'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'total_hours': round((stats['total_minutes'] or 0) / 60, 1),
            'avg_duration': round(stats['avg_duration'] or 0),
            'avg_enjoyment': round(stats['avg_enjoyment'] or 0, 1) if stats['avg_enjoyment'] else None,
            'exam_prep_count': exam_prep_count,
            'performance_prep_count': performance_prep_count,
        })

        # Pass current filters for display
        context['start_date_filter'] = self.request.GET.get('start_date')
        context['end_date_filter'] = self.request.GET.get('end_date')
        context['child_filter'] = self.request.GET.get('child')
        context['teacher_filter'] = self.request.GET.get('teacher')

        # Get child name if filtering by child
        child_id = self.request.GET.get('child')
        if child_id:
            from apps.accounts.models import ChildProfile
            try:
                child = ChildProfile.objects.get(id=child_id, guardian=self.request.user)
                context['child_name'] = child.full_name
            except ChildProfile.DoesNotExist:
                pass

        return context


class TeacherStudentPracticeView(TeacherProfileCompletedMixin, ListView):
    """Teacher views a specific student's practice log"""
    model = PracticeEntry
    template_name = 'private_teaching/practice/teacher_student_practice.html'
    context_object_name = 'practice_entries'
    paginate_by = 20

    def get_student(self):
        """Get the student whose practice log is being viewed"""
        student_id = self.kwargs.get('student_id')
        student = get_object_or_404(User, id=student_id)

        # Verify teacher has lessons with this student
        has_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            student=student,
            approved_status='Accepted',
            is_deleted=False
        ).exists()

        if not has_lessons:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this student's practice log.")

        return student

    def get_queryset(self):
        student = self.get_student()

        queryset = PracticeEntry.objects.filter(
            student=student,
            teacher=self.request.user
        ).select_related('child_profile', 'lesson_request').order_by('-practice_date', '-created_at')

        # Filter by exam prep
        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            queryset = queryset.filter(preparing_for_exam=True)

        # Filter by performance prep
        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            queryset = queryset.filter(preparing_for_performance=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import timedelta
        from django.db.models import Sum, Avg, Count

        student = self.get_student()
        context['viewed_student'] = student

        # Check if this is a child student by looking at practice entries
        # If all practice entries have a child_profile, get the child info
        practice_entries = PracticeEntry.objects.filter(
            student=student,
            teacher=self.request.user
        ).select_related('child_profile')

        # Get unique child profiles from practice entries
        child_profiles = set()
        for entry in practice_entries:
            if entry.child_profile:
                child_profiles.add(entry.child_profile)

        # If there's only one child profile, use that as the display name
        if len(child_profiles) == 1:
            context['child_profile'] = list(child_profiles)[0]
            context['is_child_student'] = True
        else:
            context['is_child_student'] = False

        # Get all practice entries for stats
        all_entries = PracticeEntry.objects.filter(
            student=student,
            teacher=self.request.user
        )

        # Apply same filters as queryset
        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            all_entries = all_entries.filter(preparing_for_exam=True)

        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            all_entries = all_entries.filter(preparing_for_performance=True)

        # Calculate statistics
        stats = all_entries.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes'),
            avg_enjoyment=Avg('enjoyment_rating')
        )

        # Calculate last 7 days stats
        from datetime import date
        seven_days_ago = date.today() - timedelta(days=7)
        last_week_entries = all_entries.filter(practice_date__gte=seven_days_ago)
        last_week_stats = last_week_entries.aggregate(
            sessions=Count('id'),
            minutes=Sum('duration_minutes')
        )

        # PERFORMANCE FIX: Consolidate 2 count queries into 1 aggregate
        prep_counts = all_entries.aggregate(
            exam_prep=Count('id', filter=Q(preparing_for_exam=True)),
            performance_prep=Count('id', filter=Q(preparing_for_performance=True))
        )
        exam_prep_count = prep_counts['exam_prep']
        performance_prep_count = prep_counts['performance_prep']

        # Mark entries as viewed by teacher
        PracticeEntry.objects.filter(
            student=student,
            teacher=self.request.user,
            teacher_viewed_at__isnull=True
        ).update(teacher_viewed_at=timezone.now())

        context.update({
            'total_sessions': stats['total_sessions'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'total_hours': round((stats['total_minutes'] or 0) / 60, 1),
            'avg_duration': round(stats['avg_duration'] or 0),
            'avg_enjoyment': round(stats['avg_enjoyment'] or 0, 1) if stats['avg_enjoyment'] else None,
            'last_week_sessions': last_week_stats['sessions'] or 0,
            'last_week_minutes': last_week_stats['minutes'] or 0,
            'last_week_hours': round((last_week_stats['minutes'] or 0) / 60, 1),
            'exam_prep_count': exam_prep_count,
            'performance_prep_count': performance_prep_count,
        })

        # Pass current filters
        context['exam_prep_filter'] = exam_prep
        context['performance_prep_filter'] = performance_prep

        return context


class AddPracticeCommentView(TeacherProfileCompletedMixin, View):
    """Teacher adds comment to a practice entry"""

    def post(self, request, *args, **kwargs):
        entry_id = kwargs.get('entry_id')
        practice_entry = get_object_or_404(
            PracticeEntry,
            id=entry_id,
            teacher=request.user
        )

        teacher_comment = request.POST.get('teacher_comment', '').strip()

        if teacher_comment:
            practice_entry.teacher_comment = teacher_comment
            practice_entry.teacher_viewed_at = timezone.now()
            practice_entry.save(update_fields=['teacher_comment', 'teacher_viewed_at'])
            messages.success(request, 'Comment added successfully!')
        else:
            messages.error(request, 'Comment cannot be empty.')

        return redirect('private_teaching:teacher_student_practice', student_id=practice_entry.student.id)


class EditPracticeView(StudentProfileCompletedMixin, StudentOnlyMixin, UpdateView):
    """Student edits their own practice entry"""
    model = PracticeEntry
    template_name = 'private_teaching/practice/log_practice.html'
    form_class = PracticeEntryForm

    def get_queryset(self):
        # Security: Students can only edit their own entries
        return PracticeEntry.objects.filter(student=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entry'] = self.object
        context['form'] = self.get_form()

        # Get teacher options (same as create)
        teacher_ids = Lesson.objects.filter(
            student=self.request.user,
            approved_status='Accepted',
            is_deleted=False
        ).values_list('teacher__id', flat=True).distinct()

        context['teachers'] = User.objects.filter(id__in=teacher_ids).select_related('profile')
        return context

    def form_valid(self, form):
        # Validate teacher relationship
        teacher = form.cleaned_data.get('teacher')
        if teacher:
            has_lessons = Lesson.objects.filter(
                student=self.request.user,
                teacher=teacher,
                approved_status='Accepted',
                is_deleted=False
            ).exists()

            if not has_lessons:
                form.add_error('teacher', 'You can only log practice for teachers you have accepted lessons with.')
                return self.form_invalid(form)

        messages.success(self.request, 'Practice entry updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('private_teaching:practice_log')


class DeletePracticeView(StudentProfileCompletedMixin, StudentOnlyMixin, DeleteView):
    """Student deletes their own practice entry"""
    model = PracticeEntry

    def get_queryset(self):
        # Security: Students can only delete their own entries
        return PracticeEntry.objects.filter(student=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Practice entry deleted successfully.')
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('private_teaching:practice_log')


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
        cancellation_reason = request.POST.get('cancellation_reason', '').strip() or None  # Optional
        student_message = request.POST.get('student_message', '').strip()  # Optional
        proposed_new_date = request.POST.get('proposed_new_date', '').strip() if request_type == 'reschedule' else None
        proposed_new_time = request.POST.get('proposed_new_time', '').strip() if request_type == 'reschedule' else None

        # Validation - only request_type is required
        if not request_type or request_type not in ['cancel_refund', 'reschedule']:
            messages.error(request, 'Please select a valid request type.')
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


class CancellationRequestDetailView(PrivateTeachingLoginRequiredMixin, View):
    """View details of a cancellation request (for both student and teacher)"""
    template_name = 'private_teaching/cancellation_request_detail.html'

    def get_cancellation_request(self, request_id):
        """Get the cancellation request"""
        cancellation_request = get_object_or_404(LessonCancellationRequest, id=request_id)

        # Check permissions
        if self.request.user not in [cancellation_request.student, cancellation_request.teacher]:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this cancellation request.")

        return cancellation_request

    def get(self, request, *args, **kwargs):
        """Display cancellation request details with reschedule form if applicable"""
        request_id = kwargs.get('request_id')
        cancellation_request = self.get_cancellation_request(request_id)

        is_teacher = request.user == cancellation_request.teacher
        is_reschedule = cancellation_request.request_type == LessonCancellationRequest.RESCHEDULE
        is_pending = cancellation_request.status == LessonCancellationRequest.PENDING

        # Initialize reschedule form for teachers viewing pending reschedule requests
        reschedule_form = None
        if is_teacher and is_reschedule and is_pending:
            reschedule_form = RescheduleForm(
                proposed_date=cancellation_request.proposed_new_date,
                proposed_time=cancellation_request.proposed_new_time
            )

        context = {
            'cancellation_request': cancellation_request,
            'lesson': cancellation_request.lesson,
            'is_teacher': is_teacher,
            'is_student': request.user == cancellation_request.student,
            'reschedule_form': reschedule_form,
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Handle inline reschedule date/time updates"""
        request_id = kwargs.get('request_id')
        cancellation_request = self.get_cancellation_request(request_id)

        # Only teachers can update reschedule dates
        if request.user != cancellation_request.teacher:
            messages.error(request, "You don't have permission to update this request.")
            return redirect('private_teaching:cancellation_request_detail', request_id=request_id)

        # Only for reschedule requests
        if cancellation_request.request_type != LessonCancellationRequest.RESCHEDULE:
            messages.error(request, "This is not a reschedule request.")
            return redirect('private_teaching:cancellation_request_detail', request_id=request_id)

        # Only for pending requests
        if cancellation_request.status != LessonCancellationRequest.PENDING:
            messages.error(request, "This request has already been processed.")
            return redirect('private_teaching:cancellation_request_detail', request_id=request_id)

        reschedule_form = RescheduleForm(request.POST)

        if reschedule_form.is_valid():
            new_date = reschedule_form.cleaned_data['lesson_date']
            new_time = reschedule_form.cleaned_data['lesson_time']
            lesson = cancellation_request.lesson

            # Check for scheduling conflicts
            from datetime import datetime
            slot_datetime = datetime.combine(new_date, new_time)
            is_available, reason = check_slot_availability(
                teacher=cancellation_request.teacher,
                slot_datetime=slot_datetime,
                duration=int(lesson.duration_in_minutes),
                exclude_lesson_id=lesson.id
            )

            if not is_available:
                messages.error(
                    request,
                    f"Cannot reschedule to this time: {reason}"
                )
            else:
                # Update the proposed dates in the cancellation request
                cancellation_request.proposed_new_date = new_date
                cancellation_request.proposed_new_time = new_time
                cancellation_request.save()

                messages.success(request, "Reschedule date/time updated successfully. You can now approve the request.")
        else:
            messages.error(request, "Invalid date or time. Please check your input.")

        return redirect('private_teaching:cancellation_request_detail', request_id=request_id)


class TeacherCancellationRequestsView(UserFilterMixin, TeacherProfileCompletedMixin, ListView):
    """Teacher view of all cancellation requests. Uses UserFilterMixin."""
    model = LessonCancellationRequest
    template_name = 'private_teaching/teacher_cancellation_requests.html'
    context_object_name = 'cancellation_requests'
    paginate_by = 20
    user_field_name = 'teacher'

    def get_queryset(self):
        status_filter = self.request.GET.get('status', 'pending')

        # UserFilterMixin automatically filters by teacher=self.request.user
        queryset = super().get_queryset().select_related('lesson', 'student', 'lesson__subject')

        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get counts for each status
        # PERFORMANCE FIX: Use single aggregate query instead of 4 separate counts
        from django.db.models import Count, Q
        counts = LessonCancellationRequest.objects.filter(
            teacher=self.request.user
        ).aggregate(
            pending=Count('id', filter=Q(status=LessonCancellationRequest.PENDING)),
            approved=Count('id', filter=Q(status=LessonCancellationRequest.APPROVED)),
            rejected=Count('id', filter=Q(status=LessonCancellationRequest.REJECTED)),
            completed=Count('id', filter=Q(status=LessonCancellationRequest.COMPLETED))
        )
        context['pending_count'] = counts['pending']
        context['approved_count'] = counts['approved']
        context['rejected_count'] = counts['rejected']
        context['completed_count'] = counts['completed']

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

            # If this is a reschedule request, update the lesson dates
            if cancellation_request.request_type == LessonCancellationRequest.RESCHEDULE:
                if cancellation_request.proposed_new_date and cancellation_request.proposed_new_time:
                    lesson = cancellation_request.lesson
                    lesson.lesson_date = cancellation_request.proposed_new_date
                    lesson.lesson_time = cancellation_request.proposed_new_time
                    lesson.save()
                    messages.success(
                        request,
                        f'Reschedule approved! Lesson has been rescheduled to {lesson.lesson_date.strftime("%B %d, %Y")} at {lesson.lesson_time.strftime("%I:%M %p")}.'
                    )
                else:
                    messages.warning(request, 'Reschedule approved but no new date/time was proposed.')

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


# ============================================================================
# QUIZ SYSTEM VIEWS
# ============================================================================

# -----------------------------
# Teacher: Quiz Library & Management
# -----------------------------

class QuizLibraryView(TeacherProfileCompletedMixin, ListView):
    """
    Teacher's quiz library - browse, search, and filter quizzes.
    Shows teacher's own quizzes plus public quizzes from other teachers.
    """
    model = PrivateLessonQuiz
    template_name = 'private_teaching/quiz/quiz_library.html'
    context_object_name = 'quizzes'
    paginate_by = 20

    def get_queryset(self):
        """Get teacher's quizzes + public quizzes, with search/filters"""
        queryset = PrivateLessonQuiz.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        ).select_related('created_by', 'subject').prefetch_related('tags')

        # Search
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()

        # Filter by subject
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        # Filter by syllabus
        syllabus = self.request.GET.get('syllabus')
        if syllabus:
            queryset = queryset.filter(syllabus=syllabus)

        # Filter by grade level
        grade = self.request.GET.get('grade')
        if grade:
            queryset = queryset.filter(grade_level__icontains=grade)

        # Filter by ownership
        ownership = self.request.GET.get('ownership')
        if ownership == 'mine':
            queryset = queryset.filter(created_by=self.request.user)
        elif ownership == 'public':
            queryset = queryset.filter(is_public=True).exclude(created_by=self.request.user)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(
            teacher=self.request.user, is_active=True
        )
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_subject'] = self.request.GET.get('subject', '')
        context['selected_syllabus'] = self.request.GET.get('syllabus', '')
        context['selected_grade'] = self.request.GET.get('grade', '')
        context['selected_ownership'] = self.request.GET.get('ownership', '')
        return context


class QuizCreateView(TeacherProfileCompletedMixin, CreateView):
    """Create new quiz"""
    model = PrivateLessonQuiz
    form_class = PrivateLessonQuizForm
    template_name = 'private_teaching/quiz/quiz_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Quiz "{form.instance.title}" created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('private_teaching:quiz_detail', kwargs={'pk': self.object.pk})


class QuizDetailView(TeacherProfileCompletedMixin, TemplateView):
    """View quiz details with questions and statistics"""
    template_name = 'private_teaching/quiz/quiz_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = get_object_or_404(
            PrivateLessonQuiz,
            pk=kwargs['pk']
        )

        # Check permissions - must be creator or quiz must be public
        if quiz.created_by != self.request.user and not quiz.is_public:
            messages.error(self.request, 'You do not have permission to view this quiz.')
            return redirect('private_teaching:quiz_library')

        context['quiz'] = quiz
        context['questions'] = quiz.questions.prefetch_related('answers').order_by('order')
        context['is_owner'] = quiz.created_by == self.request.user

        # Get assignment statistics if owner
        if context['is_owner']:
            assignments = quiz.assignments.select_related('student').all()
            context['total_assignments'] = assignments.count()
            context['completed_assignments'] = assignments.filter(status='completed').count()
            context['recent_assignments'] = assignments.order_by('-assigned_date')[:5]

        return context


class QuizEditView(TeacherProfileCompletedMixin, UpdateView):
    """Edit existing quiz"""
    model = PrivateLessonQuiz
    form_class = PrivateLessonQuizForm
    template_name = 'private_teaching/quiz/quiz_form.html'

    def get_queryset(self):
        """Only allow editing own quizzes"""
        return PrivateLessonQuiz.objects.filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Quiz "{form.instance.title}" updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('private_teaching:quiz_detail', kwargs={'pk': self.object.pk})


class QuizDeleteView(TeacherProfileCompletedMixin, DeleteView):
    """Delete quiz (with confirmation)"""
    model = PrivateLessonQuiz
    template_name = 'private_teaching/quiz/quiz_confirm_delete.html'
    success_url = reverse_lazy('private_teaching:quiz_library')

    def get_queryset(self):
        """Only allow deleting own quizzes"""
        return PrivateLessonQuiz.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        quiz = self.get_object()
        messages.success(request, f'Quiz "{quiz.title}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class QuizDuplicateView(TeacherProfileCompletedMixin, View):
    """Duplicate an existing quiz with all questions and answers"""

    def post(self, request, *args, **kwargs):
        original_quiz = get_object_or_404(
            PrivateLessonQuiz,
            pk=kwargs['pk']
        )

        # Check permissions - must be creator or quiz must be public
        if original_quiz.created_by != request.user and not original_quiz.is_public:
            messages.error(request, 'You do not have permission to duplicate this quiz.')
            return redirect('private_teaching:quiz_library')

        try:
            with transaction.atomic():
                # Duplicate quiz
                new_quiz = PrivateLessonQuiz.objects.create(
                    title=f"{original_quiz.title} (Copy)",
                    description=original_quiz.description,
                    instructions=original_quiz.instructions,
                    created_by=request.user,
                    pass_percentage=original_quiz.pass_percentage,
                    time_limit_minutes=original_quiz.time_limit_minutes,
                    randomize_questions=original_quiz.randomize_questions,
                    show_correct_answers=original_quiz.show_correct_answers,
                    allow_retakes=original_quiz.allow_retakes,
                    max_attempts=original_quiz.max_attempts,
                    subject=original_quiz.subject,
                    syllabus=original_quiz.syllabus,
                    grade_level=original_quiz.grade_level,
                    is_public=False  # Copies are always private initially
                )

                # Copy tags
                new_quiz.tags.set(original_quiz.tags.all())

                # Duplicate questions and answers
                for question in original_quiz.questions.all():
                    new_question = PrivateLessonQuizQuestion.objects.create(
                        quiz=new_quiz,
                        text=question.text,
                        order=question.order,
                        points=question.points,
                        explanation=question.explanation
                    )

                    # Duplicate answers
                    for answer in question.answers.all():
                        PrivateLessonQuizAnswer.objects.create(
                            question=new_question,
                            text=answer.text,
                            is_correct=answer.is_correct,
                            order=answer.order
                        )

            messages.success(request, f'Quiz duplicated successfully as "{new_quiz.title}"')
            return redirect('private_teaching:quiz_detail', pk=new_quiz.pk)

        except Exception as e:
            messages.error(request, f'Error duplicating quiz: {str(e)}')
            return redirect('private_teaching:quiz_library')


# -----------------------------
# Teacher: Question Management
# -----------------------------

class QuestionCreateView(TeacherProfileCompletedMixin, TemplateView):
    """Create question with inline answer formset"""
    template_name = 'private_teaching/quiz/question_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = get_object_or_404(
            PrivateLessonQuiz,
            pk=kwargs['quiz_id'],
            created_by=self.request.user
        )
        context['quiz'] = quiz
        context['form'] = PrivateLessonQuizQuestionForm()
        context['formset'] = PrivateLessonQuizAnswerFormSet()
        return context

    def post(self, request, *args, **kwargs):
        quiz = get_object_or_404(
            PrivateLessonQuiz,
            pk=kwargs['quiz_id'],
            created_by=request.user
        )

        form = PrivateLessonQuizQuestionForm(request.POST)

        # Create temporary question instance for formset
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz

            formset = PrivateLessonQuizAnswerFormSet(request.POST, instance=question)

            if formset.is_valid():
                # Check at least one correct answer
                correct_answers = sum(1 for form in formset if form.cleaned_data.get('is_correct', False) and not form.cleaned_data.get('DELETE', False))

                if correct_answers == 0:
                    messages.error(request, 'At least one answer must be marked as correct.')
                    return render(request, self.template_name, {
                        'quiz': quiz,
                        'form': form,
                        'formset': formset
                    })

                with transaction.atomic():
                    question.save()
                    formset.instance = question
                    formset.save()

                messages.success(request, 'Question added successfully!')
                return redirect('private_teaching:quiz_detail', pk=quiz.pk)
        else:
            formset = PrivateLessonQuizAnswerFormSet(request.POST)

        return render(request, self.template_name, {
            'quiz': quiz,
            'form': form,
            'formset': formset
        })


class QuestionEditView(TeacherProfileCompletedMixin, TemplateView):
    """Edit question with inline answer formset"""
    template_name = 'private_teaching/quiz/question_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = get_object_or_404(
            PrivateLessonQuizQuestion,
            pk=kwargs['pk'],
            quiz__created_by=self.request.user
        )
        context['quiz'] = question.quiz
        context['question'] = question
        context['form'] = PrivateLessonQuizQuestionForm(instance=question)
        context['formset'] = PrivateLessonQuizAnswerFormSet(instance=question)
        return context

    def post(self, request, *args, **kwargs):
        question = get_object_or_404(
            PrivateLessonQuizQuestion,
            pk=kwargs['pk'],
            quiz__created_by=request.user
        )

        form = PrivateLessonQuizQuestionForm(request.POST, instance=question)
        formset = PrivateLessonQuizAnswerFormSet(request.POST, instance=question)

        if form.is_valid() and formset.is_valid():
            # Check at least one correct answer (excluding deleted forms)
            correct_answers = sum(
                1 for f in formset
                if f.cleaned_data.get('is_correct', False) and not f.cleaned_data.get('DELETE', False)
            )

            if correct_answers == 0:
                messages.error(request, 'At least one answer must be marked as correct.')
                return render(request, self.template_name, {
                    'quiz': question.quiz,
                    'question': question,
                    'form': form,
                    'formset': formset
                })

            with transaction.atomic():
                form.save()
                formset.save()

            messages.success(request, 'Question updated successfully!')
            return redirect('private_teaching:quiz_detail', pk=question.quiz.pk)

        return render(request, self.template_name, {
            'quiz': question.quiz,
            'question': question,
            'form': form,
            'formset': formset
        })


class QuestionDeleteView(TeacherProfileCompletedMixin, DeleteView):
    """Delete question"""
    model = PrivateLessonQuizQuestion

    def get_queryset(self):
        """Only allow deleting questions from own quizzes"""
        return PrivateLessonQuizQuestion.objects.filter(quiz__created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        quiz = question.quiz
        question.delete()
        messages.success(request, 'Question deleted successfully.')
        return redirect('private_teaching:quiz_detail', pk=quiz.pk)


# -----------------------------
# Teacher: Quiz Assignments
# -----------------------------

class QuizAssignView(TeacherProfileCompletedMixin, CreateView):
    """Assign quiz to student(s)"""
    model = PrivateLessonQuizAssignment
    form_class = PrivateLessonQuizAssignmentForm
    template_name = 'private_teaching/quiz/quiz_assign.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz_id = self.kwargs.get('quiz_id')
        if quiz_id:
            context['quiz'] = get_object_or_404(
                PrivateLessonQuiz,
                pk=quiz_id,
                created_by=self.request.user
            )
        return context

    def form_valid(self, form):
        form.instance.teacher = self.request.user

        # If quiz_id in URL, set it
        quiz_id = self.kwargs.get('quiz_id')
        if quiz_id:
            form.instance.quiz = get_object_or_404(
                PrivateLessonQuiz,
                pk=quiz_id,
                created_by=self.request.user
            )

        # Get correct student name (child or adult)
        student_name = (
            form.instance.child_profile.full_name if form.instance.child_profile
            else (form.instance.student.get_full_name() or form.instance.student.username)
        )

        messages.success(
            self.request,
            f'Quiz assigned to {student_name} successfully!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('private_teaching:quiz_assignment_list')


class QuizAssignmentListView(TeacherProfileCompletedMixin, ListView):
    """Teacher's list of all quiz assignments"""
    model = PrivateLessonQuizAssignment
    template_name = 'private_teaching/quiz/quiz_assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        queryset = PrivateLessonQuizAssignment.objects.filter(
            teacher=self.request.user
        ).select_related(
            'quiz', 'student', 'child_profile', 'lesson'
        ).prefetch_related('attempts')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by student
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # Filter by quiz
        quiz_id = self.request.GET.get('quiz')
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)

        return queryset.order_by('-assigned_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get accepted students for filter
        accepted_apps = TeacherStudentApplication.objects.filter(
            teacher=self.request.user,
            status='accepted'
        ).values_list('applicant_id', flat=True)

        context['students'] = User.objects.filter(id__in=accepted_apps).order_by('first_name', 'last_name')
        context['quizzes'] = PrivateLessonQuiz.objects.filter(created_by=self.request.user).order_by('-created_at')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_student'] = self.request.GET.get('student', '')
        context['selected_quiz'] = self.request.GET.get('quiz', '')

        return context


class QuizAssignmentDetailView(TeacherProfileCompletedMixin, TemplateView):
    """View assignment details with all attempts"""
    template_name = 'private_teaching/quiz/quiz_assignment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = get_object_or_404(
            PrivateLessonQuizAssignment,
            pk=kwargs['pk'],
            teacher=self.request.user
        )

        context['assignment'] = assignment
        context['attempts'] = assignment.attempts.order_by('-started_at')

        # Calculate statistics
        if context['attempts']:
            scores = [attempt.score for attempt in context['attempts'] if attempt.submitted_at]
            if scores:
                context['best_score'] = max(scores)
                context['average_score'] = sum(scores) / len(scores)
                context['passed_attempts'] = sum(1 for attempt in context['attempts'] if attempt.passed)

        return context


class QuizAssignmentDeleteView(TeacherProfileCompletedMixin, DeleteView):
    """Delete assignment"""
    model = PrivateLessonQuizAssignment
    template_name = 'private_teaching/quiz/quiz_assignment_confirm_delete.html'
    success_url = reverse_lazy('private_teaching:quiz_assignment_list')

    def get_queryset(self):
        """Only allow deleting own assignments"""
        return PrivateLessonQuizAssignment.objects.filter(teacher=self.request.user)

    def delete(self, request, *args, **kwargs):
        assignment = self.get_object()
        messages.success(request, f'Assignment deleted successfully.')
        return super().delete(request, *args, **kwargs)


# -----------------------------
# Student: Quiz Taking
# -----------------------------

class StudentQuizListView(AcceptedStudentRequiredMixin, ListView):
    """Student's assigned quizzes"""
    model = PrivateLessonQuizAssignment
    template_name = 'private_teaching/quiz/student_quiz_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        queryset = PrivateLessonQuizAssignment.objects.filter(
            student=self.request.user
        ).select_related(
            'quiz', 'teacher', 'child_profile', 'lesson'
        ).prefetch_related('attempts')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by child profile if guardian
        child_id = self.request.GET.get('child')
        if child_id:
            queryset = queryset.filter(child_profile_id=child_id)

        return queryset.order_by('-assigned_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get child profiles if guardian
        from apps.accounts.models import ChildProfile
        context['child_profiles'] = ChildProfile.objects.filter(guardian=self.request.user)
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_child'] = self.request.GET.get('child', '')

        return context


class QuizTakeView(AcceptedStudentRequiredMixin, TemplateView):
    """Take quiz - show questions and collect answers"""
    template_name = 'private_teaching/quiz/quiz_take.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        assignment = get_object_or_404(
            PrivateLessonQuizAssignment,
            pk=kwargs['assignment_id'],
            student=self.request.user
        )

        # Check if already reached max attempts
        if assignment.quiz.max_attempts:
            attempt_count = assignment.attempts.count()
            if attempt_count >= assignment.quiz.max_attempts:
                messages.error(self.request, 'You have reached the maximum number of attempts for this quiz.')
                return redirect('private_teaching:student_quiz_list')

        # Check if quiz has questions
        if not assignment.quiz.questions.exists():
            messages.error(self.request, 'This quiz has no questions yet. Please contact your teacher.')
            return redirect('private_teaching:student_quiz_list')

        context['assignment'] = assignment
        context['quiz'] = assignment.quiz

        # Get questions (randomized if enabled)
        questions = assignment.quiz.get_questions(randomize=assignment.quiz.randomize_questions)
        context['questions'] = questions

        # Create new attempt
        attempt = PrivateLessonQuizAttempt.objects.create(
            assignment=assignment
        )
        context['attempt'] = attempt

        # Update assignment status
        if assignment.status == 'assigned':
            assignment.status = 'in_progress'
            assignment.save()

        return context


class QuizSubmitView(AcceptedStudentRequiredMixin, View):
    """Submit quiz answers (AJAX endpoint)"""

    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(
            PrivateLessonQuizAssignment,
            pk=kwargs['assignment_id'],
            student=request.user
        )

        # Get attempt ID from POST data
        attempt_id = request.POST.get('attempt_id')
        if not attempt_id:
            return JsonResponse({'success': False, 'error': 'No attempt ID provided'}, status=400)

        attempt = get_object_or_404(
            PrivateLessonQuizAttempt,
            pk=attempt_id,
            assignment=assignment
        )

        # Check if already submitted
        if attempt.submitted_at:
            return JsonResponse({'success': False, 'error': 'Quiz already submitted'}, status=400)

        try:
            with transaction.atomic():
                # Collect answers from POST data
                answers_data = {}
                for key, value in request.POST.items():
                    if key.startswith('question_'):
                        question_id = key.replace('question_', '')
                        answers_data[question_id] = value

                # Save answers
                attempt.answers_data = answers_data
                attempt.submitted_at = timezone.now()

                # Calculate time taken
                time_taken = (attempt.submitted_at - attempt.started_at).total_seconds() / 60
                attempt.time_taken_minutes = int(time_taken)

                # Grade the attempt
                attempt.calculate_score()
                attempt.grade()
                attempt.save()

                # Update assignment status
                assignment.status = 'completed'
                assignment.save()

                return JsonResponse({
                    'success': True,
                    'score': float(attempt.score),
                    'passed': attempt.passed,
                    'redirect_url': reverse('private_teaching:quiz_attempt_results', kwargs={'pk': attempt.pk})
                })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class QuizAttemptResultsView(AcceptedStudentRequiredMixin, TemplateView):
    """View quiz results after submission"""
    template_name = 'private_teaching/quiz/quiz_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        attempt = get_object_or_404(
            PrivateLessonQuizAttempt,
            pk=kwargs['pk'],
            assignment__student=self.request.user
        )

        context['attempt'] = attempt
        context['assignment'] = attempt.assignment
        context['quiz'] = attempt.assignment.quiz

        # Get questions with student's answers
        questions_data = []
        for question in attempt.assignment.quiz.questions.order_by('order'):
            question_id_str = str(question.id)
            student_answer_id = attempt.answers_data.get(question_id_str)

            question_info = {
                'question': question,
                'student_answer_id': student_answer_id,
                'answers': question.answers.order_by('order'),
                'correct_answer': question.answers.filter(is_correct=True).first(),
                'is_correct': False
            }

            # Check if answer is correct
            if student_answer_id:
                correct_answer = question.answers.filter(is_correct=True).first()
                if correct_answer and str(correct_answer.id) == student_answer_id:
                    question_info['is_correct'] = True

            questions_data.append(question_info)

        context['questions_data'] = questions_data

        # Check if can retake
        context['can_retake'] = False
        if attempt.assignment.quiz.allow_retakes:
            if attempt.assignment.quiz.max_attempts:
                attempt_count = attempt.assignment.attempts.count()
                context['can_retake'] = attempt_count < attempt.assignment.quiz.max_attempts
            else:
                context['can_retake'] = True

        return context