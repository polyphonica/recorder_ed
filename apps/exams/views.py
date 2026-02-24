from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.core.views import BaseCheckoutSuccessView, BaseCheckoutCancelView, UserFilterMixin
from apps.private_teaching.mixins import (
    PrivateTeachingLoginRequiredMixin,
    TeacherProfileCompletedMixin,
    StudentProfileCompletedMixin,
)
from lessons.models import Lesson
from .models import ExamBoard, ExamRegistration, ExamPiece
from .forms import ExamRegistrationForm, ExamPieceFormSet, ExamResultsForm
from .notifications import ExamNotificationService


class ExamRegistrationListView(UserFilterMixin, PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, ListView):
    """List all exam registrations for a teacher."""
    model = ExamRegistration
    template_name = 'exams/list.html'
    context_object_name = 'exams'
    paginate_by = 20
    user_field_name = 'teacher'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'student', 'child_profile', 'subject', 'exam_board'
        ).prefetch_related('pieces')

        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-exam_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        status_filter = self.request.GET.get('status')
        if status_filter:
            context['status_filter'] = status_filter

        all_exams = ExamRegistration.objects.filter(
            teacher=self.request.user
        ).select_related('student', 'child_profile', 'subject', 'exam_board').prefetch_related('pieces')

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
    template_name = 'exams/create.html'

    def get(self, request):
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

                pieces = piece_formset.save(commit=False)
                for piece in pieces:
                    piece.exam_registration = exam
                    piece.save()

                for obj in piece_formset.deleted_objects:
                    obj.delete()

                messages.success(request, f'Exam registration created for {exam.student_name}!')
                ExamNotificationService.send_exam_registration_notification(exam)
                return redirect('exams:exam_detail', pk=exam.id)

        return render(request, self.template_name, {
            'form': form,
            'piece_formset': piece_formset,
        })


class ExamRegistrationDetailView(PrivateTeachingLoginRequiredMixin, View):
    """View exam registration details"""
    template_name = 'exams/detail.html'

    def get(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk)

        if request.user == exam.teacher:
            is_teacher = True
        elif request.user == exam.student or (exam.child_profile and request.user == exam.child_profile.guardian):
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
    template_name = 'exams/edit.html'

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

                pieces = piece_formset.save(commit=False)
                for piece in pieces:
                    piece.exam_registration = exam
                    piece.save()

                for obj in piece_formset.deleted_objects:
                    obj.delete()

                messages.success(request, 'Exam registration updated!')
                return redirect('exams:exam_detail', pk=exam.id)

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
        return redirect('exams:exam_list')


class ExamResultsUpdateView(PrivateTeachingLoginRequiredMixin, TeacherProfileCompletedMixin, View):
    """Update exam results"""
    template_name = 'exams/results.html'

    def get(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)
        form = ExamResultsForm(instance=exam)
        return render(request, self.template_name, {'exam': exam, 'form': form})

    def post(self, request, pk):
        exam = get_object_or_404(ExamRegistration, pk=pk, teacher=request.user)
        form = ExamResultsForm(request.POST, instance=exam)

        if form.is_valid():
            exam = form.save()
            messages.success(request, 'Exam results updated!')
            ExamNotificationService.send_exam_results_notification(exam)
            return redirect('exams:exam_detail', pk=exam.id)

        return render(request, self.template_name, {'exam': exam, 'form': form})


class StudentExamListView(PrivateTeachingLoginRequiredMixin, StudentProfileCompletedMixin, ListView):
    """List all exams for a student"""
    model = ExamRegistration
    template_name = 'exams/student_list.html'
    context_object_name = 'exams'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        return ExamRegistration.objects.filter(
            Q(student=user) | Q(child_profile__guardian=user)
        ).select_related(
            'teacher', 'subject', 'exam_board', 'child_profile'
        ).prefetch_related('pieces').order_by('-exam_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        all_exams = ExamRegistration.objects.filter(
            Q(student=user) | Q(child_profile__guardian=user)
        ).select_related('teacher', 'subject', 'exam_board', 'child_profile').prefetch_related('pieces')

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

        if not (request.user == exam.student or
                (exam.child_profile and request.user == exam.child_profile.guardian)):
            messages.error(request, 'You do not have permission to pay for this exam.')
            return redirect('private_teaching:home')

        if exam.is_paid:
            messages.info(request, 'This exam has already been paid for.')
            return redirect('exams:exam_detail', pk=exam.id)

        if not exam.requires_payment or exam.payment_amount <= 0:
            messages.error(request, 'No payment is required for this exam.')
            return redirect('exams:exam_detail', pk=exam.id)

        from apps.payments.stripe_service import create_checkout_session

        try:
            success_url = request.build_absolute_uri(
                reverse('exams:exam_payment_success', kwargs={'pk': exam.id})
            )
            cancel_url = request.build_absolute_uri(
                reverse('exams:exam_payment_cancel', kwargs={'pk': exam.id})
            )

            metadata = {
                'exam_id': str(exam.id),
                'student_id': str(exam.student.id),
                'teacher_id': str(exam.teacher.id),
            }

            checkout_session = create_checkout_session(
                amount=exam.payment_amount,
                student=exam.student,
                teacher=exam.teacher,
                domain='private_teaching',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
                item_name=f'Exam Registration: {exam.display_name}',
                item_description=f'{exam.student_name} - {exam.exam_board} {exam.get_grade_type_display()} Grade {exam.grade_level}'
            )

            exam.stripe_checkout_session_id = checkout_session.id
            exam.payment_status = 'pending'
            exam.save()

            return redirect(checkout_session.url)

        except Exception as e:
            messages.error(request, f'Error creating payment session: {str(e)}')
            return redirect('exams:exam_detail', pk=exam.id)


class ExamPaymentSuccessView(BaseCheckoutSuccessView):
    """Handle successful exam payment"""
    template_name = 'core/checkout_success.html'

    def get_object_model(self):
        return ExamRegistration

    def get_object_id_kwarg(self):
        return 'pk'

    def get_redirect_url_name(self):
        return 'exams:student_exams'

    def perform_post_checkout_actions(self, exam):
        if exam.payment_status != 'completed':
            exam.payment_status = 'completed'
            exam.paid_at = timezone.now()
            exam.save(update_fields=['payment_status', 'paid_at'])

    def get_context_extras(self, exam):
        return {
            'exam': exam,
            'student_name': exam.student_name,
            'success_message': f'Payment successful! Your exam registration for {exam.display_name} is confirmed.',
            'detail_url': reverse('exams:exam_detail', kwargs={'pk': exam.id}),
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
        return 'exams:exam_detail'
