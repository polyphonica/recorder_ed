import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from apps.private_teaching.mixins import TeacherProfileCompletedMixin, StudentProfileCompletedMixin

from .forms import (
    SessionGradeForm, SightReadingAssignmentForm,
    SightReadingExampleForm, SightReadingSetForm,
)
from .models import (
    SightReadingAssignment, SightReadingExample,
    SightReadingResult, SightReadingSet, SightReadingSetItem,
)


# ---------------------------------------------------------------------------
# Example library views (teacher)
# ---------------------------------------------------------------------------

class ExampleLibraryView(TeacherProfileCompletedMixin, ListView):
    template_name = 'sight_reading/example_library.html'
    context_object_name = 'examples'
    paginate_by = 24

    def get_queryset(self):
        qs = SightReadingExample.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        ).select_related('created_by')
        q = self.request.GET.get('q', '').strip()
        grade = self.request.GET.get('grade', '').strip()
        ownership = self.request.GET.get('ownership', '')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(grade_level__icontains=q))
        if grade:
            qs = qs.filter(grade_level=grade)
        if ownership == 'mine':
            qs = qs.filter(created_by=self.request.user)
        elif ownership == 'public':
            qs = qs.filter(is_public=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['grade'] = self.request.GET.get('grade', '')
        ctx['ownership'] = self.request.GET.get('ownership', '')
        ctx['grade_levels'] = (
            SightReadingExample.objects.filter(
                Q(created_by=self.request.user) | Q(is_public=True)
            ).exclude(grade_level='').values_list('grade_level', flat=True).distinct().order_by('grade_level')
        )
        return ctx


class ExampleCreateView(TeacherProfileCompletedMixin, CreateView):
    template_name = 'sight_reading/example_form.html'
    form_class = SightReadingExampleForm

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        instance = form.save()
        messages.success(self.request, f'"{instance.title}" added to your library.')
        return redirect('sight_reading:example_detail', pk=instance.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Upload Example'
        return ctx


class ExampleDetailView(TeacherProfileCompletedMixin, DetailView):
    template_name = 'sight_reading/example_detail.html'
    context_object_name = 'example'

    def get_queryset(self):
        return SightReadingExample.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_owner'] = self.object.created_by == self.request.user
        ctx['sets_using'] = (
            SightReadingSet.objects.filter(items__example=self.object)
            .filter(Q(created_by=self.request.user) | Q(is_public=True))
            .distinct()
        )
        return ctx


class ExampleEditView(TeacherProfileCompletedMixin, UpdateView):
    template_name = 'sight_reading/example_form.html'
    form_class = SightReadingExampleForm

    def get_queryset(self):
        return SightReadingExample.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        instance = form.save()
        messages.success(self.request, 'Example updated.')
        return redirect('sight_reading:example_detail', pk=instance.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Example'
        return ctx


class ExampleDeleteView(TeacherProfileCompletedMixin, DeleteView):
    template_name = 'sight_reading/example_confirm_delete.html'
    context_object_name = 'example'

    def get_queryset(self):
        return SightReadingExample.objects.filter(created_by=self.request.user)

    def get_success_url(self):
        return reverse('sight_reading:example_library')

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.title}" deleted.')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Set management views (teacher)
# ---------------------------------------------------------------------------

class SetLibraryView(TeacherProfileCompletedMixin, ListView):
    template_name = 'sight_reading/set_library.html'
    context_object_name = 'sets'

    def get_queryset(self):
        return (
            SightReadingSet.objects.filter(
                Q(created_by=self.request.user) | Q(is_public=True)
            )
            .select_related('created_by')
            .prefetch_related('items')
        )


class SetCreateView(TeacherProfileCompletedMixin, CreateView):
    template_name = 'sight_reading/set_form.html'
    form_class = SightReadingSetForm

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        instance = form.save()
        messages.success(self.request, f'"{instance.name}" created. Add examples below.')
        return redirect('sight_reading:set_detail', pk=instance.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Create Set'
        return ctx


class SetDetailView(TeacherProfileCompletedMixin, TemplateView):
    template_name = 'sight_reading/set_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sr_set = get_object_or_404(
            SightReadingSet,
            pk=self.kwargs['pk'],
        )
        if sr_set.created_by != self.request.user and not sr_set.is_public:
            raise PermissionDenied

        items = sr_set.items.select_related('example').order_by('order')
        existing_example_ids = items.values_list('example_id', flat=True)

        # Examples available to add (teacher's own + public, not already in set)
        available = SightReadingExample.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        ).exclude(id__in=existing_example_ids).order_by('title')

        ctx['sr_set'] = sr_set
        ctx['items'] = items
        ctx['available_examples'] = available
        ctx['is_owner'] = sr_set.created_by == self.request.user
        return ctx


class SetEditView(TeacherProfileCompletedMixin, UpdateView):
    template_name = 'sight_reading/set_form.html'
    form_class = SightReadingSetForm

    def get_queryset(self):
        return SightReadingSet.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        instance = form.save()
        messages.success(self.request, 'Set updated.')
        return redirect('sight_reading:set_detail', pk=instance.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Set'
        return ctx


class SetDeleteView(TeacherProfileCompletedMixin, DeleteView):
    template_name = 'sight_reading/set_confirm_delete.html'
    context_object_name = 'sr_set'

    def get_queryset(self):
        return SightReadingSet.objects.filter(created_by=self.request.user)

    def get_success_url(self):
        return reverse('sight_reading:set_library')

    def form_valid(self, form):
        if self.object.assignments.filter(is_unlocked=True).exists():
            messages.error(self.request, 'Cannot delete a set with an active (unlocked) session.')
            return redirect('sight_reading:set_detail', pk=self.object.pk)
        messages.success(self.request, f'"{self.object.name}" deleted.')
        return super().form_valid(form)


class SetAddExampleView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk):
        sr_set = get_object_or_404(SightReadingSet, pk=pk, created_by=request.user)
        example_id = request.POST.get('example_id')
        if not example_id:
            messages.error(request, 'No example selected.')
            return redirect('sight_reading:set_detail', pk=pk)

        example = get_object_or_404(
            SightReadingExample,
            pk=example_id,
        )
        # Ensure teacher has access to this example
        if example.created_by != request.user and not example.is_public:
            raise PermissionDenied

        max_order = sr_set.items.count()
        SightReadingSetItem.objects.get_or_create(
            set=sr_set,
            example=example,
            defaults={'order': max_order},
        )
        messages.success(request, f'"{example.title}" added to set.')
        return redirect('sight_reading:set_detail', pk=pk)


class SetRemoveExampleView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk, item_pk):
        sr_set = get_object_or_404(SightReadingSet, pk=pk, created_by=request.user)
        item = get_object_or_404(SightReadingSetItem, pk=item_pk, set=sr_set)
        item.delete()
        # Renumber remaining items
        for i, remaining in enumerate(sr_set.items.order_by('order')):
            if remaining.order != i:
                remaining.order = i
                remaining.save(update_fields=['order'])
        messages.success(request, 'Example removed from set.')
        return redirect('sight_reading:set_detail', pk=pk)


