from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.views.generic import TemplateView
from functools import wraps
from .models import Piece, Stem, LessonPiece, Composer, Tag
from .forms import PieceForm, StemFormSet
from apps.courses.models import Lesson


# ===== PERMISSION DECORATORS =====

def teacher_required(view_func):
    """Decorator to ensure only teachers can access a view"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
            messages.error(request, 'Only teachers can access this page.')
            return redirect('private_teaching:home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ===== TEACHER VIEWS - Piece Library Management =====

@teacher_required
def piece_list(request):
    """List all pieces in the library"""
    pieces = Piece.objects.prefetch_related('stems', 'lesson_assignments__lesson').all()

    context = {
        'pieces': pieces,
        'title': 'Playalong Piece Library'
    }
    return render(request, 'audioplayer/piece_list.html', context)


@teacher_required
@transaction.atomic
def piece_create(request):
    """Create new piece with stems"""
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


@teacher_required
@transaction.atomic
def piece_edit(request, pk):
    """Edit existing piece and its stems"""
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


@teacher_required
def piece_delete(request, pk):
    """Delete piece (with safety check for usage in lessons)"""
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
            'pdf_score': lp.piece.pdf_score.url if lp.piece.pdf_score else None,
            'pdf_score_title': lp.piece.pdf_score_title if lp.piece.pdf_score_title else None,
            'order': lp.order,
            'description': lp.piece.description if lp.piece.description else None,
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
    """View details of a piece (students can view, teachers can edit)"""
    from lessons.models import PrivateLessonPiece

    piece = get_object_or_404(Piece, pk=pk)
    stems = piece.stems.all().order_by('order')

    # Check if user is a teacher
    is_teacher = (
        hasattr(request.user, 'profile') and
        request.user.profile.is_teacher
    )

    # Get private teaching lessons using this piece (filtered by current user)
    if is_teacher:
        # Teachers see all their lessons using this piece
        lessons_using = PrivateLessonPiece.objects.filter(
            piece=piece,
            lesson__teacher=request.user,
            lesson__is_deleted=False
        ).select_related(
            'lesson__student',
            'lesson__lesson_request'
        ).order_by('-lesson__lesson_date')
    else:
        # Students see only their own lessons using this piece
        lessons_using = PrivateLessonPiece.objects.filter(
            piece=piece,
            lesson__student=request.user,
            lesson__is_deleted=False
        ).select_related(
            'lesson__lesson_request'
        ).order_by('-lesson__lesson_date')

    context = {
        'piece': piece,
        'stems': stems,
        'lessons_using': lessons_using,
        'title': piece.title,
        'is_teacher': is_teacher
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
            'pdf_score': lp.piece.pdf_score.url if lp.piece.pdf_score else None,
            'pdf_score_title': lp.piece.pdf_score_title if lp.piece.pdf_score_title else None,
            'order': lp.order,
            'description': lp.piece.description if lp.piece.description else None,
        }

        # Add lesson-specific customizations
        if lp.instructions:
            piece_data['instructions'] = lp.instructions
        if lp.is_optional:
            piece_data['is_optional'] = True

        pieces_data.append(piece_data)

    return JsonResponse({'pieces_data': pieces_data})


# ===== PLAY-ALONG LIBRARY VIEWS =====

class PlayAlongLibraryView(TemplateView):
    """
    Play-along library for students and teachers.
    Shows pieces from assigned lessons + all public pieces for browsing.
    """
    template_name = 'audioplayer/library.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters
        search_query = self.request.GET.get('search', '').strip()
        composer_id = self.request.GET.get('composer', '').strip()
        grade_level = self.request.GET.get('grade', '').strip()
        genre = self.request.GET.get('genre', '').strip()
        difficulty = self.request.GET.get('difficulty', '').strip()
        tag_id = self.request.GET.get('tag', '').strip()
        view_mode = self.request.GET.get('mode', 'my_pieces')  # 'my_pieces' or 'browse_all'

        # Determine if user is teacher
        is_teacher = (
            self.request.user.is_authenticated and
            hasattr(self.request.user, 'profile') and
            self.request.user.profile.is_teacher
        )

        # Base queryset - will be filtered based on mode
        pieces = Piece.objects.select_related('composer').prefetch_related('tags', 'stems')

        if view_mode == 'my_pieces' and self.request.user.is_authenticated:
            # Show pieces from user's lessons
            if is_teacher:
                # Teachers see pieces from all their lessons
                from lessons.models import Lesson as PrivateLesson, PrivateLessonPiece
                teacher_lesson_ids = PrivateLesson.objects.filter(
                    teacher=self.request.user,
                    is_deleted=False
                ).values_list('id', flat=True)

                piece_ids_from_lessons = PrivateLessonPiece.objects.filter(
                    lesson_id__in=teacher_lesson_ids
                ).values_list('piece_id', flat=True).distinct()

                pieces = pieces.filter(id__in=piece_ids_from_lessons)
            else:
                # Students see pieces from their paid & assigned lessons
                from lessons.models import Lesson as PrivateLesson, PrivateLessonPiece
                student_lessons = PrivateLesson.objects.filter(
                    student=self.request.user,
                    approved_status='Accepted',
                    payment_status='Paid',
                    status='Assigned',
                    is_deleted=False
                ).values_list('id', flat=True)

                piece_ids_from_lessons = PrivateLessonPiece.objects.filter(
                    lesson_id__in=student_lessons
                ).values_list('piece_id', flat=True).distinct()

                pieces = pieces.filter(id__in=piece_ids_from_lessons)

        elif view_mode == 'browse_all':
            # Show all public pieces (teachers see all pieces)
            if not is_teacher:
                pieces = pieces.filter(is_public=True)
        else:
            # Default to empty if not authenticated
            if not self.request.user.is_authenticated:
                pieces = pieces.filter(is_public=True)

        # Apply filters
        if search_query:
            pieces = pieces.filter(
                Q(title__icontains=search_query) |
                Q(composer__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        if composer_id:
            pieces = pieces.filter(composer_id=composer_id)

        if grade_level:
            pieces = pieces.filter(grade_level=grade_level)

        if genre:
            pieces = pieces.filter(genre=genre)

        if difficulty:
            pieces = pieces.filter(difficulty=difficulty)

        if tag_id:
            pieces = pieces.filter(tags__id=tag_id)

        # Order by title
        pieces = pieces.order_by('title')

        # PERFORMANCE FIX: Limit results to prevent loading thousands of pieces
        # Apply reasonable limit to prevent performance issues
        pieces = pieces[:200]  # Show up to 200 pieces (user can use filters to narrow down)

        # Get filter options for dropdowns
        composers = Composer.objects.all().order_by('name')
        tags = Tag.objects.all().order_by('name')

        # Add to context
        context['pieces'] = pieces
        context['composers'] = composers
        context['tags'] = tags
        context['grade_choices'] = Piece.GRADE_CHOICES
        context['genre_choices'] = Piece.GENRE_CHOICES
        context['difficulty_choices'] = Piece.DIFFICULTY_CHOICES
        context['view_mode'] = view_mode
        context['is_teacher'] = is_teacher

        # Preserve filter values
        context['search_query'] = search_query
        context['selected_composer'] = composer_id
        context['selected_grade'] = grade_level
        context['selected_genre'] = genre
        context['selected_difficulty'] = difficulty
        context['selected_tag'] = tag_id

        return context


def library_piece_player(request, piece_id):
    """
    Audio player page for a single piece from the library.
    Accessible by any authenticated user.
    """
    piece = get_object_or_404(Piece, pk=piece_id)

    context = {
        'piece': piece,
        'piece_count': 1,
        'title': f'Play: {piece.title}',
        'is_library_player': True  # Flag to help template know this is library mode
    }
    return render(request, 'audioplayer/audio_player.html', context)


def library_piece_json(request, piece_id):
    """
    Returns JSON data for a single piece from the library.
    Used by the audio player JavaScript.
    """
    piece = get_object_or_404(Piece, pk=piece_id)

    # Build stems data - match format used by lesson endpoints
    stems_data = [
        {
            'audio_file': stem.audio_file.url if stem.audio_file else None,
            'instrument_name': stem.instrument_name
        }
        for stem in piece.stems.all().order_by('order')
    ]

    # Build piece data - match format used by lesson endpoints
    piece_data = {
        'title': piece.title,
        'stems': stems_data,
        'svg_image': piece.svg_image.url if piece.svg_image else None,
        'pdf_score': piece.pdf_score.url if piece.pdf_score else None,
        'pdf_score_title': piece.pdf_score_title if piece.pdf_score_title else None,
        'order': 0,  # Single piece, so order is always 0
        'description': piece.description if piece.description else None,
    }

    return JsonResponse({'pieces_data': [piece_data]})


# ===== COMPOSER MANAGEMENT VIEWS =====

@teacher_required
def composer_list(request):
    """List all composers for teacher management"""
    composers = Composer.objects.prefetch_related('pieces').order_by('name')

    context = {
        'composers': composers,
        'title': 'Manage Composers'
    }
    return render(request, 'audioplayer/composer_list.html', context)


@teacher_required
def composer_create(request):
    """Create a new composer"""
    from django import forms
    from django_ckeditor_5.widgets import CKEditor5Widget

    class ComposerCreateForm(forms.ModelForm):
        class Meta:
            model = Composer
            fields = ['name', 'dates', 'period', 'bio']
            widgets = {
                'name': forms.TextInput(attrs={
                    'class': 'input input-bordered w-full',
                    'placeholder': 'e.g., Johann Sebastian Bach'
                }),
                'dates': forms.TextInput(attrs={
                    'class': 'input input-bordered w-full',
                    'placeholder': 'e.g., 1685-1750 or c.1547 - c.1601'
                }),
                'period': forms.TextInput(attrs={
                    'class': 'input input-bordered w-full',
                    'placeholder': 'e.g., Baroque, Classical, Traditional'
                }),
                'bio': CKEditor5Widget(
                    attrs={'class': 'django_ckeditor_5'},
                    config_name='default'
                )
            }
            labels = {
                'name': 'Composer Name',
                'dates': 'Dates',
                'period': 'Period/Era',
                'bio': 'Biography'
            }
            help_texts = {
                'name': 'Full name of the composer or artist',
                'dates': 'Birth and death dates (e.g., "1685-1750" or "c.1547 - c.1601")',
                'period': 'Musical period or era (optional)',
                'bio': 'Biographical information with formatting (optional)'
            }

    if request.method == 'POST':
        form = ComposerCreateForm(request.POST)
        if form.is_valid():
            composer = form.save()
            messages.success(request, f'Composer "{composer.name}" created successfully!')
            return redirect('audioplayer:composer_list')
    else:
        form = ComposerCreateForm()

    context = {
        'form': form,
        'title': 'Create New Composer',
        'is_create': True
    }
    return render(request, 'audioplayer/composer_edit.html', context)


@teacher_required
def composer_edit(request, pk):
    """Edit composer details including biography"""
    from django import forms
    from django_ckeditor_5.widgets import CKEditor5Widget

    composer = get_object_or_404(Composer, pk=pk)
    
    class ComposerEditForm(forms.ModelForm):
        class Meta:
            model = Composer
            fields = ['name', 'dates', 'period', 'bio']
            widgets = {
                'name': forms.TextInput(attrs={
                    'class': 'input input-bordered w-full',
                    'placeholder': 'e.g., Johann Sebastian Bach'
                }),
                'dates': forms.TextInput(attrs={
                    'class': 'input input-bordered w-full',
                    'placeholder': 'e.g., 1685-1750 or c.1547 - c.1601'
                }),
                'period': forms.TextInput(attrs={
                    'class': 'input input-bordered w-full',
                    'placeholder': 'e.g., Baroque, Classical, Traditional'
                }),
                'bio': CKEditor5Widget(
                    attrs={'class': 'django_ckeditor_5'},
                    config_name='default'
                )
            }
            labels = {
                'name': 'Composer Name',
                'dates': 'Dates',
                'period': 'Period/Era',
                'bio': 'Biography'
            }
            help_texts = {
                'name': 'Full name of the composer or artist',
                'dates': 'Birth and death dates (e.g., "1685-1750" or "c.1547 - c.1601")',
                'period': 'Musical period or era (optional)',
                'bio': 'Biographical information with formatting (optional)'
            }
    
    if request.method == 'POST':
        form = ComposerEditForm(request.POST, instance=composer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Composer "{composer.name}" updated successfully!')
            return redirect('audioplayer:composer_list')
    else:
        form = ComposerEditForm(instance=composer)
    
    # Get pieces by this composer
    pieces = composer.pieces.all()
    
    context = {
        'form': form,
        'composer': composer,
        'pieces': pieces,
        'title': f'Edit Composer: {composer.name}'
    }
    return render(request, 'audioplayer/composer_edit.html', context)


@teacher_required
def composer_delete(request, pk):
    """Delete a composer (only if not used in any pieces)"""
    composer = get_object_or_404(Composer, pk=pk)
    
    if composer.pieces.exists():
        messages.error(
            request,
            f'Cannot delete "{composer.name}" because it is used in {composer.pieces.count()} piece(s). '
            f'Remove the composer from all pieces first.'
        )
        return redirect('audioplayer:composer_list')
    
    if request.method == 'POST':
        name = composer.name
        composer.delete()
        messages.success(request, f'Composer "{name}" deleted successfully!')
        return redirect('audioplayer:composer_list')
    
    context = {
        'composer': composer,
        'title': f'Delete Composer: {composer.name}'
    }
    return render(request, 'audioplayer/composer_confirm_delete.html', context)
