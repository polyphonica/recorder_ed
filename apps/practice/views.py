from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, View, UpdateView, DeleteView
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg

from apps.private_teaching.mixins import (
    StudentProfileCompletedMixin,
    StudentOnlyMixin,
    TeacherProfileCompletedMixin,
)
from lessons.models import Lesson
from .models import PracticeEntry
from .forms import PracticeEntryForm
from .notifications import PracticeNotificationService

User = get_user_model()


class LogPracticeView(StudentProfileCompletedMixin, StudentOnlyMixin, TemplateView):
    """Student logs a new practice session"""
    template_name = 'practice/log_practice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PracticeEntryForm(user=self.request.user)

        # Get teacher options for this student
        teacher_ids = Lesson.objects.filter(
            student=self.request.user,
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
                        approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
                                    approved_status=Lesson.ApprovalStatus.ACCEPTED,
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
                                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                                is_deleted=False
                            ).values_list('teacher__id', flat=True).distinct()
                        ).select_related('profile')
                    })

            practice_entry.save()

            if practice_entry.teacher:
                PracticeNotificationService.send_practice_logged_notification(practice_entry)

            # Show success message emphasizing exam/performance prep if applicable
            success_msg = 'Practice session logged successfully!'
            if practice_entry.preparing_for_exam:
                success_msg += ' Keep up the great exam preparation work!'
            elif practice_entry.preparing_for_performance:
                success_msg += ' Excellent performance preparation!'

            messages.success(request, success_msg)
            return redirect('practice:practice_log')

        return render(request, self.template_name, {
            'form': form,
            'teachers': User.objects.filter(
                id__in=Lesson.objects.filter(
                    student=request.user,
                    approved_status=Lesson.ApprovalStatus.ACCEPTED,
                    is_deleted=False
                ).values_list('teacher__id', flat=True).distinct()
            ).select_related('profile')
        })