class SetReorderView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk):
        get_object_or_404(SightReadingSet, pk=pk, created_by=request.user)
        try:
            data = json.loads(request.body)
            item_ids = data.get('order', [])
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

        for idx, item_id in enumerate(item_ids):
            SightReadingSetItem.objects.filter(
                pk=item_id, set__created_by=request.user
            ).update(order=idx)

        return JsonResponse({'status': 'ok'})


# ---------------------------------------------------------------------------
# Assignment views (teacher)
# ---------------------------------------------------------------------------

class AssignmentListView(TeacherProfileCompletedMixin, ListView):
    template_name = 'sight_reading/assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        qs = SightReadingAssignment.objects.filter(
            teacher=self.request.user
        ).select_related('sight_reading_set', 'student', 'child_profile', 'lesson')

        if self.request.GET.get('needs_repeat') == '1':
            qs = qs.filter(needs_repeat=True)
        student_id = self.request.GET.get('student')
        if student_id:
            qs = qs.filter(student_id=student_id)

        return qs.prefetch_related('results')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['needs_repeat_filter'] = self.request.GET.get('needs_repeat') == '1'
        ctx['needs_repeat_count'] = SightReadingAssignment.objects.filter(
            teacher=self.request.user, needs_repeat=True
        ).count()
        return ctx


class AssignmentCreateView(TeacherProfileCompletedMixin, View):
    template_name = 'sight_reading/assignment_form.html'

    def get(self, request):
        form = SightReadingAssignmentForm(teacher=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SightReadingAssignmentForm(request.POST, teacher=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = request.user
            assignment.save()
            messages.success(request, f'Set "{assignment.sight_reading_set.name}" assigned to {assignment.student_display}.')
            return redirect('sight_reading:assignment_list')
        return render(request, self.template_name, {'form': form})


class AssignmentDetailView(TeacherProfileCompletedMixin, TemplateView):
    template_name = 'sight_reading/assignment_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assignment = get_object_or_404(
            SightReadingAssignment, pk=self.kwargs['pk'], teacher=self.request.user
        )
        results = list(assignment.results.select_related('example').order_by('order'))
        correct_count = sum(1 for r in results if r.result == 'correct')
        incorrect_count = sum(1 for r in results if r.result == 'incorrect')
        ungraded_count = sum(1 for r in results if r.result is None)

        ctx['assignment'] = assignment
        ctx['results'] = results
        ctx['correct_count'] = correct_count
        ctx['incorrect_count'] = incorrect_count
        ctx['ungraded_count'] = ungraded_count
        ctx['total'] = len(results)
        ctx['session_url'] = (
            reverse('sight_reading:session_exercise', args=[assignment.pk, 1])
            if results else None
        )
        return ctx


class AssignmentDeleteView(TeacherProfileCompletedMixin, DeleteView):
    template_name = 'sight_reading/assignment_confirm_delete.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        return SightReadingAssignment.objects.filter(teacher=self.request.user)

    def get_success_url(self):
        return reverse('sight_reading:assignment_list')

    def form_valid(self, form):
        messages.success(self.request, 'Assignment deleted.')
        return super().form_valid(form)


class AssignmentToggleLockView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk):
        assignment = get_object_or_404(SightReadingAssignment, pk=pk, teacher=request.user)

        if not assignment.is_unlocked:
            # Unlocking: create result stubs if this is a fresh session
            if not assignment.results.exists():
                items = assignment.sight_reading_set.items.order_by('order').select_related('example')
                for i, item in enumerate(items, start=1):
                    SightReadingResult.objects.create(
                        assignment=assignment,
                        example=item.example,
                        order=i,
                    )
            assignment.is_unlocked = True
            messages.success(request, 'Session unlocked. Both you and your student can now access the exercises.')
        else:
            assignment.is_unlocked = False
            messages.success(request, 'Session locked.')

        assignment.save(update_fields=['is_unlocked'])
        return redirect('sight_reading:assignment_detail', pk=pk)


