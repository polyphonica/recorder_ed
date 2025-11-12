from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Piece, Stem, LessonPiece
from .forms import PieceForm, StemFormSet
from apps.courses.models import Lesson


# ===== TEACHER VIEWS - Piece Library Management =====

@login_required
def piece_list(request):
    """List all pieces in the library"""
    # TODO: Add permission check for teachers only
    # if not request.user.profile.is_teacher:
    #     messages.error(request, 'Only teachers can access the piece library.')
    #     return redirect('courses:list')

    pieces = Piece.objects.prefetch_related('stems', 'lesson_assignments__lesson').all()

    context = {
        'pieces': pieces,
        'title': 'Playalong Piece Library'
    }
    return render(request, 'audioplayer/piece_list.html', context)


@login_required
@transaction.atomic
def piece_create(request):
    """Create new piece with stems"""
    # TODO: Add permission check for teachers only

    if request.method == 'POST':
        form = PieceForm(request.POST, request.FILES)
        formset = StemFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            piece = form.save()
            formset.instance = piece
            formset.save()
            messages.success(request, f'Piece "{piece.title}" created successfully!')
            return redirect('audioplayer:piece_list')
        else:
            if not form.is_valid():
                messages.error(request, f'Piece form errors: {form.errors}')
            if not formset.is_valid():
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        messages.error(request, f'Stem {i+1} errors: {form_errors}')
                if formset.non_form_errors():
                    messages.error(request, f'Formset errors: {formset.non_form_errors()}')
    else:
        form = PieceForm()
        formset = StemFormSet()

    context = {
        'form': form,
        'formset': formset,
        'title': 'Create New Piece',
        'submit_text': 'Create Piece'
    }
    return render(request, 'audioplayer/piece_form.html', context)


@login_required
@transaction.atomic
def piece_edit(request, pk):
    """Edit existing piece and its stems"""
    # TODO: Add permission check for teachers only

    piece = get_object_or_404(Piece, pk=pk)

    if request.method == 'POST':
        form = PieceForm(request.POST, request.FILES, instance=piece)
        formset = StemFormSet(request.POST, request.FILES, instance=piece)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Piece "{piece.title}" updated successfully!')
            return redirect('audioplayer:piece_list')
        else:
            if not form.is_valid():
                messages.error(request, f'Piece form errors: {form.errors}')
            if not formset.is_valid():
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        messages.error(request, f'Stem {i+1} errors: {form_errors}')
                if formset.non_form_errors():
                    messages.error(request, f'Formset errors: {formset.non_form_errors()}')
    else:
        form = PieceForm(instance=piece)
        formset = StemFormSet(instance=piece)

    # Get lessons using this piece
    lessons_using = piece.lesson_assignments.select_related('lesson__topic__course').all()

    context = {
        'form': form,
        'formset': formset,
        'piece': piece,
        'lessons_using': lessons_using,
        'title': f'Edit: {piece.title}',
        'submit_text': 'Update Piece'
    }
    return render(request, 'audioplayer/piece_form.html', context)


@login_required
def piece_delete(request, pk):
    """Delete piece (with safety check for usage in lessons)"""
    # TODO: Add permission check for teachers only

    piece = get_object_or_404(Piece, pk=pk)

    # Check if used in any lessons
    usage_count = piece.lesson_assignments.count()
    lessons_using = piece.lesson_assignments.select_related('lesson__topic__course').all()[:5]

    if request.method == 'POST':
        if usage_count > 0:
            messages.error(
                request,
                f'Cannot delete "{piece.title}". It is currently used in {usage_count} lesson(s). '
                f'Please remove it from all lessons first.'
            )
            return redirect('audioplayer:piece_edit', pk=pk)

        piece_title = piece.title
        piece.delete()
        messages.success(request, f'Piece "{piece_title}" deleted successfully.')
        return redirect('audioplayer:piece_list')

    context = {
        'piece': piece,
        'usage_count': usage_count,
        'lessons_using': lessons_using,
        'title': f'Delete: {piece.title}'
    }
    return render(request, 'audioplayer/piece_confirm_delete.html', context)


# ===== STUDENT VIEWS - Playback Interface =====

def audio_player(request, lesson_id):
    """Student playback interface for a lesson's playalong pieces"""
    lesson = get_object_or_404(Lesson, pk=lesson_id)

    # TODO: Add enrollment/access check
    # if not request.user.is_authenticated:
    #     return redirect('accounts:login')
    #
    # # Check if user is enrolled or is the instructor
    # is_enrolled = lesson.course.enrollments.filter(
    #     student=request.user,
    #     is_active=True
    # ).exists()
    # is_instructor = lesson.course.instructor == request.user
    #
    # if not (is_enrolled or is_instructor):
    #     messages.error(request, 'You must be enrolled in this course to access this lesson.')
    #     return redirect('courses:detail', slug=lesson.course.slug)

    # Get count of visible pieces
    piece_count = lesson.lesson_pieces.filter(is_visible=True).count()

    context = {
        'lesson': lesson,
        'piece_count': piece_count,
        'title': f'Playalong: {lesson.lesson_title}'
    }
    return render(request, 'audioplayer/audio_player.html', context)


