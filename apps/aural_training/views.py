from itertools import groupby

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q


class StudentTrainingView(LoginRequiredMixin, TemplateView):
    """
    Main aural training interface for students.
    Serves the adapted POC as a Django template.
    """
    template_name = 'aural_training/student_training.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Pass API base URL for JS
        context['api_base_url'] = '/aural-training/api/'

        # For child profile selection if user is a guardian
        if hasattr(self.request.user, 'profile') and self.request.user.profile.is_guardian:
            from apps.accounts.models import ChildProfile
            context['child_profiles'] = ChildProfile.objects.filter(
                guardian=self.request.user
            )

        return context


class StudentProgressView(LoginRequiredMixin, TemplateView):
    """
    Shows student's aural training progress summary.
    """
    template_name = 'aural_training/student_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import StudentIntervalProgress, AuralTrainingSession

        # Get progress data
        context['interval_progress'] = StudentIntervalProgress.objects.filter(
            student=self.request.user
        ).order_by('interval')

        # Get recent sessions
        context['recent_sessions'] = AuralTrainingSession.objects.filter(
            student=self.request.user
        ).order_by('-started_at')[:10]

        return context


# ---------------------------------------------------------------------------
# Aural Tests tab
# ---------------------------------------------------------------------------

class AuralTestsView(LoginRequiredMixin, TemplateView):
    template_name = 'aural_training/aural_tests.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import AuralTestSet
        from apps.private_teaching.models import TeacherStudentApplication

        user = self.request.user
        is_teacher = hasattr(user, 'profile') and user.profile.is_teacher

        if is_teacher:
            test_sets = AuralTestSet.objects.filter(
                Q(is_shared=True) | Q(created_by=user)
            ).prefetch_related('tests').select_related('created_by')
        else:
            teacher_ids = TeacherStudentApplication.objects.filter(
                applicant=user, status='accepted'
            ).values_list('teacher_id', flat=True)
            test_sets = AuralTestSet.objects.filter(
                Q(is_shared=True) | Q(created_by_id__in=teacher_ids)
            ).prefetch_related('tests').select_related('created_by')

        context['test_sets'] = test_sets
        context['is_teacher'] = is_teacher
        return context


# ---------------------------------------------------------------------------
# Test Set CRUD (teachers only)
# ---------------------------------------------------------------------------

