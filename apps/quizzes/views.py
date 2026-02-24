"""
Views for the unified Quiz system (private lesson quizzes).
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, ListView, TemplateView, UpdateView,
)
from django import forms as django_forms

from .models import Quiz, QuizQuestion, QuizAnswer, QuizAssignment, QuizAttempt
from .forms import (
    QuizForm, QuizQuestionForm, QuizAnswerForm,
    QuizAnswerFormSet, QuizAssignmentForm,
)
from apps.private_teaching.mixins import (
    TeacherProfileCompletedMixin,
    AcceptedStudentRequiredMixin,
)
from apps.private_teaching.models import Subject, TeacherStudentApplication
from apps.quizzes.notifications import (
    QuizTeacherNotificationService, QuizStudentNotificationService,
)

User = get_user_model()


# ============================================================================
# Teacher: Quiz Library & Management
# ============================================================================

class QuizLibraryView(TeacherProfileCompletedMixin, ListView):
    """Teacher's quiz library - browse, search, and filter quizzes."""
    model = Quiz
    template_name = 'quizzes/quiz_library.html'
    context_object_name = 'quizzes'
    paginate_by = 20

    def get_queryset(self):
        queryset = Quiz.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True),
            course_lesson__isnull=True,  # private lesson quizzes only
        ).select_related('created_by', 'subject').prefetch_related('tags')

        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()

        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        syllabus = self.request.GET.get('syllabus')
        if syllabus:
            queryset = queryset.filter(syllabus=syllabus)

        grade = self.request.GET.get('grade')
        if grade:
            queryset = queryset.filter(grade_level__icontains=grade)

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
    """Create new private lesson quiz."""
    model = Quiz
    form_class = QuizForm
    template_name = 'quizzes/quiz_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Quiz "{form.instance.title}" created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('quizzes:quiz_detail', kwargs={'pk': self.object.pk})


class QuizDetailView(TeacherProfileCompletedMixin, TemplateView):
    """View quiz details with questions and statistics."""
    template_name = 'quizzes/quiz_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = get_object_or_404(Quiz, pk=kwargs['pk'])

        if quiz.created_by != self.request.user and not quiz.is_public:
            messages.error(self.request, 'You do not have permission to view this quiz.')
            return redirect('quizzes:quiz_library')

        context['quiz'] = quiz
        context['questions'] = quiz.questions.prefetch_related('answers').order_by('order')
        context['is_owner'] = quiz.created_by == self.request.user

        if context['is_owner']:
            assignments = quiz.assignments.select_related('student').all()
            context['total_assignments'] = assignments.count()
            context['completed_assignments'] = assignments.filter(status='completed').count()
            context['recent_assignments'] = assignments.order_by('-assigned_date')[:5]

        return context


class QuizEditView(TeacherProfileCompletedMixin, UpdateView):
    """Edit existing quiz."""
    model = Quiz
    form_class = QuizForm
    template_name = 'quizzes/quiz_form.html'

    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Quiz "{form.instance.title}" updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('quizzes:quiz_detail', kwargs={'pk': self.object.pk})