class AssignmentCompleteView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk):
        assignment = get_object_or_404(SightReadingAssignment, pk=pk, teacher=request.user)
        assignment.completed_at = timezone.now()
        assignment.is_unlocked = False
        assignment.needs_repeat = assignment.results.filter(result='incorrect').exists()
        assignment.save(update_fields=['completed_at', 'is_unlocked', 'needs_repeat'])

        if not assignment.needs_repeat:
            messages.success(request, 'Session complete — all exercises correct!')
        else:
            messages.warning(request, 'Session complete. This set needs repeating next lesson.')

        return redirect('sight_reading:assignment_detail', pk=pk)


class AssignmentNoteSaveView(TeacherProfileCompletedMixin, View):
    def post(self, request, pk):
        assignment = get_object_or_404(SightReadingAssignment, pk=pk, teacher=request.user)
        assignment.notes = request.POST.get('notes', '')
        assignment.save(update_fields=['notes'])
        return JsonResponse({'status': 'ok'})


# ---------------------------------------------------------------------------
# Session views (teacher + student shared)
# ---------------------------------------------------------------------------

class SessionExerciseView(LoginRequiredMixin, View):
    def get(self, request, pk, position):
        assignment = get_object_or_404(SightReadingAssignment, pk=pk)
        is_teacher = (assignment.teacher == request.user)
        is_student = (assignment.student == request.user)

        if not (is_teacher or is_student):
            raise PermissionDenied

        if not assignment.is_unlocked:
            template = 'sight_reading/session/locked_teacher.html' if is_teacher else 'sight_reading/session/locked_student.html'
            return render(request, template, {'assignment': assignment})

        results = list(assignment.results.order_by('order').select_related('example'))
        total = len(results)

        if total == 0:
            messages.error(request, 'This set has no exercises.')
            if is_teacher:
                return redirect('sight_reading:assignment_detail', pk=pk)
            return redirect('sight_reading:student_assignments')

        if position < 1 or position > total:
            return redirect('sight_reading:session_exercise', pk=pk, position=max(1, min(position, total)))

        result = results[position - 1]

        grade_form = None
        if is_teacher:
            grade_form = SessionGradeForm(initial={
                'result': result.result or '',
                'teacher_note': result.teacher_note,
                'next_position': position + 1,
            })

        ctx = {
            'assignment': assignment,
            'result': result,
            'example': result.example,
            'position': position,
            'total': total,
            'is_teacher': is_teacher,
            'prev_url': reverse('sight_reading:session_exercise', args=[pk, position - 1]) if position > 1 else None,
            'next_url': reverse('sight_reading:session_exercise', args=[pk, position + 1]) if position < total else None,
            'grade_form': grade_form,
        }
        return render(request, 'sight_reading/session/exercise.html', ctx)


class SessionGradeView(LoginRequiredMixin, View):
    def post(self, request, pk, position):
        assignment = get_object_or_404(SightReadingAssignment, pk=pk, teacher=request.user)

        if not assignment.is_unlocked:
            messages.error(request, 'Session is locked.')
            return redirect('sight_reading:assignment_detail', pk=pk)

        results = list(assignment.results.order_by('order'))
        total = len(results)

        if position < 1 or position > total:
            return redirect('sight_reading:assignment_detail', pk=pk)

        result = results[position - 1]
        form = SessionGradeForm(request.POST)

        if form.is_valid():
            result.result = form.cleaned_data['result'] or None
            result.teacher_note = form.cleaned_data['teacher_note']
            if result.result and not result.played_at:
                result.played_at = timezone.now()
            result.save(update_fields=['result', 'teacher_note', 'played_at'])

            next_pos = form.cleaned_data['next_position']
            if next_pos <= total:
                return redirect('sight_reading:session_exercise', pk=pk, position=next_pos)
            return redirect('sight_reading:assignment_detail', pk=pk)

        # Form invalid — redisplay
        return redirect('sight_reading:session_exercise', pk=pk, position=position)


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------

class StudentAssignmentListView(StudentProfileCompletedMixin, ListView):
    template_name = 'sight_reading/student_assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        return (
            SightReadingAssignment.objects.filter(student=self.request.user)
            .select_related('sight_reading_set', 'teacher__profile', 'child_profile')
            .prefetch_related('results')
            .order_by('-assigned_at')
        )