def pieces_json(request, lesson_id):
    """
    JSON API endpoint for audio player JavaScript.
    Returns all visible pieces and stems for a lesson.
    """
    lesson = get_object_or_404(Lesson, pk=lesson_id)

    # TODO: Add same access check as audio_player view

    # Get pieces through the LessonPiece relationship
    lesson_pieces = LessonPiece.objects.filter(
        lesson=lesson,
        is_visible=True
    ).select_related('piece').prefetch_related('piece__stems').order_by('order')

    pieces_data = []
    for lp in lesson_pieces:
        # Get stems ordered by their order field
        stems_data = [
            {
                'audio_file': stem.audio_file.url,
                'instrument_name': stem.instrument_name
            }
            for stem in lp.piece.stems.all().order_by('order')
        ]

        piece_data = {
            'title': lp.piece.title,
            'stems': stems_data,
            'svg_image': lp.piece.svg_image.url if lp.piece.svg_image else None,
            'order': lp.order,
        }

        # Add lesson-specific customizations
        if lp.instructions:
            piece_data['instructions'] = lp.instructions
        if lp.is_optional:
            piece_data['is_optional'] = True

        pieces_data.append(piece_data)

    return JsonResponse({'pieces_data': pieces_data})


# ===== HELPER VIEWS =====

@login_required
def piece_detail(request, pk):
    """View details of a piece (for teachers)"""
    piece = get_object_or_404(Piece, pk=pk)
    stems = piece.stems.all().order_by('order')
    lessons_using = piece.lesson_assignments.select_related('lesson__topic__course').all()

    context = {
        'piece': piece,
        'stems': stems,
        'lessons_using': lessons_using,
        'title': piece.title
    }
    return render(request, 'audioplayer/piece_detail.html', context)


# ===== PRIVATE TEACHING LESSON VIEWS =====

@login_required
def private_lesson_player(request, lesson_id):
    """
    Audio player page for private teaching lessons.
    Accessible by the student or teacher once lesson status is 'Assigned'.
    """
    from lessons.models import Lesson as PrivateLesson

    lesson = get_object_or_404(PrivateLesson, pk=lesson_id)

    # Check access: user must be the student OR the teacher
    is_student = lesson.student == request.user
    is_teacher = lesson.teacher == request.user

    if not (is_student or is_teacher):
        messages.error(request, 'You do not have permission to access this lesson.')
        return redirect('lessons:lesson_list')

    # Check lesson status - only accessible when status is 'Assigned'
    if lesson.status != 'Assigned' and not is_teacher:
        messages.error(request, 'This lesson is not yet available. Playalong content will be accessible when the teacher assigns the lesson.')
        return redirect('lessons:lesson_detail', pk=lesson_id)

    # Get count of visible pieces
    piece_count = lesson.lesson_pieces.filter(is_visible=True).count()

    if piece_count == 0:
        messages.info(request, 'No playalong pieces have been assigned to this lesson yet.')
        return redirect('lessons:lesson_detail', pk=lesson_id)

    context = {
        'lesson': lesson,
        'piece_count': piece_count,
        'title': f'Playalong: {lesson.subject.subject} - {lesson.lesson_date}',
        'is_private_lesson': True  # Flag to help template know this is a private lesson
    }
    return render(request, 'audioplayer/audio_player.html', context)


def private_lesson_pieces_json(request, lesson_id):
    """
    JSON API endpoint for private lesson audio player JavaScript.
    Returns all visible pieces and stems for a private teaching lesson.
    """
    from lessons.models import Lesson as PrivateLesson, PrivateLessonPiece

    lesson = get_object_or_404(PrivateLesson, pk=lesson_id)

    # Check access: user must be the student OR the teacher
    is_student = lesson.student == request.user
    is_teacher = lesson.teacher == request.user

    if not (is_student or is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # For students, only show when lesson status is 'Assigned'
    if not is_teacher and lesson.status != 'Assigned':
        return JsonResponse({'error': 'Lesson not assigned yet'}, status=403)

    # Get pieces through the PrivateLessonPiece relationship
    lesson_pieces = PrivateLessonPiece.objects.filter(
        lesson=lesson,
        is_visible=True
    ).select_related('piece').prefetch_related('piece__stems').order_by('order')

    pieces_data = []
    for lp in lesson_pieces:
        # Get stems ordered by their order field
        stems_data = [
            {
                'audio_file': stem.audio_file.url,
                'instrument_name': stem.instrument_name
            }
            for stem in lp.piece.stems.all().order_by('order')
        ]

        piece_data = {
            'title': lp.piece.title,
            'stems': stems_data,
            'svg_image': lp.piece.svg_image.url if lp.piece.svg_image else None,
            'order': lp.order,
        }

        # Add lesson-specific customizations
        if lp.instructions:
            piece_data['instructions'] = lp.instructions
        if lp.is_optional:
            piece_data['is_optional'] = True

        pieces_data.append(piece_data)

    return JsonResponse({'pieces_data': pieces_data})