class QuizDeleteView(TeacherProfileCompletedMixin, DeleteView):
    """Delete quiz (with confirmation)."""
    model = Quiz
    template_name = 'quizzes/quiz_confirm_delete.html'
    success_url = reverse_lazy('quizzes:quiz_library')

    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        quiz = self.get_object()
        messages.success(request, f'Quiz "{quiz.title}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class QuizDuplicateView(TeacherProfileCompletedMixin, View):
    """Duplicate an existing quiz with all questions and answers."""

    def post(self, request, *args, **kwargs):
        original_quiz = get_object_or_404(Quiz, pk=kwargs['pk'])

        if original_quiz.created_by != request.user and not original_quiz.is_public:
            messages.error(request, 'You do not have permission to duplicate this quiz.')
            return redirect('quizzes:quiz_library')

        try:
            with transaction.atomic():
                new_quiz = Quiz.objects.create(
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
                    is_public=False,
                )
                new_quiz.tags.set(original_quiz.tags.all())

                for question in original_quiz.questions.all():
                    new_question = QuizQuestion.objects.create(
                        quiz=new_quiz,
                        text=question.text,
                        order=question.order,
                        points=question.points,
                        explanation=question.explanation,
                    )
                    for answer in question.answers.all():
                        QuizAnswer.objects.create(
                            question=new_question,
                            text=answer.text,
                            is_correct=answer.is_correct,
                            order=answer.order,
                        )

            messages.success(request, f'Quiz duplicated successfully as "{new_quiz.title}"')
            return redirect('quizzes:quiz_detail', pk=new_quiz.pk)

        except Exception as e:
            messages.error(request, f'Error duplicating quiz: {str(e)}')
            return redirect('quizzes:quiz_library')


# ============================================================================
# Teacher: Question Management
# ============================================================================

class QuestionCreateView(TeacherProfileCompletedMixin, TemplateView):
    """Create question with inline answer formset."""
    template_name = 'quizzes/question_form.html'

    def get_answer_formset_class(self):
        return django_forms.inlineformset_factory(
            QuizQuestion, QuizAnswer,
            form=QuizAnswerForm,
            extra=3, max_num=10, can_delete=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = get_object_or_404(Quiz, pk=kwargs['quiz_id'], created_by=self.request.user)
        context['quiz'] = quiz
        context['form'] = QuizQuestionForm()
        context['formset'] = self.get_answer_formset_class()()
        return context

    def post(self, request, *args, **kwargs):
        quiz = get_object_or_404(Quiz, pk=kwargs['quiz_id'], created_by=request.user)
        form = QuizQuestionForm(request.POST)
        formset_class = self.get_answer_formset_class()

        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            formset = formset_class(request.POST, instance=question)

            if formset.is_valid():
                correct_answers = sum(
                    1 for f in formset
                    if f.cleaned_data
                    and not f.cleaned_data.get('DELETE', False)
                    and f.cleaned_data.get('is_correct', False)
                )
                if correct_answers == 0:
                    messages.error(request, 'At least one answer must be marked as correct.')
                    return render(request, self.template_name, {
                        'quiz': quiz, 'form': form, 'formset': formset
                    })

                with transaction.atomic():
                    question.save()
                    formset.instance = question
                    answers = formset.save(commit=False)
                    for index, answer in enumerate(answers):
                        answer.order = index
                        answer.save()
                    for obj in formset.deleted_objects:
                        obj.delete()

                messages.success(request, 'Question added successfully!')
                return redirect('quizzes:quiz_detail', pk=quiz.pk)
        else:
            formset = formset_class(request.POST)

        return render(request, self.template_name, {
            'quiz': quiz, 'form': form, 'formset': formset
        })


class QuestionEditView(TeacherProfileCompletedMixin, TemplateView):
    """Edit question with inline answer formset."""
    template_name = 'quizzes/question_form.html'

    def get_answer_formset_class_edit(self):
        return django_forms.inlineformset_factory(
            QuizQuestion, QuizAnswer,
            form=QuizAnswerForm,
            extra=0, max_num=10, can_delete=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = get_object_or_404(
            QuizQuestion, pk=kwargs['pk'], quiz__created_by=self.request.user
        )
        context['quiz'] = question.quiz
        context['question'] = question
        context['form'] = QuizQuestionForm(instance=question)
        context['formset'] = self.get_answer_formset_class_edit()(instance=question)
        return context

    def post(self, request, *args, **kwargs):
        question = get_object_or_404(
            QuizQuestion, pk=kwargs['pk'], quiz__created_by=request.user
        )
        form = QuizQuestionForm(request.POST, instance=question)
        formset_class = self.get_answer_formset_class_edit()
        formset = formset_class(request.POST, instance=question)

        if form.is_valid() and formset.is_valid():
            correct_answers = sum(
                1 for f in formset
                if f.cleaned_data
                and not f.cleaned_data.get('DELETE', False)
                and f.cleaned_data.get('is_correct', False)
            )
            if correct_answers == 0:
                messages.error(request, 'At least one answer must be marked as correct.')
                return render(request, self.template_name, {
                    'quiz': question.quiz, 'question': question,
                    'form': form, 'formset': formset
                })

            with transaction.atomic():
                form.save()
                answers = formset.save(commit=False)
                for index, answer in enumerate(answers):
                    answer.order = index
                    answer.save()
                for obj in formset.deleted_objects:
                    obj.delete()

            messages.success(request, 'Question updated successfully!')
            return redirect('quizzes:quiz_detail', pk=question.quiz.pk)

        return render(request, self.template_name, {
            'quiz': question.quiz, 'question': question,
            'form': form, 'formset': formset
        })


class QuestionDeleteView(TeacherProfileCompletedMixin, DeleteView):
    """Delete question."""
    model = QuizQuestion

    def get_queryset(self):
        return QuizQuestion.objects.filter(quiz__created_by=self.request.user)

    def get_success_url(self):
        return reverse('quizzes:quiz_detail', kwargs={'pk': self.object.quiz.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Question deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# Teacher: Quiz Assignments
# ============================================================================

class QuizAssignView(TeacherProfileCompletedMixin, CreateView):
    """Assign quiz to a private lesson student."""
    model = QuizAssignment
    form_class = QuizAssignmentForm
    template_name = 'quizzes/quiz_assign.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        quiz_id = self.kwargs.get('quiz_id')
        if quiz_id:
            quiz = get_object_or_404(Quiz, pk=quiz_id, created_by=self.request.user)
            initial['quiz'] = quiz
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        quiz_id = self.kwargs.get('quiz_id')
        if quiz_id:
            form.instance.quiz = get_object_or_404(
                Quiz, pk=quiz_id, created_by=self.request.user
            )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz_id = self.kwargs.get('quiz_id')
        if quiz_id:
            context['quiz'] = get_object_or_404(
                Quiz, pk=quiz_id, created_by=self.request.user
            )
        return context

    def form_valid(self, form):
        try:
            form.instance.teacher = self.request.user

            quiz_id = self.kwargs.get('quiz_id')
            if quiz_id:
                form.instance.quiz = get_object_or_404(
                    Quiz, pk=quiz_id, created_by=self.request.user
                )

            parsed_student = form.cleaned_data.get('_parsed_student')
            parsed_child = form.cleaned_data.get('_parsed_child_profile')

            if parsed_child:
                student_name = parsed_child.full_name
            elif parsed_student:
                student_name = parsed_student.get_full_name() or parsed_student.username
            else:
                student_name = 'Unknown Student'

            response = super().form_valid(form)
            messages.success(self.request, f'Quiz assigned to {student_name} successfully!')
            QuizStudentNotificationService.send_quiz_assignment_notification(self.object)
            return response
        except Exception as e:
            messages.error(self.request, f'Error assigning quiz: {str(e)}')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('quizzes:quiz_assignment_list')


class QuizAssignmentListView(TeacherProfileCompletedMixin, ListView):
    """Teacher's list of all quiz assignments."""
    model = QuizAssignment
    template_name = 'quizzes/quiz_assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        queryset = QuizAssignment.objects.filter(
            teacher=self.request.user
        ).select_related(
            'quiz', 'student', 'child_profile', 'lesson'
        ).prefetch_related('attempts')

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        quiz_id = self.request.GET.get('quiz')
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)

        return queryset.order_by('-assigned_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accepted_apps = TeacherStudentApplication.objects.filter(
            teacher=self.request.user,
            status='accepted'
        ).values_list('applicant_id', flat=True)
        context['students'] = User.objects.filter(id__in=accepted_apps).order_by('first_name', 'last_name')
        context['quizzes'] = Quiz.objects.filter(created_by=self.request.user).order_by('-created_at')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_student'] = self.request.GET.get('student', '')
        context['selected_quiz'] = self.request.GET.get('quiz', '')
        return context


class QuizAssignmentDetailView(TeacherProfileCompletedMixin, TemplateView):
    """View assignment details with all attempts."""
    template_name = 'quizzes/quiz_assignment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = get_object_or_404(
            QuizAssignment, pk=kwargs['pk'], teacher=self.request.user
        )
        context['assignment'] = assignment
        context['attempts'] = assignment.attempts.order_by('-started_at')

        if context['attempts']:
            scores = [a.score for a in context['attempts'] if a.submitted_at]
            if scores:
                context['best_score'] = max(scores)
                context['average_score'] = sum(scores) / len(scores)
                context['passed_attempts'] = sum(1 for a in context['attempts'] if a.passed)

        return context


class QuizAssignmentDeleteView(TeacherProfileCompletedMixin, DeleteView):
    """Delete assignment."""
    model = QuizAssignment
    template_name = 'quizzes/quiz_assignment_confirm_delete.html'
    success_url = reverse_lazy('quizzes:quiz_assignment_list')

    def get_queryset(self):
        return QuizAssignment.objects.filter(teacher=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Assignment deleted successfully.')
        return super().delete(request, *args, **kwargs)


class TeacherQuizAttemptResultsView(TeacherProfileCompletedMixin, TemplateView):
    """Teacher view for student quiz results."""
    template_name = 'quizzes/quiz_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = get_object_or_404(QuizAttempt, pk=kwargs['pk'])

        if attempt.assignment.teacher != self.request.user:
            messages.error(self.request, 'You do not have permission to view this quiz attempt.')
            return redirect('private_teaching:teacher_dashboard')

        context['attempt'] = attempt
        context['assignment'] = attempt.assignment
        context['quiz'] = attempt.assignment.quiz
        context['is_teacher_view'] = True

        questions_data = []
        for question in attempt.assignment.quiz.questions.order_by('order'):
            question_id_str = str(question.id)
            student_answer = attempt.answers_data.get(question_id_str)

            if student_answer is None:
                student_answer_ids = []
            elif isinstance(student_answer, list):
                student_answer_ids = [str(a) for a in student_answer]
            else:
                student_answer_ids = [str(student_answer)]

            is_multi_answer = question.has_multiple_correct_answers()
            correct_answers = question.get_correct_answers()
            correct_answer_ids = [str(a.id) for a in correct_answers]

            question_info = {
                'question': question,
                'student_answer_ids': student_answer_ids,
                'is_multi_answer': is_multi_answer,
                'answers': question.answers.order_by('order'),
                'correct_answer_ids': correct_answer_ids,
                'is_correct': False,
            }

            if student_answer_ids:
                if is_multi_answer:
                    question_info['is_correct'] = set(student_answer_ids) == set(correct_answer_ids)
                else:
                    question_info['is_correct'] = student_answer_ids[0] in correct_answer_ids

            questions_data.append(question_info)

        context['questions_data'] = questions_data
        context['can_retake'] = False

        return context


# ============================================================================
# Student: Quiz Taking
# ============================================================================

class StudentQuizListView(AcceptedStudentRequiredMixin, ListView):
    """Student's assigned quizzes."""
    model = QuizAssignment
    template_name = 'quizzes/student_quiz_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        queryset = QuizAssignment.objects.filter(
            student=self.request.user
        ).select_related(
            'quiz', 'teacher', 'child_profile', 'lesson'
        ).prefetch_related('attempts')

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        child_id = self.request.GET.get('child')
        if child_id:
            queryset = queryset.filter(child_profile_id=child_id)

        return queryset.order_by('-assigned_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounts.models import ChildProfile
        context['child_profiles'] = ChildProfile.objects.filter(guardian=self.request.user)
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_child'] = self.request.GET.get('child', '')
        return context


class QuizTakeView(AcceptedStudentRequiredMixin, TemplateView):
    """Take quiz - show questions and collect answers."""
    template_name = 'quizzes/quiz_take.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        assignment = get_object_or_404(
            QuizAssignment,
            pk=kwargs['assignment_id'],
            student=self.request.user
        )

        if assignment.quiz.max_attempts:
            attempt_count = assignment.attempts.count()
            if attempt_count >= assignment.quiz.max_attempts:
                messages.error(self.request, 'You have reached the maximum number of attempts for this quiz.')
                return redirect('quizzes:student_quiz_list')

        if not assignment.quiz.questions.exists():
            messages.error(self.request, 'This quiz has no questions yet. Please contact your teacher.')
            return redirect('quizzes:student_quiz_list')

        context['assignment'] = assignment
        context['quiz'] = assignment.quiz
        questions = assignment.quiz.get_questions(randomize=assignment.quiz.randomize_questions)
        context['questions'] = questions

        existing_attempt = assignment.attempts.filter(
            submitted_at__isnull=True
        ).order_by('-started_at').first()

        if existing_attempt:
            attempt = existing_attempt
            context['is_resuming'] = True
            context['last_save_time'] = (
                existing_attempt.last_autosave_at.strftime('%I:%M %p')
                if existing_attempt.last_autosave_at
                else None
            )
        else:
            attempt = QuizAttempt.objects.create(assignment=assignment)
            context['is_resuming'] = False

        context['attempt'] = attempt

        if assignment.status == 'assigned':
            assignment.status = 'in_progress'
            assignment.save()

        return context


class QuizSubmitView(AcceptedStudentRequiredMixin, View):
    """Submit quiz answers (AJAX endpoint)."""

    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(
            QuizAssignment,
            pk=kwargs['assignment_id'],
            student=request.user
        )

        attempt_id = request.POST.get('attempt_id')
        if not attempt_id:
            return JsonResponse({'success': False, 'error': 'No attempt ID provided'}, status=400)

        attempt = get_object_or_404(QuizAttempt, pk=attempt_id, assignment=assignment)

        if attempt.submitted_at:
            return JsonResponse({'success': False, 'error': 'Quiz already submitted'}, status=400)

        try:
            with transaction.atomic():
                answers_data = {}
                processed_keys = set()
                for key in request.POST.keys():
                    if key.startswith('question_') and key not in processed_keys:
                        processed_keys.add(key)
                        if key.endswith('[]'):
                            question_id = key.replace('question_', '').replace('[]', '')
                            answers_data[question_id] = request.POST.getlist(key)
                        else:
                            question_id = key.replace('question_', '')
                            answers_data[question_id] = request.POST.get(key)

                attempt.answers_data = answers_data
                attempt.submitted_at = timezone.now()
                attempt.last_autosave_at = None

                time_taken = (attempt.submitted_at - attempt.started_at).total_seconds() / 60
                attempt.time_taken_minutes = int(time_taken)

                attempt.calculate_score()
                attempt.grade()
                attempt.save()

                assignment.status = 'completed'
                assignment.save()

            QuizTeacherNotificationService.send_quiz_submission_notification(attempt)

            return JsonResponse({
                'success': True,
                'score': float(attempt.score),
                'passed': attempt.passed,
                'redirect_url': reverse('quizzes:quiz_attempt_results', kwargs={'pk': attempt.pk})
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class QuizAutoSaveView(AcceptedStudentRequiredMixin, View):
    """Auto-save quiz answers without grading (AJAX endpoint)."""

    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(
            QuizAssignment,
            pk=kwargs['assignment_id'],
            student=request.user
        )

        attempt_id = request.POST.get('attempt_id')
        if not attempt_id:
            return JsonResponse({'success': False, 'error': 'No attempt ID provided'}, status=400)

        attempt = get_object_or_404(QuizAttempt, pk=attempt_id, assignment=assignment)

        if attempt.submitted_at:
            return JsonResponse({'success': False, 'error': 'Cannot auto-save submitted quiz'}, status=400)

        try:
            answers_data = {}
            processed_keys = set()
            for key in request.POST.keys():
                if key.startswith('question_') and key not in processed_keys:
                    processed_keys.add(key)
                    if key.endswith('[]'):
                        question_id = key.replace('question_', '').replace('[]', '')
                        answers_data[question_id] = request.POST.getlist(key)
                    else:
                        question_id = key.replace('question_', '')
                        answers_data[question_id] = request.POST.get(key)

            attempt.autosave_answers(answers_data)
            save_time = attempt.last_autosave_at.strftime('%I:%M %p')

            return JsonResponse({
                'success': True,
                'saved_at': save_time,
                'timestamp': attempt.last_autosave_at.isoformat(),
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class QuizAttemptResultsView(AcceptedStudentRequiredMixin, TemplateView):
    """View quiz results after submission."""
    template_name = 'quizzes/quiz_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        attempt = get_object_or_404(
            QuizAttempt,
            pk=kwargs['pk'],
            assignment__student=self.request.user
        )

        context['attempt'] = attempt
        context['assignment'] = attempt.assignment
        context['quiz'] = attempt.assignment.quiz

        questions_data = []
        for question in attempt.assignment.quiz.questions.order_by('order'):
            question_id_str = str(question.id)
            student_answer = attempt.answers_data.get(question_id_str)

            if student_answer is None:
                student_answer_ids = []
            elif isinstance(student_answer, list):
                student_answer_ids = [str(a) for a in student_answer]
            else:
                student_answer_ids = [str(student_answer)]

            is_multi_answer = question.has_multiple_correct_answers()
            correct_answers = question.get_correct_answers()
            correct_answer_ids = [str(a.id) for a in correct_answers]

            question_info = {
                'question': question,
                'student_answer_ids': student_answer_ids,
                'is_multi_answer': is_multi_answer,
                'answers': question.answers.order_by('order'),
                'correct_answer_ids': correct_answer_ids,
                'is_correct': False,
            }

            if student_answer_ids:
                if is_multi_answer:
                    question_info['is_correct'] = set(student_answer_ids) == set(correct_answer_ids)
                else:
                    question_info['is_correct'] = student_answer_ids[0] in correct_answer_ids

            questions_data.append(question_info)

        context['questions_data'] = questions_data
        context['can_retake'] = False
        if attempt.assignment.quiz.allow_retakes:
            if attempt.assignment.quiz.max_attempts:
                attempt_count = attempt.assignment.attempts.count()
                context['can_retake'] = attempt_count < attempt.assignment.quiz.max_attempts
            else:
                context['can_retake'] = True

        return context
