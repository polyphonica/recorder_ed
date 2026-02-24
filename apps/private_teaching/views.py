from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, ListView, View, UpdateView, DeleteView
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.db import transaction, models
from django.db.models import Count, Q, Sum
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.conf import settings
from django import forms

from apps.core.views import BaseCheckoutSuccessView, BaseCheckoutCancelView, UserFilterMixin
from apps.core.models import Cart
from .models import (
    LessonRequest, Subject, LessonRequestMessage, CartItem, Order, OrderItem,
    TeacherStudentApplication, LessonCancellationRequest,
    StudentPieceAssignment, StudentCollectionAssignment
)
from .notifications import TeacherNotificationService, StudentNotificationService
from apps.exams.models import ExamRegistration
from apps.practice.models import PracticeEntry
from apps.quizzes.models import Quiz as PrivateLessonQuiz, QuizAssignment as PrivateLessonQuizAssignment
from apps.scheduling.availability_engine import check_slot_availability
from lessons.models import Lesson, Document, LessonAttachedUrl, LessonAssignment
from .forms import LessonRequestForm, ProfileCompleteForm, StudentSignupForm, StudentLessonFormSet, TeacherProfileCompleteForm, TeacherLessonFormSet, TeacherResponseForm, SubjectForm, RescheduleForm, TeacherInitiateCancellationForm
from .cart import CartManager
from apps.payments.voucher_service import VoucherService, VoucherValidationError
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