def _require_teacher(request):
    """Return True if user is a teacher, otherwise redirect with error."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
        messages.error(request, 'Only teachers can manage aural test sets.')
        return False
    return True


@login_required
def aural_test_set_create(request):
    if not _require_teacher(request):
        return redirect('aural_training:aural_tests')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_shared = request.POST.get('is_shared') == 'on'
        order = request.POST.get('order', '0').strip() or '0'

        errors = []
        if not name:
            errors.append('Name is required.')
        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            from .models import AuralTestSet
            AuralTestSet.objects.create(
                name=name,
                description=description,
                created_by=request.user,
                is_shared=is_shared,
                order=order,
            )
            messages.success(request, f'Test set "{name}" created.')
            return redirect('aural_training:aural_tests')

    return render(request, 'aural_training/aural_test_set_form.html', {'action': 'Create'})


@login_required
def aural_test_set_edit(request, pk):
    from .models import AuralTestSet
    test_set = get_object_or_404(AuralTestSet, pk=pk)

    if not _require_teacher(request):
        return redirect('aural_training:aural_tests')
    if test_set.created_by != request.user:
        messages.error(request, 'You can only edit your own test sets.')
        return redirect('aural_training:aural_tests')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_shared = request.POST.get('is_shared') == 'on'
        order = request.POST.get('order', '0').strip() or '0'

        errors = []
        if not name:
            errors.append('Name is required.')
        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            test_set.name = name
            test_set.description = description
            test_set.is_shared = is_shared
            test_set.order = order
            test_set.save()
            messages.success(request, f'Test set "{name}" updated.')
            return redirect('aural_training:aural_tests')

    return render(request, 'aural_training/aural_test_set_form.html', {
        'action': 'Edit',
        'test_set': test_set,
    })


@login_required
def aural_test_set_delete(request, pk):
    from .models import AuralTestSet
    test_set = get_object_or_404(AuralTestSet, pk=pk)

    if not _require_teacher(request):
        return redirect('aural_training:aural_tests')
    if test_set.created_by != request.user:
        messages.error(request, 'You can only delete your own test sets.')
        return redirect('aural_training:aural_tests')

    if request.method == 'POST':
        name = test_set.name
        test_set.delete()
        messages.success(request, f'Test set "{name}" deleted.')
    return redirect('aural_training:aural_tests')


# ---------------------------------------------------------------------------
# Test CRUD (teachers only)
# ---------------------------------------------------------------------------

@login_required
def aural_test_create(request, set_pk):
    from .models import AuralTestSet
    test_set = get_object_or_404(AuralTestSet, pk=set_pk)

    if not _require_teacher(request):
        return redirect('aural_training:aural_tests')
    if test_set.created_by != request.user:
        messages.error(request, 'You can only add tests to your own sets.')
        return redirect('aural_training:aural_tests')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        instructions = request.POST.get('instructions', '').strip()
        audio_file = request.FILES.get('audio_file')
        order = request.POST.get('order', '0').strip() or '0'

        errors = []
        if not title:
            errors.append('Title is required.')
        if not instructions:
            errors.append('Instructions are required.')
        if not audio_file:
            errors.append('Please upload an audio file.')
        elif not audio_file.name.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
            errors.append('Accepted formats: MP3, WAV, OGG, M4A.')
        elif audio_file.size > 50 * 1024 * 1024:
            errors.append('File must be under 50MB.')
        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            from .models import AuralTest
            AuralTest.objects.create(
                test_set=test_set,
                title=title,
                instructions=instructions,
                audio_file=audio_file,
                order=order,
            )
            messages.success(request, f'Test "{title}" added to {test_set.name}.')
            return redirect('aural_training:aural_tests')

    return render(request, 'aural_training/aural_test_form.html', {
        'action': 'Add',
        'test_set': test_set,
    })


@login_required
def aural_test_edit(request, pk):
    from .models import AuralTest
    test = get_object_or_404(AuralTest, pk=pk)
    test_set = test.test_set

    if not _require_teacher(request):
        return redirect('aural_training:aural_tests')
    if test_set.created_by != request.user:
        messages.error(request, 'You can only edit tests in your own sets.')
        return redirect('aural_training:aural_tests')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        instructions = request.POST.get('instructions', '').strip()
        audio_file = request.FILES.get('audio_file')
        order = request.POST.get('order', '0').strip() or '0'

        errors = []
        if not title:
            errors.append('Title is required.')
        if not instructions:
            errors.append('Instructions are required.')
        if audio_file:
            if not audio_file.name.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                errors.append('Accepted formats: MP3, WAV, OGG, M4A.')
            elif audio_file.size > 50 * 1024 * 1024:
                errors.append('File must be under 50MB.')
        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            test.title = title
            test.instructions = instructions
            test.order = order
            if audio_file:
                test.audio_file = audio_file
            test.save()
            messages.success(request, f'Test "{title}" updated.')
            return redirect('aural_training:aural_tests')

    return render(request, 'aural_training/aural_test_form.html', {
        'action': 'Edit',
        'test_set': test_set,
        'test': test,
    })


# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------

class GlossaryView(LoginRequiredMixin, TemplateView):
    template_name = 'aural_training/glossary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import GlossaryTerm
        from apps.private_teaching.models import TeacherStudentApplication

        user = self.request.user
        is_teacher = hasattr(user, 'profile') and user.profile.is_teacher

        if is_teacher:
            terms = GlossaryTerm.objects.filter(
                Q(is_shared=True) | Q(created_by=user)
            ).select_related('created_by')
        else:
            teacher_ids = TeacherStudentApplication.objects.filter(
                applicant=user, status='accepted'
            ).values_list('teacher_id', flat=True)
            terms = GlossaryTerm.objects.filter(
                Q(is_shared=True) | Q(created_by_id__in=teacher_ids)
            ).select_related('created_by')

        grouped = []
        for grade, items in groupby(terms, key=lambda t: t.grade):
            grouped.append({
                'grade': grade,
                'grade_label': f'Grade {grade}' if grade else 'General',
                'terms': list(items),
            })

        context['grouped_terms'] = grouped
        context['is_teacher'] = is_teacher
        return context


@login_required
def glossary_term_create(request):
    if not _require_teacher(request):
        return redirect('aural_training:glossary')

    if request.method == 'POST':
        term = request.POST.get('term', '').strip()
        definition = request.POST.get('definition', '').strip()
        grade = request.POST.get('grade', '').strip() or None
        is_shared = request.POST.get('is_shared') == 'on'
        order = request.POST.get('order', '0').strip() or '0'

        errors = []
        if not term:
            errors.append('Term is required.')
        if not definition:
            errors.append('Definition is required.')
        if grade is not None:
            try:
                grade = int(grade)
                if not 1 <= grade <= 8:
                    raise ValueError
            except ValueError:
                errors.append('Grade must be between 1 and 8.')
                grade = None
        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            from .models import GlossaryTerm
            GlossaryTerm.objects.create(
                term=term,
                definition=definition,
                grade=grade,
                created_by=request.user,
                is_shared=is_shared,
                order=order,
            )
            messages.success(request, f'"{term}" added to the glossary.')
            return redirect('aural_training:glossary')

    from .models import GRADE_CHOICES
    return render(request, 'aural_training/glossary_term_form.html', {
        'action': 'Add',
        'grade_choices': GRADE_CHOICES,
    })


@login_required
def glossary_term_edit(request, pk):
    from .models import GlossaryTerm
    glossary_term = get_object_or_404(GlossaryTerm, pk=pk)

    if not _require_teacher(request):
        return redirect('aural_training:glossary')
    if glossary_term.created_by != request.user:
        messages.error(request, 'You can only edit your own glossary terms.')
        return redirect('aural_training:glossary')

    if request.method == 'POST':
        term = request.POST.get('term', '').strip()
        definition = request.POST.get('definition', '').strip()
        grade = request.POST.get('grade', '').strip() or None
        is_shared = request.POST.get('is_shared') == 'on'
        order = request.POST.get('order', '0').strip() or '0'

        errors = []
        if not term:
            errors.append('Term is required.')
        if not definition:
            errors.append('Definition is required.')
        if grade is not None:
            try:
                grade = int(grade)
                if not 1 <= grade <= 8:
                    raise ValueError
            except ValueError:
                errors.append('Grade must be between 1 and 8.')
                grade = None
        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            glossary_term.term = term
            glossary_term.definition = definition
            glossary_term.grade = grade
            glossary_term.is_shared = is_shared
            glossary_term.order = order
            glossary_term.save()
            messages.success(request, f'"{term}" updated.')
            return redirect('aural_training:glossary')

    from .models import GRADE_CHOICES
    return render(request, 'aural_training/glossary_term_form.html', {
        'action': 'Edit',
        'glossary_term': glossary_term,
        'grade_choices': GRADE_CHOICES,
    })


@login_required
def glossary_term_delete(request, pk):
    from .models import GlossaryTerm
    glossary_term = get_object_or_404(GlossaryTerm, pk=pk)

    if not _require_teacher(request):
        return redirect('aural_training:glossary')
    if glossary_term.created_by != request.user:
        messages.error(request, 'You can only delete your own glossary terms.')
        return redirect('aural_training:glossary')

    if request.method == 'POST':
        term = glossary_term.term
        glossary_term.delete()
        messages.success(request, f'"{term}" removed from the glossary.')
    return redirect('aural_training:glossary')


@login_required
def aural_test_delete(request, pk):
    from .models import AuralTest
    test = get_object_or_404(AuralTest, pk=pk)

    if not _require_teacher(request):
        return redirect('aural_training:aural_tests')
    if test.test_set.created_by != request.user:
        messages.error(request, 'You can only delete tests in your own sets.')
        return redirect('aural_training:aural_tests')

    if request.method == 'POST':
        title = test.title
        test.delete()
        messages.success(request, f'Test "{title}" deleted.')
    return redirect('aural_training:aural_tests')