class PracticeLogView(StudentProfileCompletedMixin, StudentOnlyMixin, ListView):
    """Student views their practice log history with statistics"""
    model = PracticeEntry
    template_name = 'practice/practice_log.html'
    context_object_name = 'practice_entries'
    paginate_by = 20

    def get_queryset(self):
        queryset = PracticeEntry.objects.filter(
            student=self.request.user
        ).select_related('teacher', 'teacher__profile', 'child_profile', 'lesson_request').order_by('-practice_date', '-created_at')

        child_id = self.request.GET.get('child')
        if child_id:
            queryset = queryset.filter(child_profile__id=child_id)

        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher__id=teacher_id)

        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            queryset = queryset.filter(preparing_for_exam=True)

        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            queryset = queryset.filter(preparing_for_performance=True)

        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(practice_date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(practice_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import timedelta, date

        all_entries = PracticeEntry.objects.filter(student=self.request.user)

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

        start_date = self.request.GET.get('start_date')
        if start_date:
            all_entries = all_entries.filter(practice_date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            all_entries = all_entries.filter(practice_date__lte=end_date)

        stats = all_entries.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes'),
            avg_enjoyment=Avg('enjoyment_rating')
        )

        seven_days_ago = date.today() - timedelta(days=7)
        last_week_stats = all_entries.filter(practice_date__gte=seven_days_ago).aggregate(
            sessions=Count('id'),
            minutes=Sum('duration_minutes')
        )

        prep_counts = all_entries.aggregate(
            exam_prep=Count('id', filter=Q(preparing_for_exam=True)),
            performance_prep=Count('id', filter=Q(preparing_for_performance=True))
        )

        context.update({
            'total_sessions': stats['total_sessions'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'total_hours': round((stats['total_minutes'] or 0) / 60, 1),
            'avg_duration': round(stats['avg_duration'] or 0),
            'avg_enjoyment': round(stats['avg_enjoyment'] or 0, 1) if stats['avg_enjoyment'] else None,
            'last_week_sessions': last_week_stats['sessions'] or 0,
            'last_week_minutes': last_week_stats['minutes'] or 0,
            'last_week_hours': round((last_week_stats['minutes'] or 0) / 60, 1),
            'exam_prep_count': prep_counts['exam_prep'],
            'performance_prep_count': prep_counts['performance_prep'],
        })

        if self.request.user.profile.is_guardian:
            from apps.accounts.models import ChildProfile
            context['children'] = ChildProfile.objects.filter(guardian=self.request.user)

        teacher_ids = PracticeEntry.objects.filter(
            student=self.request.user
        ).values_list('teacher__id', flat=True).distinct()
        context['teachers'] = User.objects.filter(id__in=teacher_ids).select_related('profile')

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
    template_name = 'practice/practice_log_print.html'
    context_object_name = 'practice_entries'

    def get_queryset(self):
        queryset = PracticeEntry.objects.filter(
            student=self.request.user
        ).select_related('teacher', 'teacher__profile', 'child_profile', 'lesson_request').order_by('-practice_date', '-created_at')

        child_id = self.request.GET.get('child')
        if child_id:
            queryset = queryset.filter(child_profile__id=child_id)

        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher__id=teacher_id)

        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            queryset = queryset.filter(preparing_for_exam=True)

        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            queryset = queryset.filter(preparing_for_performance=True)

        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(practice_date__gte=start_date)

        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(practice_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_entries = self.get_queryset()

        stats = all_entries.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes'),
            avg_enjoyment=Avg('enjoyment_rating')
        )

        prep_counts = all_entries.aggregate(
            exam_prep=Count('id', filter=Q(preparing_for_exam=True)),
            performance_prep=Count('id', filter=Q(preparing_for_performance=True))
        )

        context.update({
            'total_sessions': stats['total_sessions'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'total_hours': round((stats['total_minutes'] or 0) / 60, 1),
            'avg_duration': round(stats['avg_duration'] or 0),
            'avg_enjoyment': round(stats['avg_enjoyment'] or 0, 1) if stats['avg_enjoyment'] else None,
            'exam_prep_count': prep_counts['exam_prep'],
            'performance_prep_count': prep_counts['performance_prep'],
        })

        context['start_date_filter'] = self.request.GET.get('start_date')
        context['end_date_filter'] = self.request.GET.get('end_date')
        context['child_filter'] = self.request.GET.get('child')
        context['teacher_filter'] = self.request.GET.get('teacher')

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
    template_name = 'practice/teacher_student_practice.html'
    context_object_name = 'practice_entries'
    paginate_by = 20

    def get_student(self):
        student_id = self.kwargs.get('student_id')
        student = get_object_or_404(User, id=student_id)

        has_lessons = Lesson.objects.filter(
            teacher=self.request.user,
            student=student,
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
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

        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            queryset = queryset.filter(preparing_for_exam=True)

        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            queryset = queryset.filter(preparing_for_performance=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import timedelta, date

        student = self.get_student()
        context['viewed_student'] = student

        practice_entries = PracticeEntry.objects.filter(
            student=student,
            teacher=self.request.user
        ).select_related('child_profile')

        child_profiles = set()
        for entry in practice_entries:
            if entry.child_profile:
                child_profiles.add(entry.child_profile)

        if len(child_profiles) == 1:
            context['child_profile'] = list(child_profiles)[0]
            context['is_child_student'] = True
        else:
            context['is_child_student'] = False

        all_entries = PracticeEntry.objects.filter(
            student=student,
            teacher=self.request.user
        )

        exam_prep = self.request.GET.get('exam_prep')
        if exam_prep == 'yes':
            all_entries = all_entries.filter(preparing_for_exam=True)

        performance_prep = self.request.GET.get('performance_prep')
        if performance_prep == 'yes':
            all_entries = all_entries.filter(preparing_for_performance=True)

        stats = all_entries.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes'),
            avg_enjoyment=Avg('enjoyment_rating')
        )

        seven_days_ago = date.today() - timedelta(days=7)
        last_week_stats = all_entries.filter(practice_date__gte=seven_days_ago).aggregate(
            sessions=Count('id'),
            minutes=Sum('duration_minutes')
        )

        prep_counts = all_entries.aggregate(
            exam_prep=Count('id', filter=Q(preparing_for_exam=True)),
            performance_prep=Count('id', filter=Q(preparing_for_performance=True))
        )

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
            'exam_prep_count': prep_counts['exam_prep'],
            'performance_prep_count': prep_counts['performance_prep'],
        })

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
            PracticeNotificationService.send_practice_comment_notification(practice_entry)
        else:
            messages.error(request, 'Comment cannot be empty.')

        return redirect('practice:teacher_student_practice', student_id=practice_entry.student.id)


class EditPracticeView(StudentProfileCompletedMixin, StudentOnlyMixin, UpdateView):
    """Student edits their own practice entry"""
    model = PracticeEntry
    template_name = 'practice/log_practice.html'
    form_class = PracticeEntryForm

    def get_queryset(self):
        return PracticeEntry.objects.filter(student=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entry'] = self.object
        context['form'] = self.get_form()

        teacher_ids = Lesson.objects.filter(
            student=self.request.user,
            approved_status=Lesson.ApprovalStatus.ACCEPTED,
            is_deleted=False
        ).values_list('teacher__id', flat=True).distinct()

        context['teachers'] = User.objects.filter(id__in=teacher_ids).select_related('profile')
        return context

    def form_valid(self, form):
        teacher = form.cleaned_data.get('teacher')
        if teacher:
            has_lessons = Lesson.objects.filter(
                student=self.request.user,
                teacher=teacher,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False
            ).exists()

            if not has_lessons:
                form.add_error('teacher', 'You can only log practice for teachers you have accepted lessons with.')
                return self.form_invalid(form)

        messages.success(self.request, 'Practice entry updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('practice:practice_log')


class DeletePracticeView(StudentProfileCompletedMixin, StudentOnlyMixin, DeleteView):
    """Student deletes their own practice entry"""
    model = PracticeEntry

    def get_queryset(self):
        return PracticeEntry.objects.filter(student=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Practice entry deleted successfully.')
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('practice:practice_log')