class PrivateLessonTermsView(TemplateView):
    """Display current Private Lesson Terms and Conditions"""
    template_name = 'private_teaching/terms_and_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import PrivateLessonTermsAndConditions
        current_terms = PrivateLessonTermsAndConditions.objects.filter(is_current=True).first()
        context['current_terms'] = current_terms
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
                    lessons__approved_status=Lesson.ApprovalStatus.ACCEPTED,
                    lessons__payment_status='pending',
                    lessons__is_deleted=False
                )
            ),
            total_active_lessons=Count(
                'lessons',
                filter=Q(lessons__is_deleted=False)
            ),
            rejected_lessons_count=Count(
                'lessons',
                filter=Q(
                    lessons__is_deleted=True,
                    lessons__approved_status=Lesson.ApprovalStatus.REJECTED
                )
            )
        ).order_by('-created_at')

        # Exclude requests with no lessons at all (neither active nor rejected)
        return queryset.exclude(total_active_lessons=0, rejected_lessons_count=0)


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
        rejected_lessons = lesson_request.lessons.filter(
            is_deleted=True,
            approved_status=Lesson.ApprovalStatus.REJECTED
        ).select_related('subject')

        # Count eligible lessons (accepted and unpaid)
        eligible_lessons_count = lessons.filter(
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            payment_status='pending'
        ).count()

        context.update({
            'lesson_request': lesson_request,
            'lessons': lessons,
            'rejected_lessons': rejected_lessons,
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
    if lesson.payment_status == 'completed':
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
            lessons__approved_status=Lesson.ApprovalStatus.PENDING
        ).distinct().select_related('student', 'child_profile').prefetch_related(
            Prefetch('lessons',
                     queryset=Lesson.objects.select_related('subject').filter(approved_status=Lesson.ApprovalStatus.PENDING))
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

        # Get paid lessons waiting to be assigned (payment_status='Paid' and status=Lesson.Status.DRAFT)
        # These are lessons that have been paid for but the teacher hasn't scheduled them yet
        paid_unassigned_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            payment_status='completed',
            status=Lesson.Status.DRAFT,
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
            'pending_applications': pending_applications[:10],
            'pending_applications_count': pending_applications.count(),
            'waitlist_applications': waitlist_applications[:10],
            'waitlist_applications_count': waitlist_applications.count(),
            'pending_requests': pending_requests[:10],
            'pending_count': pending_requests.count(),
            'today_lessons': today_lessons,
            'upcoming_lessons': upcoming_lessons,
            'paid_unassigned_lessons': paid_unassigned_lessons[:10],
            'paid_unassigned_count': paid_unassigned_lessons.count(),
            'active_exams_count': active_exams,
            'pending_cancellations': pending_cancellations[:10],
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
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            is_deleted=False
        ).select_related('subject', 'teacher').order_by('lesson_date', 'lesson_time')[:5]

        # Get lessons awaiting payment (approved but not paid)
        awaiting_payment = Lesson.objects.filter(
            student=self.request.user,
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            payment_status='pending',
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
        # Includes both lesson-linked (lesson.student = user) and standalone (student = user)
        from assignments.models import AssignmentSubmission

        assignment_links = LessonAssignment.objects.filter(
            Q(lesson__student=self.request.user, lesson__status=Lesson.Status.ASSIGNED) |
            Q(student=self.request.user, lesson__isnull=True)
        ).select_related('assignment')

        # Fetch all submissions in a single query
        assignment_ids = [link.assignment_id for link in assignment_links]
        submissions_by_assignment = {
            sub.assignment_id: sub
            for sub in AssignmentSubmission.objects.filter(
                student=self.request.user,
                assignment_id__in=assignment_ids
            )
        }

        pending_assignments_count = 0
        for link in assignment_links:
            submission = submissions_by_assignment.get(link.assignment_id)
            if not submission or submission.status == 'draft':
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
                if lesson.approved_status == Lesson.ApprovalStatus.REJECTED:
                    lesson.is_deleted = True
                    rejected_lessons.append(lesson)
                elif lesson.approved_status == Lesson.ApprovalStatus.ACCEPTED:
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

        # Lesson IDs that already have a pending teacher-initiated request (disable button)
        pending_teacher_cancel_ids = set(
            LessonCancellationRequest.objects.filter(
                teacher=self.request.user,
                initiated_by=LessonCancellationRequest.INITIATED_BY_TEACHER,
                status=LessonCancellationRequest.PENDING
            ).values_list('lesson_id', flat=True)
        )

        context.update({
            'scheduled_lessons': scheduled_lessons,
            'today': today,
            'end_date': end_date,
            'pending_teacher_cancel_ids': pending_teacher_cancel_ids,
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
        # Prefetch order_item to access price_paid for discount display
        return super().get_queryset().filter(
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            is_deleted=False
        ).select_related('subject', 'teacher', 'order_item').order_by('lesson_date', 'lesson_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Separate paid and unpaid lessons
        lessons = self.get_queryset()
        context['paid_lessons'] = lessons.filter(payment_status='completed')
        context['unpaid_lessons'] = lessons.filter(payment_status='pending')

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
            if lesson.payment_status == 'completed':
                color = '#10b981'  # Green for paid lessons
            elif lesson.approved_status == Lesson.ApprovalStatus.ACCEPTED:
                color = '#f59e0b'  # Yellow/amber for approved but not paid
            elif lesson.approved_status == Lesson.ApprovalStatus.REJECTED:
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


# ============================================================================
# VOUCHER MANAGEMENT VIEWS
# ============================================================================

class VoucherListView(TeacherProfileCompletedMixin, TemplateView):
    """List all vouchers created by the teacher"""
    template_name = 'private_teaching/voucher_list.html'

    def get_context_data(self, **kwargs):
        from apps.payments.models import Voucher
        from .forms import VoucherForm

        context = super().get_context_data(**kwargs)
        vouchers = (
            Voucher.objects
            .filter(created_by=self.request.user)
            .annotate(redemption_count=Count('redemptions'))
            .order_by('-created_at')
        )

        # Calculate stats on full queryset before paginating
        active_vouchers = vouchers.filter(status='active')
        total_redemptions = vouchers.aggregate(total=Sum('redemption_count'))['total'] or 0

        paginator = Paginator(vouchers, 20)
        page = paginator.get_page(self.request.GET.get('page'))

        context['vouchers'] = page
        context['page_obj'] = page
        context['is_paginated'] = page.has_other_pages()
        context['active_count'] = active_vouchers.count()
        context['total_redemptions'] = total_redemptions
        context['voucher_form'] = VoucherForm(teacher=self.request.user)
        return context


class VoucherCreateView(TeacherProfileCompletedMixin, View):
    """Create a new voucher (POST-only)"""

    def post(self, request, *args, **kwargs):
        from .forms import VoucherForm

        form = VoucherForm(request.POST, teacher=request.user)
        if form.is_valid():
            voucher = form.save()
            messages.success(request, f'Voucher "{voucher.code}" created successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

        return redirect('private_teaching:voucher_list')


class VoucherDetailView(TeacherProfileCompletedMixin, TemplateView):
    """View voucher details and redemption history"""
    template_name = 'private_teaching/voucher_detail.html'

    def get_context_data(self, **kwargs):
        from apps.payments.models import Voucher, VoucherRedemption
        from .forms import VoucherForm

        context = super().get_context_data(**kwargs)
        voucher_id = self.kwargs.get('pk')
        voucher = get_object_or_404(Voucher, id=voucher_id, created_by=self.request.user)

        redemptions = VoucherRedemption.objects.filter(voucher=voucher).select_related(
            'student', 'private_lesson_order', 'workshop_registration'
        ).order_by('-redeemed_at')

        # Calculate stats on full queryset before paginating
        total_discount_given = redemptions.aggregate(total=Sum('discount_amount'))['total'] or 0

        paginator = Paginator(redemptions, 20)
        page = paginator.get_page(self.request.GET.get('page'))

        context['voucher'] = voucher
        context['redemptions'] = page
        context['page_obj'] = page
        context['is_paginated'] = page.has_other_pages()
        context['total_discount_given'] = total_discount_given
        context['voucher_form'] = VoucherForm(instance=voucher, teacher=self.request.user)
        return context


class VoucherUpdateView(TeacherProfileCompletedMixin, View):
    """Update voucher (POST-only)"""

    def post(self, request, *args, **kwargs):
        from apps.payments.models import Voucher
        from .forms import VoucherForm

        voucher_id = kwargs.get('pk')
        voucher = get_object_or_404(Voucher, id=voucher_id, created_by=request.user)

        form = VoucherForm(request.POST, instance=voucher, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Voucher "{voucher.code}" updated successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

        return redirect('private_teaching:voucher_detail', pk=voucher_id)


class VoucherDeleteView(TeacherProfileCompletedMixin, View):
    """Delete voucher (POST-only)"""

    def post(self, request, *args, **kwargs):
        from apps.payments.models import Voucher

        voucher_id = kwargs.get('pk')
        voucher = get_object_or_404(Voucher, id=voucher_id, created_by=request.user)

        # Check if voucher has redemptions
        if voucher.redemptions.exists():
            messages.error(request, f'Cannot delete voucher "{voucher.code}" - it has been used. You can pause it instead.')
            return redirect('private_teaching:voucher_list')

        code = voucher.code
        voucher.delete()
        messages.success(request, f'Voucher "{code}" deleted successfully!')
        return redirect('private_teaching:voucher_list')


class VoucherToggleStatusView(TeacherProfileCompletedMixin, View):
    """Toggle voucher status between active and paused"""

    def post(self, request, *args, **kwargs):
        from apps.payments.models import Voucher

        voucher_id = kwargs.get('pk')
        voucher = get_object_or_404(Voucher, id=voucher_id, created_by=request.user)

        if voucher.status == 'active':
            voucher.status = 'paused'
            messages.success(request, f'Voucher "{voucher.code}" has been paused.')
        elif voucher.status == 'paused':
            voucher.status = 'active'
            messages.success(request, f'Voucher "{voucher.code}" is now active.')
        else:
            messages.warning(request, f'Voucher "{voucher.code}" cannot be toggled (status: {voucher.status}).')

        voucher.save()
        return redirect('private_teaching:voucher_list')


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
    """Create Stripe checkout session and redirect to payment, with voucher support"""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from apps.payments.stripe_service import create_checkout_session
        from decimal import Decimal

        cart_manager = CartManager(request)
        cart_context = cart_manager.get_cart_context()

        if not cart_context['cart_items']:
            messages.error(request, "Your cart is empty. Add lessons before checkout.")
            return redirect('private_teaching:cart')

        # Get teacher from cart items
        teacher = None
        for cart_item in cart_context['cart_items']:
            if cart_item.lesson.teacher:
                teacher = cart_item.lesson.teacher
                break

        # Handle voucher code if provided
        voucher_code = request.POST.get('voucher_code', '').strip()
        applied_voucher = None
        discount_amount = Decimal('0.00')
        final_total = cart_context['cart_total']

        if voucher_code:
            try:
                applied_voucher = VoucherService.validate_voucher(
                    code=voucher_code,
                    student=request.user,
                    domain='private_teaching',
                    cart_total=cart_context['cart_total'],
                    teacher=teacher
                )
                discount_amount, final_total = VoucherService.calculate_discount(
                    applied_voucher, cart_context['cart_total']
                )
            except VoucherValidationError as e:
                messages.error(request, str(e))
                return redirect('private_teaching:cart')

        # Clean up ANY existing OrderItems for these lessons first
        lesson_ids_to_checkout = [cart_item.lesson.id for cart_item in cart_context['cart_items']]

        # Find ALL OrderItems for these lessons (regardless of order status)
        orphaned_order_items = OrderItem.objects.filter(
            lesson_id__in=lesson_ids_to_checkout
        )

        # Delete the existing orders (will cascade delete OrderItems)
        orphaned_order_ids = list(orphaned_order_items.values_list('order_id', flat=True).distinct())
        if orphaned_order_ids:
            deleted_count = Order.objects.filter(id__in=orphaned_order_ids).delete()
            print(f"Cleaned up {deleted_count[0]} existing orders for these lessons")

        # Collect lesson IDs and create order items
        lesson_ids = []

        # Handle 100% FREE voucher - bypass Stripe entirely
        if final_total == Decimal('0.00') and applied_voucher:
            # Create order with completed status
            order = Order.objects.create(
                student=request.user,
                total_amount=Decimal('0.00'),
                payment_status='completed',
                payment_method='voucher_free'
            )

            # Create order items and mark lessons as paid
            for cart_item in cart_context['cart_items']:
                OrderItem.objects.create(
                    order=order,
                    lesson=cart_item.lesson,
                    price_paid=Decimal('0.00')
                )
                lesson_ids.append(str(cart_item.lesson.id))

                # Mark lesson as paid
                cart_item.lesson.payment_status = 'completed'
                cart_item.lesson.in_cart = False
                cart_item.lesson.save()

            # Create voucher redemption record
            VoucherService.create_redemption(
                voucher=applied_voucher,
                student=request.user,
                domain='private_teaching',
                original_amount=cart_context['cart_total'],
                discount_amount=discount_amount,
                final_amount=final_total,
                request=request,
                private_lesson_order=order
            )

            # Clear the cart
            cart_manager.clear_cart()

            # Send notifications
            StudentNotificationService.send_payment_confirmation(order)
            if teacher:
                from .notifications import TeacherPaymentNotificationService
                TeacherPaymentNotificationService.send_lesson_payment_notification(order, teacher)

            messages.success(request, f"Voucher {applied_voucher.code} applied! Your lessons are now booked.")
            return redirect('private_teaching:checkout_success', order_id=order.id)

        # Create order with pending status for paid checkout
        order = Order.objects.create(
            student=request.user,
            total_amount=final_total,
            payment_status='pending',
            payment_method='stripe'
        )

        # Create order items (but don't mark lessons as paid yet)
        for cart_item in cart_context['cart_items']:
            OrderItem.objects.create(
                order=order,
                lesson=cart_item.lesson,
                price_paid=cart_item.price
            )
            lesson_ids.append(str(cart_item.lesson.id))

        # Prepare success and cancel URLs
        success_url = request.build_absolute_uri(
            reverse('private_teaching:checkout_success', kwargs={'order_id': order.id})
        )
        cancel_url = request.build_absolute_uri(
            reverse('private_teaching:checkout_cancel', kwargs={'order_id': order.id})
        )

        # Prepare metadata
        metadata = {
            'order_id': str(order.id),
            'lesson_ids': ','.join(lesson_ids),
        }

        # Add voucher info to metadata if applied
        if applied_voucher:
            metadata['voucher_id'] = str(applied_voucher.id)
            metadata['voucher_code'] = applied_voucher.code
            metadata['original_amount'] = str(cart_context['cart_total'])
            metadata['discount_amount'] = str(discount_amount)
            # Override total_amount with discounted amount for correct finance reporting
            metadata['total_amount'] = str(final_total)
            # Recalculate commission on discounted amount
            from apps.payments.utils import calculate_commission
            platform_commission, teacher_share = calculate_commission(final_total)
            metadata['platform_commission'] = str(platform_commission)
            metadata['teacher_share'] = str(teacher_share)

        # Get Stripe coupon ID if voucher provides partial discount
        coupon_id = None
        if applied_voucher and final_total > Decimal('0.00'):
            coupon_id = VoucherService.create_or_get_stripe_coupon(applied_voucher)

        # Create Stripe checkout session
        try:
            session = create_checkout_session(
                amount=cart_context['cart_total'],  # Use original amount, Stripe coupon will apply discount
                student=request.user,
                teacher=teacher,
                domain='private_teaching',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
                coupon_id=coupon_id
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
    """Handle return from Stripe after successful checkout.

    Includes fallback processing if webhook hasn't processed the payment yet.
    This handles race conditions and local development without webhook forwarding.
    """
    template_name = 'private_teaching/payment_success.html'

    def get_object_model(self):
        return Order

    def get_object_id_kwarg(self):
        return 'order_id'

    def get_redirect_url_name(self):
        return 'private_teaching:home'

    def perform_post_checkout_actions(self, obj):
        """Clear the cart and process payment fallback if needed"""
        # Check if webhook has already processed this payment
        if obj.payment_status == 'pending' and obj.stripe_checkout_session_id:
            self._process_payment_fallback(obj)

        cart_manager = CartManager(self.request)
        cart_manager.clear_cart()

    def _process_payment_fallback(self, order):
        """Process payment if webhook hasn't done so yet."""
        import stripe
        from decimal import Decimal
        from django.conf import settings
        from django.utils import timezone
        from apps.payments.models import StripePayment
        from apps.payments.voucher_service import VoucherService
        import logging

        logger = logging.getLogger(__name__)
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            # Check if StripePayment already exists
            existing_payment = StripePayment.objects.filter(
                stripe_checkout_session_id=order.stripe_checkout_session_id
            ).first()

            if existing_payment:
                logger.info(f"StripePayment already exists for order {order.id}")
                return

            # Retrieve the Stripe session
            session = stripe.checkout.Session.retrieve(order.stripe_checkout_session_id)

            # Only process if payment succeeded
            if session.payment_status != 'paid':
                logger.warning(f"Checkout session {order.stripe_checkout_session_id} not paid: {session.payment_status}")
                return

            metadata = session.get('metadata', {})
            logger.info(f"Processing payment fallback for order {order.id}")

            # Get amounts from metadata
            total_amount = Decimal(metadata.get('total_amount', str(order.total_amount)))
            platform_commission = Decimal(metadata.get('platform_commission', '0'))
            teacher_share = Decimal(metadata.get('teacher_share', '0'))

            # Get teacher from first order item
            first_item = order.items.select_related('lesson__teacher').first()
            teacher = first_item.lesson.teacher if first_item else None

            # Create StripePayment record
            stripe_payment = StripePayment.objects.create(
                stripe_checkout_session_id=order.stripe_checkout_session_id,
                stripe_payment_intent_id=session.payment_intent,
                domain='private_teaching',
                student=order.student,
                teacher=teacher,
                total_amount=total_amount,
                platform_commission=platform_commission,
                teacher_share=teacher_share,
                currency='gbp',
                status='completed',
                metadata=metadata,
            )

            # Update order status
            order.payment_status = 'completed'
            order.stripe_payment_intent_id = session.payment_intent
            order.total_amount = total_amount
            order.save()

            # Mark all lessons in this order as Paid
            for order_item in order.items.select_related('lesson'):
                lesson = order_item.lesson
                lesson.payment_status = 'completed'
                lesson.save(update_fields=['payment_status'])

            # Handle voucher redemption if applicable
            voucher_id = metadata.get('voucher_id')
            if voucher_id:
                try:
                    from apps.payments.models import Voucher
                    voucher = Voucher.objects.get(id=voucher_id)
                    original_amount = Decimal(metadata.get('original_amount', '0'))
                    discount_amount = Decimal(metadata.get('discount_amount', '0'))

                    VoucherService.create_redemption(
                        voucher=voucher,
                        student=order.student,
                        domain='private_teaching',
                        original_amount=original_amount,
                        discount_amount=discount_amount,
                        final_amount=total_amount,
                        private_lesson_order=order,
                        stripe_payment=stripe_payment
                    )
                    logger.info(f"Created VoucherRedemption for voucher {voucher.code}")
                except Exception as e:
                    logger.error(f"Error creating voucher redemption: {e}")

            logger.info(f"Successfully processed payment fallback for order {order.id}")

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in payment fallback: {e}")
        except Exception as e:
            logger.error(f"Error in payment fallback processing: {e}")

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
                    approved_status=Lesson.ApprovalStatus.ACCEPTED
                )
            else:
                lesson = Lesson.objects.select_related(
                    'subject', 'student', 'teacher', 'lesson_request', 'lesson_request__child_profile'
                ).get(
                    id=lesson_id,
                    student=request.user,
                    approved_status=Lesson.ApprovalStatus.ACCEPTED
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
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            payment_status='completed',
            status=Lesson.Status.ASSIGNED,
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
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).select_related('subject', 'lesson_request', 'lesson_request__child_profile')

            # Get unique subjects for this student
            subjects = Subject.objects.filter(
                teacher=self.request.user,
                lesson__student=student,
                lesson__approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
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


class TeacherStudentProgressView(TeacherProfileCompletedMixin, TemplateView):
    """
    Comprehensive student progress and management view for teachers.
    Shows assignments, quizzes, exams, and practice logs for a specific student.
    """
    template_name = 'private_teaching/teacher_student_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = kwargs.get('student_id')

        try:
            # Verify this teacher has lessons with this student
            from lessons.models import Lesson
            lesson_exists = Lesson.objects.filter(
                teacher=self.request.user,
                student_id=student_id,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).exists()

            if not lesson_exists:
                raise PermissionDenied("You don't have permission to view this student")

            # Get student details
            student = User.objects.select_related('profile').get(id=student_id)
            context['student'] = student

            # Get subjects for this student
            subjects = Subject.objects.filter(
                teacher=self.request.user,
                lesson__student=student,
                lesson__approved_status=Lesson.ApprovalStatus.ACCEPTED,
                lesson__is_deleted=False
            ).distinct()
            context['subjects'] = subjects

            # Get total lessons count
            total_lessons = Lesson.objects.filter(
                teacher=self.request.user,
                student=student,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).count()
            context['total_lessons'] = total_lessons

            # Check if student is a guardian with children
            from apps.accounts.models import ChildProfile
            lessons = Lesson.objects.filter(
                teacher=self.request.user,
                student=student,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).select_related('lesson_request__child_profile')

            child_profiles = []
            for lesson in lessons:
                if lesson.lesson_request and lesson.lesson_request.child_profile:
                    child_profile = lesson.lesson_request.child_profile
                    if child_profile not in child_profiles:
                        child_profiles.append(child_profile)

            context['child_profiles'] = child_profiles
            context['is_guardian'] = len(child_profiles) > 0

            # Get filter parameter
            filter_status = self.request.GET.get('filter', 'all')
            context['filter_status'] = filter_status

            # ===== ASSIGNMENTS SECTION =====
            from assignments.models import AssignmentSubmission
            from lessons.models import LessonAssignment
            from django.db.models import Q as DQ

            assignments = LessonAssignment.objects.filter(
                DQ(lesson__student=student, lesson__subject__teacher=self.request.user) |
                DQ(student=student, teacher=self.request.user, lesson__isnull=True)
            ).select_related('assignment')

            # Annotate assignments with status
            assignment_data = []
            for assign in assignments:
                sub = assign.submission

                # Determine status
                if not sub:
                    status = 'not_started'
                    grade = None
                    grade_display = '—'
                elif sub.status == 'draft':
                    status = 'in_progress'
                    grade = None
                    grade_display = '—'
                elif sub.status == 'submitted':
                    status = 'submitted'
                    grade = None
                    grade_display = 'Pending'
                elif sub.status == 'graded':
                    status = 'graded'
                    grade = sub.grade
                    grade_display = assign.assignment.format_grade(grade)
                else:
                    status = 'unknown'
                    grade = None
                    grade_display = '—'

                # Check if passed (for graded assignments)
                passed = None
                if status == 'graded' and grade is not None:
                    if assign.assignment.grading_scale == 'pass_fail':
                        passed = grade >= 1
                    else:
                        # Consider 60% as passing (adjust as needed)
                        max_grade = assign.assignment.get_max_grade()
                        passed = (grade / max_grade) >= 0.6 if max_grade > 0 else False

                assignment_data.append({
                    'assignment': assign,
                    'submission': sub,
                    'status': status,
                    'grade': grade,
                    'grade_display': grade_display,
                    'passed': passed,
                    'is_overdue': assign.is_overdue,
                })

            # Apply filter
            if filter_status == 'outstanding':
                assignment_data = [a for a in assignment_data if a['status'] in ['not_started', 'in_progress', 'submitted']]
            elif filter_status == 'completed':
                assignment_data = [a for a in assignment_data if a['status'] == 'graded']
            elif filter_status == 'not_passed':
                assignment_data = [a for a in assignment_data if a['status'] == 'graded' and a['passed'] is False]

            context['assignment_data'] = assignment_data
            context['total_assignments'] = len(assignments)
            context['outstanding_assignments'] = len([a for a in assignment_data if a['status'] in ['not_started', 'in_progress', 'submitted']])

            # ===== QUIZZES SECTION =====
            quiz_assignments = PrivateLessonQuizAssignment.objects.filter(
                teacher=self.request.user,
                student=student
            ).select_related('quiz').prefetch_related('attempts')

            quiz_data = []
            for quiz_assign in quiz_assignments:
                best_attempt = quiz_assign.best_attempt
                latest_attempt = quiz_assign.latest_attempt

                # Determine status
                if quiz_assign.attempt_count == 0:
                    status = 'not_started'
                elif quiz_assign.status == 'completed':
                    status = 'completed'
                elif quiz_assign.status == 'in_progress':
                    status = 'in_progress'
                else:
                    status = 'assigned'

                # Get best score
                best_score = best_attempt.score if best_attempt else None
                best_score_display = f"{best_score}%" if best_score is not None else '—'

                # Get latest score
                latest_score = latest_attempt.score if latest_attempt and latest_attempt.submitted_at else None
                latest_score_display = f"{latest_score}%" if latest_score is not None else '—'

                # Check if passed (based on latest attempt)
                passed = latest_attempt.passed if latest_attempt and latest_attempt.submitted_at else quiz_assign.passed

                quiz_data.append({
                    'assignment': quiz_assign,
                    'status': status,
                    'best_score': best_score,
                    'best_score_display': best_score_display,
                    'latest_score': latest_score,
                    'latest_score_display': latest_score_display,
                    'passed': passed,
                    'attempts': quiz_assign.attempt_count,
                    'max_attempts': quiz_assign.quiz.max_attempts,
                    'best_attempt': best_attempt,
                    'latest_attempt': latest_attempt,
                    'is_overdue': quiz_assign.is_overdue,
                })

            # Apply filter
            if filter_status == 'outstanding':
                quiz_data = [q for q in quiz_data if q['status'] in ['not_started', 'assigned', 'in_progress'] or not q['passed']]
            elif filter_status == 'completed':
                quiz_data = [q for q in quiz_data if q['status'] == 'completed' and q['passed']]
            elif filter_status == 'not_passed':
                quiz_data = [q for q in quiz_data if q['status'] == 'completed' and not q['passed']]

            context['quiz_data'] = quiz_data
            context['total_quizzes'] = len(quiz_assignments)
            context['outstanding_quizzes'] = len([q for q in quiz_data if q['status'] in ['not_started', 'assigned', 'in_progress'] or not q['passed']])

            # ===== EXAMS SECTION =====
            from django.utils import timezone

            exams = ExamRegistration.objects.filter(
                teacher=self.request.user,
                student=student
            ).order_by('exam_date')

            upcoming_exams = exams.filter(exam_date__gte=timezone.now())
            past_exams = exams.filter(exam_date__lt=timezone.now())

            context['upcoming_exams'] = upcoming_exams
            context['past_exams'] = past_exams
            context['total_exams'] = exams.count()

            # ===== PRACTICE LOG SECTION =====
            practice_entries = PracticeEntry.objects.filter(
                student=student
            ).select_related('child_profile').order_by('-practice_date')[:10]

            # Calculate practice stats
            from datetime import timedelta
            now = timezone.now()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            week_practice = PracticeEntry.objects.filter(
                student=student,
                practice_date__gte=week_ago
            ).aggregate(total=models.Sum('duration_minutes'))['total'] or 0

            month_practice = PracticeEntry.objects.filter(
                student=student,
                practice_date__gte=month_ago
            ).aggregate(total=models.Sum('duration_minutes'))['total'] or 0

            context['practice_entries'] = practice_entries
            context['week_practice_minutes'] = week_practice
            context['month_practice_minutes'] = month_practice

            # ===== PLAYALONGS SECTION =====
            from apps.audioplayer.models import Piece, PieceCollection

            # Get student-level assignments
            piece_assignments = StudentPieceAssignment.objects.filter(
                teacher=self.request.user, student=student
            ).select_related('piece', 'piece__composer').order_by('status', '-assigned_at')

            collection_assignments = StudentCollectionAssignment.objects.filter(
                teacher=self.request.user, student=student
            ).select_related('collection').prefetch_related(
                'collection__collection_memberships'
            ).order_by('status', '-assigned_at')

            # Build playalong data for template
            playalong_data = []

            for pa in piece_assignments:
                playalong_data.append({
                    'type': 'piece',
                    'id': pa.id,
                    'title': pa.piece.title,
                    'status': pa.status,
                    'instructions': pa.instructions,
                    'assigned_at': pa.assigned_at,
                    'piece_count': 1,
                })

            for ca in collection_assignments:
                playalong_data.append({
                    'type': 'collection',
                    'id': ca.id,
                    'title': ca.collection.title,
                    'status': ca.status,
                    'instructions': ca.instructions,
                    'assigned_at': ca.assigned_at,
                    'piece_count': ca.collection.collection_memberships.count(),
                })

            context['playalong_data'] = playalong_data
            context['total_playalongs'] = len(playalong_data)
            context['total_playalong_pieces'] = piece_assignments.count()
            context['total_playalong_collections'] = collection_assignments.count()

            # Available pieces and collections for assign modal
            context['available_pieces'] = Piece.objects.filter(
                created_by=self.request.user
            ).select_related('composer').order_by('title')
            context['available_collections'] = PieceCollection.objects.filter(
                created_by=self.request.user
            ).select_related('composer').prefetch_related('collection_memberships').order_by('title')

            # ===== LESSONS SECTION =====
            from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
            from django.db.models import Count

            # Get all lessons for this student with content counts
            lessons_queryset = Lesson.objects.filter(
                teacher=self.request.user,
                student=student,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).select_related('subject', 'lesson_request').annotate(
                pieces_count=Count('lesson_pieces', distinct=True),
                collections_count=Count('lesson_collections', distinct=True),
                assignments_count=Count('lesson_assignments', distinct=True)
            ).order_by('-lesson_date', '-lesson_time')

            # Apply filters
            subject_filter = self.request.GET.get('subject')
            date_from = self.request.GET.get('date_from')
            date_to = self.request.GET.get('date_to')

            if subject_filter:
                lessons_queryset = lessons_queryset.filter(subject_id=subject_filter)

            if date_from:
                from datetime import datetime
                try:
                    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
                    lessons_queryset = lessons_queryset.filter(lesson_date__gte=date_from_parsed)
                except ValueError:
                    pass  # Invalid date format, ignore filter

            if date_to:
                from datetime import datetime
                try:
                    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
                    lessons_queryset = lessons_queryset.filter(lesson_date__lte=date_to_parsed)
                except ValueError:
                    pass  # Invalid date format, ignore filter

            # Paginate lessons (20 per page)
            paginator = Paginator(lessons_queryset, 20)
            page = self.request.GET.get('page')

            try:
                lessons_page = paginator.page(page)
            except PageNotAnInteger:
                lessons_page = paginator.page(1)
            except EmptyPage:
                lessons_page = paginator.page(paginator.num_pages)

            context['lessons'] = lessons_page
            context['lessons_total'] = lessons_queryset.count()
            context['subject_filter'] = subject_filter
            context['date_from'] = date_from
            context['date_to'] = date_to

            # ===== TIMELINE SECTION =====
            # Build a unified timeline of all content organized by lesson
            timeline_data = []

            # Get all lessons with their content for this student (most recent first)
            timeline_lessons = Lesson.objects.filter(
                teacher=self.request.user,
                student=student,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).select_related('subject').prefetch_related(
                'lesson_pieces__piece',
                'lesson_collections__collection__collection_memberships',
                'lesson_assignments__assignment'
            ).order_by('-lesson_date', '-lesson_time')[:20]  # Limit to recent 20 lessons

            for lesson in timeline_lessons:
                lesson_entry = {
                    'lesson': lesson,
                    'date': lesson.lesson_date,
                    'subject': lesson.subject.subject if lesson.subject else 'No Subject',
                    'items': []
                }

                # Add playalong pieces
                for lp in lesson.lesson_pieces.all():
                    lesson_entry['items'].append({
                        'type': 'piece',
                        'icon': 'fa-music',
                        'color': 'success',
                        'title': lp.piece.title,
                        'subtitle': 'Playalong Piece',
                        'is_visible': lp.is_visible,
                        'is_optional': lp.is_optional,
                    })

                # Add playalong collections
                for lc in lesson.lesson_collections.all():
                    piece_count = lc.collection.collection_memberships.count()
                    lesson_entry['items'].append({
                        'type': 'collection',
                        'icon': 'fa-folder',
                        'color': 'primary',
                        'title': lc.collection.title,
                        'subtitle': f'Collection ({piece_count} pieces)',
                        'is_visible': lc.is_visible,
                        'is_optional': False,
                    })

                # Add assignments from this lesson
                for la in lesson.lesson_assignments.all():
                    # Use submission property (effective_student = lesson.student for lesson-linked)
                    submission = la.submission
                    status = 'not_started'
                    grade_display = '—'

                    if submission:
                        if submission.status == 'graded':
                            status = 'graded'
                            grade_display = la.assignment.format_grade(submission.grade) if submission.grade else '—'
                        elif submission.status == 'submitted':
                            status = 'submitted'
                        else:
                            status = 'in_progress'

                    lesson_entry['items'].append({
                        'type': 'assignment',
                        'icon': 'fa-file-alt',
                        'color': 'warning',
                        'title': la.assignment.title,
                        'subtitle': f'Assignment - {status.replace("_", " ").title()}',
                        'status': status,
                        'grade': grade_display,
                        'due_date': la.due_date,
                    })

                # Only add lesson to timeline if it has content
                if lesson_entry['items']:
                    timeline_data.append(lesson_entry)

            # Also add quizzes (not lesson-scoped, so add separately with their due dates)
            standalone_quizzes = []
            for quiz_assign in quiz_assignments:
                best_attempt = quiz_assign.best_attempt
                score_display = f"{best_attempt.score}%" if best_attempt and best_attempt.score is not None else '—'
                status = 'passed' if quiz_assign.passed else ('completed' if quiz_assign.status == 'completed' else 'pending')

                standalone_quizzes.append({
                    'type': 'quiz',
                    'icon': 'fa-question-circle',
                    'color': 'info',
                    'title': quiz_assign.quiz.title,
                    'subtitle': f'Quiz - {status.title()}',
                    'status': status,
                    'score': score_display,
                    'due_date': quiz_assign.due_date,
                    'assigned_date': quiz_assign.assigned_date,
                })

            context['timeline_data'] = timeline_data
            context['standalone_quizzes'] = standalone_quizzes

            # ===== AURAL TRAINING SECTION =====
            # Wrapped in try/except to gracefully handle if app not installed or migrations not run
            try:
                from apps.aural_training.models import StudentIntervalProgress, AuralTrainingSession

                # Get aural training progress for this student
                aural_progress = StudentIntervalProgress.objects.filter(
                    student=student
                ).order_by('interval')

                aural_total_attempts = sum(p.attempts for p in aural_progress)
                aural_total_correct = sum(p.correct for p in aural_progress)
                aural_accuracy = round((aural_total_correct / aural_total_attempts * 100), 1) if aural_total_attempts > 0 else 0
                aural_intervals_mastered = sum(1 for p in aural_progress if p.is_mastered)
                aural_intervals_unlocked = sum(1 for p in aural_progress if p.unlocked)

                # Get recent sessions
                recent_aural_sessions = AuralTrainingSession.objects.filter(
                    student=student
                ).order_by('-started_at')[:5]

                last_aural_practice = recent_aural_sessions.first().started_at if recent_aural_sessions.exists() else None

                context['aural_progress'] = aural_progress
                context['aural_total_attempts'] = aural_total_attempts
                context['aural_accuracy'] = aural_accuracy
                context['aural_intervals_mastered'] = aural_intervals_mastered
                context['aural_intervals_unlocked'] = aural_intervals_unlocked
                context['recent_aural_sessions'] = recent_aural_sessions
                context['last_aural_practice'] = last_aural_practice
            except Exception:
                # Aural training app not available or not migrated - set defaults
                context['aural_progress'] = []
                context['aural_total_attempts'] = 0
                context['aural_accuracy'] = 0
                context['aural_intervals_mastered'] = 0
                context['aural_intervals_unlocked'] = 0
                context['recent_aural_sessions'] = []
                context['last_aural_practice'] = None

            # ===== NAVIGATION =====
            # Get all students for this teacher (for next/previous navigation)
            all_student_ids = list(Lesson.objects.filter(
                teacher=self.request.user,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).order_by('student__profile__last_name', 'student__profile__first_name').values_list('student__id', flat=True).distinct())

            try:
                current_index = all_student_ids.index(student_id)
                context['next_student_id'] = all_student_ids[current_index + 1] if current_index < len(all_student_ids) - 1 else None
                context['previous_student_id'] = all_student_ids[current_index - 1] if current_index > 0 else None
            except (ValueError, IndexError):
                context['next_student_id'] = None
                context['previous_student_id'] = None

        except User.DoesNotExist:
            raise Http404("Student not found")

        return context


class TeacherLessonDetailView(TeacherProfileCompletedMixin, TemplateView):
    """
    Detailed view of a specific lesson for teachers.
    Shows lesson information, content, notes, and related materials.
    """
    template_name = 'private_teaching/teacher_lesson_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson_id = kwargs.get('lesson_id')

        try:
            from lessons.models import Lesson
            # Get lesson and verify teacher owns it
            lesson = Lesson.objects.select_related(
                'subject', 'student', 'student__profile', 'lesson_request__child_profile'
            ).prefetch_related(
                'lesson_pieces__piece',
                'lesson_assignments__assignment'
            ).get(id=lesson_id, teacher=self.request.user, is_deleted=False)

            context['lesson'] = lesson

            # Get student info
            context['student'] = lesson.student
            child_profile = None
            if lesson.lesson_request and lesson.lesson_request.child_profile:
                child_profile = lesson.lesson_request.child_profile
            context['child_profile'] = child_profile

            # Get lesson pieces (playalongs)
            lesson_pieces = lesson.lesson_pieces.filter(is_visible=True).order_by('order')
            context['lesson_pieces'] = lesson_pieces

            # Get lesson assignments (homework)
            lesson_assignments = lesson.lesson_assignments.all().order_by('order')
            context['lesson_assignments'] = lesson_assignments

            # Get documents and URLs attached to this lesson
            from lessons.models import Document, LessonAttachedUrl
            documents = Document.objects.filter(lesson=lesson).order_by('-uploaded_at')
            urls = LessonAttachedUrl.objects.filter(lesson=lesson).order_by('-created_at')
            context['documents'] = documents
            context['urls'] = urls

        except Lesson.DoesNotExist:
            from django.core.exceptions import PermissionDenied
            from django.http import Http404
            raise Http404("Lesson not found")

        return context


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
        if lesson.fee and lesson.payment_status == 'completed':
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

        is_teacher_initiated = (
            cancellation_request.initiated_by == LessonCancellationRequest.INITIATED_BY_TEACHER
        )
        is_pending_reschedule = (
            is_teacher_initiated
            and cancellation_request.request_type == LessonCancellationRequest.RESCHEDULE
            and is_pending
        )

        context = {
            'cancellation_request': cancellation_request,
            'lesson': cancellation_request.lesson,
            'is_teacher': is_teacher,
            'is_student': request.user == cancellation_request.student,
            'is_teacher_initiated': is_teacher_initiated,
            'is_pending_reschedule': is_pending_reschedule,
            'is_student_view': (request.user == cancellation_request.student),
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


class TeacherInitiateCancellationView(TeacherProfileCompletedMixin, View):
    """
    Teacher cancels or proposes a reschedule for an auto-accepted lesson.

    Cancel:    Immediate — lesson soft-deleted, full refund if paid. No student approval.
    Reschedule: Proposal — student is notified and must Accept or Decline.
    """
    template_name = 'private_teaching/teacher_initiate_cancellation.html'

    def get_lesson(self, lesson_id, teacher):
        lesson = get_object_or_404(Lesson, id=lesson_id, is_deleted=False)
        if lesson.teacher != teacher:
            raise PermissionDenied("You can only cancel your own lessons.")
        from lessons.models import Lesson as LessonModel
        if lesson.approved_status != LessonModel.ApprovalStatus.ACCEPTED:
            messages.error(self.request, "Only accepted lessons can be cancelled or rescheduled here.")
            return None
        return lesson

    def get(self, request, *args, **kwargs):
        lesson = self.get_lesson(kwargs['lesson_id'], request.user)
        if lesson is None:
            return redirect('private_teaching:teacher_schedule')
        # Check for already-pending teacher request
        existing = LessonCancellationRequest.objects.filter(
            lesson=lesson,
            initiated_by=LessonCancellationRequest.INITIATED_BY_TEACHER,
            status=LessonCancellationRequest.PENDING
        ).first()
        return render(request, self.template_name, {
            'form': TeacherInitiateCancellationForm(),
            'lesson': lesson,
            'existing_request': existing,
        })

    def post(self, request, *args, **kwargs):
        lesson = self.get_lesson(kwargs['lesson_id'], request.user)
        if lesson is None:
            return redirect('private_teaching:teacher_schedule')

        # Block if a pending teacher-initiated request already exists
        if LessonCancellationRequest.objects.filter(
            lesson=lesson,
            initiated_by=LessonCancellationRequest.INITIATED_BY_TEACHER,
            status=LessonCancellationRequest.PENDING
        ).exists():
            messages.error(request, "A pending reschedule proposal already exists for this lesson.")
            return redirect('private_teaching:teacher_schedule')

        form = TeacherInitiateCancellationForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'lesson': lesson})

        action = form.cleaned_data['action']
        reason = form.cleaned_data['reason']

        if action == 'cancel':
            cancellation_request = LessonCancellationRequest.objects.create(
                lesson=lesson,
                student=lesson.student,
                teacher=request.user,
                initiated_by=LessonCancellationRequest.INITIATED_BY_TEACHER,
                request_type=LessonCancellationRequest.CANCEL_WITH_REFUND,
                reason=reason,
                status=LessonCancellationRequest.COMPLETED,
                completed_at=timezone.now(),
            )

            # Process full refund if lesson was paid (teacher fault = no platform fee retained)
            if lesson.payment_status == 'completed' and lesson.fee:
                from apps.payments.models import StripePayment
                from apps.payments.stripe_service import create_refund
                try:
                    order_item = OrderItem.objects.filter(lesson=lesson).select_related('order').first()
                    if order_item and order_item.order.stripe_payment_intent_id:
                        stripe_payment = StripePayment.objects.get(
                            stripe_payment_intent_id=order_item.order.stripe_payment_intent_id
                        )
                        create_refund(
                            payment_intent_id=stripe_payment.stripe_payment_intent_id,
                            amount=lesson.fee,
                            reason='requested_by_customer',
                            metadata={
                                'cancellation_request_id': str(cancellation_request.id),
                                'lesson_id': str(lesson.id),
                                'refund_type': 'teacher_initiated_cancellation',
                            }
                        )
                        cancellation_request.refund_amount = lesson.fee
                        cancellation_request.platform_fee_retained = 0
                        cancellation_request.refund_processed_at = timezone.now()
                        cancellation_request.save(update_fields=[
                            'refund_amount', 'platform_fee_retained', 'refund_processed_at'
                        ])
                        messages.success(
                            request,
                            f'Lesson cancelled and full refund of £{lesson.fee} processed.'
                        )
                    else:
                        messages.warning(request, 'Lesson cancelled. No payment record found — please process any refund manually.')
                except StripePayment.DoesNotExist:
                    messages.warning(request, 'Lesson cancelled. Payment record not found — please process any refund manually.')
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Refund error on teacher cancel: {e}")
                    messages.error(request, f'Lesson cancelled but refund failed: {e}. Please process manually in Stripe.')
            else:
                messages.success(request, 'Lesson cancelled and student notified.')

            lesson.is_deleted = True
            lesson.save()

            try:
                StudentNotificationService.send_teacher_initiated_cancellation_notification(
                    cancellation_request, lesson
                )
            except Exception as e:
                print(f"Error sending teacher cancellation email: {e}")

            return redirect('private_teaching:teacher_cancellation_requests')

        else:  # reschedule
            cancellation_request = LessonCancellationRequest.objects.create(
                lesson=lesson,
                student=lesson.student,
                teacher=request.user,
                initiated_by=LessonCancellationRequest.INITIATED_BY_TEACHER,
                request_type=LessonCancellationRequest.RESCHEDULE,
                reason=reason,
                proposed_new_date=form.cleaned_data['proposed_new_date'],
                proposed_new_time=form.cleaned_data['proposed_new_time'],
                status=LessonCancellationRequest.PENDING,
            )

            try:
                StudentNotificationService.send_teacher_reschedule_proposal_notification(
                    cancellation_request, lesson
                )
            except Exception as e:
                print(f"Error sending reschedule proposal email: {e}")

            messages.success(
                request,
                f'Reschedule proposal sent to {lesson.student.get_full_name() or lesson.student.username}. '
                f'They will be asked to accept or decline.'
            )
            return redirect(
                'private_teaching:cancellation_request_detail',
                request_id=cancellation_request.id
            )


class StudentRespondToTeacherRescheduleView(StudentProfileCompletedMixin, StudentOnlyMixin, View):
    """
    Student accepts or declines a teacher-proposed reschedule.
    Accept  → lesson date/time updated, request completed, teacher notified.
    Decline → request rejected, original lesson time kept, teacher notified.
    """

    def post(self, request, *args, **kwargs):
        cancellation_request = get_object_or_404(
            LessonCancellationRequest,
            id=kwargs['request_id'],
            student=request.user,
            initiated_by=LessonCancellationRequest.INITIATED_BY_TEACHER,
            request_type=LessonCancellationRequest.RESCHEDULE,
            status=LessonCancellationRequest.PENDING,
        )

        action = request.POST.get('action')
        lesson = cancellation_request.lesson

        if action == 'accept':
            lesson.lesson_date = cancellation_request.proposed_new_date
            lesson.lesson_time = cancellation_request.proposed_new_time
            lesson.save()

            cancellation_request.status = LessonCancellationRequest.COMPLETED
            cancellation_request.completed_at = timezone.now()
            cancellation_request.save()

            try:
                TeacherNotificationService.send_student_reschedule_response_notification(
                    cancellation_request, lesson, accepted=True
                )
            except Exception as e:
                print(f"Error sending reschedule response email: {e}")

            messages.success(
                request,
                f'Lesson rescheduled to {lesson.lesson_date.strftime("%B %d, %Y")} '
                f'at {lesson.lesson_time.strftime("%I:%M %p")}.'
            )

        elif action == 'decline':
            cancellation_request.status = LessonCancellationRequest.REJECTED
            cancellation_request.save()

            try:
                TeacherNotificationService.send_student_reschedule_response_notification(
                    cancellation_request, lesson, accepted=False
                )
            except Exception as e:
                print(f"Error sending reschedule response email: {e}")

            messages.info(request, 'Reschedule declined. Your original lesson time is kept.')

        else:
            messages.error(request, 'Invalid action.')

        return redirect('private_teaching:cancellation_request_detail', request_id=cancellation_request.id)


# ============================================================================
# QUIZ SYSTEM VIEWS
# ============================================================================

# -----------------------------
# Teacher: Quiz Library & Management
# -----------------------------

# Quiz views moved to apps.quizzes.views


# ============================================================================
# STUDENT PLAYALONG ASSIGNMENT VIEWS
# ============================================================================

class AssignPlayalongView(TeacherProfileCompletedMixin, View):
    """Assign pieces and/or collections to a student."""

    def post(self, request, student_id):
        student = get_object_or_404(User, id=student_id)

        # Verify teacher has lessons with this student
        if not Lesson.objects.filter(
            teacher=request.user, student=student,
            approved_status=Lesson.ApprovalStatus.ACCEPTED, is_deleted=False
        ).exists():
            raise PermissionDenied()

        piece_ids = request.POST.getlist('piece_ids')
        collection_ids = request.POST.getlist('collection_ids')

        # Get child_profile if this is a child student
        child_profile = None
        lesson_with_child = Lesson.objects.filter(
            teacher=request.user, student=student,
            approved_status=Lesson.ApprovalStatus.ACCEPTED, is_deleted=False
        ).select_related('lesson_request__child_profile').first()
        if lesson_with_child and lesson_with_child.lesson_request:
            child_profile = lesson_with_child.lesson_request.child_profile

        created_piece_ids = []
        created_collection_ids = []

        for piece_id in piece_ids:
            _, created = StudentPieceAssignment.objects.get_or_create(
                student=student, piece_id=piece_id, teacher=request.user,
                defaults={'child_profile': child_profile}
            )
            if created:
                created_piece_ids.append(piece_id)

        for collection_id in collection_ids:
            _, created = StudentCollectionAssignment.objects.get_or_create(
                student=student, collection_id=collection_id, teacher=request.user,
                defaults={'child_profile': child_profile}
            )
            if created:
                created_collection_ids.append(collection_id)

        created_count = len(created_piece_ids) + len(created_collection_ids)

        if created_count:
            messages.success(request, f"Assigned {created_count} item{'s' if created_count != 1 else ''} to student.")
            from apps.audioplayer.models import Piece, PieceCollection
            new_pieces = list(Piece.objects.filter(id__in=created_piece_ids)) if created_piece_ids else []
            new_collections = list(PieceCollection.objects.filter(id__in=created_collection_ids)) if created_collection_ids else []
            StudentNotificationService.send_playalong_assignment_notification(
                student=student,
                teacher=request.user,
                new_pieces=new_pieces,
                new_collections=new_collections,
            )
        else:
            messages.info(request, "All selected items were already assigned.")

        return redirect(
            reverse('private_teaching:teacher_student_progress', kwargs={'student_id': student_id})
            + '?filter=playalongs'
        )


class RemovePlayalongAssignmentView(TeacherProfileCompletedMixin, View):
    """Remove a piece or collection assignment from a student."""

    def post(self, request, student_id, assignment_id):
        assignment_type = request.POST.get('type', 'piece')

        if assignment_type == 'collection':
            assignment = get_object_or_404(
                StudentCollectionAssignment, id=assignment_id, teacher=request.user
            )
        else:
            assignment = get_object_or_404(
                StudentPieceAssignment, id=assignment_id, teacher=request.user
            )

        assignment.delete()
        messages.success(request, "Assignment removed.")

        return redirect(
            reverse('private_teaching:teacher_student_progress', kwargs={'student_id': student_id})
            + '?filter=playalongs'
        )


class UpdatePlayalongStatusView(TeacherProfileCompletedMixin, View):
    """Update the status of a student's playalong assignment."""

    def post(self, request, student_id, assignment_id):
        assignment_type = request.POST.get('type', 'piece')
        new_status = request.POST.get('status', 'active')

        if new_status not in ('active', 'completed', 'archived'):
            messages.error(request, "Invalid status.")
            return redirect(
                reverse('private_teaching:teacher_student_progress', kwargs={'student_id': student_id})
                + '?filter=playalongs'
            )

        if assignment_type == 'collection':
            assignment = get_object_or_404(
                StudentCollectionAssignment, id=assignment_id, teacher=request.user
            )
        else:
            assignment = get_object_or_404(
                StudentPieceAssignment, id=assignment_id, teacher=request.user
            )

        assignment.status = new_status
        if new_status == 'completed' and not assignment.completed_at:
            assignment.completed_at = timezone.now()
        elif new_status == 'active':
            assignment.completed_at = None
        assignment.save()

        return redirect(
            reverse('private_teaching:teacher_student_progress', kwargs={'student_id': student_id})
            + '?filter=playalongs'
        )