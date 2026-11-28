from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Max
from django.views.generic import TemplateView
from functools import wraps
from .models import Piece, Stem, LessonPiece, Composer, Tag, PieceCollection, CollectionPiece
from .forms import PieceForm, StemFormSet, PieceCollectionForm
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


# ===== SHEET MUSIC IN PLAYER DATA =====

def _score_url(item, field, user):
    """
    URL of a piece's or collection's score image or PDF for the player, or None.
    Music still in copyright never gets sheet music, except for teachers
    checking their own uploads. PDF downloads need a (free) account.
    """
    file = getattr(item, field)
    if not file:
        return None
    is_teacher = user.is_authenticated and (user.is_staff or _is_teacher(user))
    if item.is_in_copyright and not is_teacher:
        return None
    if field == 'pdf_score' and not user.is_authenticated:
        return None
    return file.url


# ===== TEACHER VIEWS - Piece Library Management =====

def _attention_issues(item, is_collection):
    """Things about a library item the teacher may want to sort out."""
    import datetime
    from django.utils import timezone
    issues = []
    status = item.copyright_status
    if item.is_public and status == 'public_domain' and not item.pdf_score:
        issues.append('Public, but no edition PDF yet')
    if item.is_public and status == 'permitted':
        source = item.music_source_title if is_collection else item.music_source()
        if not source:
            issues.append('No "Get the music" details')
    if item.audio_permission and item.permission_expires:
        days = (item.permission_expires - timezone.localdate()).days
        if days < 0:
            issues.append(f'Permission expired on {item.permission_expires:%d %b %Y}')
        elif days <= 60:
            issues.append(f'Permission expires on {item.permission_expires:%d %b %Y}')
    if is_collection and item.is_public:
        private = item.collection_memberships.filter(piece__is_public=False).count()
        if private:
            issues.append(f'{private} private piece{"s" if private != 1 else ""} playable through this public collection')
    return issues


@teacher_required
def piece_list(request):
    """List all pieces and collections created by the logged-in teacher"""
    # 'all', 'pieces', 'collections' or 'attention'
    view_filter = request.GET.get('filter', 'all')

    pieces = list(Piece.objects.filter(
        created_by=request.user
    ).select_related('composer').prefetch_related('stems', 'lesson_assignments__lesson', 'collection_memberships__collection'))

    collections = list(PieceCollection.objects.filter(
        created_by=request.user
    ).select_related('composer').prefetch_related('collection_memberships__piece__stems', 'tags'))

    for piece in pieces:
        piece.issues = _attention_issues(piece, is_collection=False)
    for collection in collections:
        collection.issues = _attention_issues(collection, is_collection=True)

    attention_count = sum(1 for item in pieces + collections if item.issues)
    if view_filter == 'attention':
        pieces = [p for p in pieces if p.issues]
        collections = [c for c in collections if c.issues]

    context = {
        'pieces': pieces if view_filter in ['all', 'pieces', 'attention'] else [],
        'collections': collections if view_filter in ['all', 'collections', 'attention'] else [],
        'view_filter': view_filter,
        'attention_count': attention_count,
        'title': 'My Playalong Library'
    }
    return render(request, 'audioplayer/piece_list.html', context)


@teacher_required
def collection_publish(request, pk):
    """Make a collection and all its pieces public in one step, where the copyright lock allows."""
    from django.core.exceptions import ValidationError
    collection = get_object_or_404(PieceCollection, pk=pk, created_by=request.user)
    if request.method != 'POST':
        return redirect('audioplayer:piece_list')

    collection.is_public = True
    try:
        collection.clean()
    except ValidationError as exc:
        for errors in exc.message_dict.values():
            for error in errors:
                messages.error(request, f'"{collection.title}" can\'t be published: {error}')
        return redirect('audioplayer:piece_list')

    with transaction.atomic():
        collection.save()
        kept_private = 0
        for membership in collection.collection_memberships.select_related('piece__composer'):
            piece = membership.piece
            if not piece.is_public:
                piece.is_public = True
                piece.save()  # the copyright lock may keep it private
                if not piece.is_public:
                    kept_private += 1

    collection.refresh_from_db()
    if not collection.is_public:
        messages.error(request, f'"{collection.title}" stays private: it contains music still in copyright without permission.')
    else:
        note = f' {kept_private} piece(s) stay private because of copyright, but play through the collection.' if kept_private else ''
        messages.success(request, f'"{collection.title}" and its pieces are now public.{note}')
    return redirect('audioplayer:piece_list')


@teacher_required
@transaction.atomic
def piece_create(request):
    """Create new piece with stems"""
    if request.method == 'POST':
        form = PieceForm(request.POST, request.FILES)
        formset = StemFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            piece = form.save(commit=False)
            piece.created_by = request.user
            piece.save()
            form.save_m2m()  # Save many-to-many relationships (tags)
            formset.instance = piece
            formset.save()
            messages.success(request, f'Piece "{piece.title}" created successfully!')
            return redirect('audioplayer:piece_list')
        else:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.replace("_", " ").title()}: {error}')
            if not formset.is_valid():
                for i, stem_form in enumerate(formset.forms):
                    if stem_form.errors and stem_form.has_changed():
                        for field, errors in stem_form.errors.items():
                            for error in errors:
                                field_label = stem_form.fields[field].label if field in stem_form.fields else field
                                messages.error(request, f'Stem {i+1} - {field_label}: {error}')
                if formset.non_form_errors():
                    for error in formset.non_form_errors():
                        messages.error(request, f'Stems: {error}')
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
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.replace("_", " ").title()}: {error}')
            if not formset.is_valid():
                for i, stem_form in enumerate(formset.forms):
                    if stem_form.errors and stem_form.has_changed():
                        for field, errors in stem_form.errors.items():
                            for error in errors:
                                field_label = stem_form.fields[field].label if field in stem_form.fields else field
                                messages.error(request, f'Stem {i+1} - {field_label}: {error}')
                if formset.non_form_errors():
                    for error in formset.non_form_errors():
                        messages.error(request, f'Stems: {error}')
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
    """Delete piece (will also remove from all lessons)"""
    piece = get_object_or_404(Piece, pk=pk)

    # Check if used in any lessons (for warning, not blocking)
    usage_count = piece.lesson_assignments.count()
    lessons_using = piece.lesson_assignments.select_related('lesson__topic__course').all()[:5]

    if request.method == 'POST':
        piece_title = piece.title
        piece.delete()  # CASCADE will automatically delete lesson assignments

        if usage_count > 0:
            messages.success(
                request,
                f'Piece "{piece_title}" deleted successfully and removed from {usage_count} lesson(s).'
            )
        else:
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

    if not _can_access_course_lesson(request.user, lesson):
        return _deny_library_access(request)

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

    if not _can_access_course_lesson(request.user, lesson):
        return _deny_library_access(request)

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
            'svg_image': _score_url(lp.piece, 'svg_image', request.user),
            'pdf_score': _score_url(lp.piece, 'pdf_score', request.user),
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
    if lesson.status != PrivateLesson.Status.ASSIGNED and not is_teacher:
        messages.error(request, 'This lesson is not yet available. Playalong content will be accessible when the teacher assigns the lesson.')
        return redirect('lessons:lesson_detail', pk=lesson_id)

    # Get count of visible pieces (individual pieces)
    piece_count = lesson.lesson_pieces.filter(is_visible=True).count()

    # Get count of visible collections and their pieces
    collection_count = lesson.lesson_collections.filter(is_visible=True).count()
    collection_piece_count = 0
    for lc in lesson.lesson_collections.filter(is_visible=True):
        collection_piece_count += lc.collection.collection_memberships.count()

    total_piece_count = piece_count + collection_piece_count

    if total_piece_count == 0:
        messages.info(request, 'No playalong pieces have been assigned to this lesson yet.')
        return redirect('lessons:lesson_detail', pk=lesson_id)

    context = {
        'lesson': lesson,
        'piece_count': total_piece_count,
        'collection_count': collection_count,
        'title': f'Playalong: {lesson.subject.subject} - {lesson.lesson_date}',
        'is_private_lesson': True  # Flag to help template know this is a private lesson
    }
    return render(request, 'audioplayer/audio_player.html', context)


def private_lesson_pieces_json(request, lesson_id):
    """
    JSON API endpoint for private lesson audio player JavaScript.
    Returns all visible pieces and stems for a private teaching lesson.
    Includes both individual pieces and pieces from assigned collections.
    """
    from lessons.models import Lesson as PrivateLesson, PrivateLessonPiece, PrivateLessonCollection

    lesson = get_object_or_404(PrivateLesson, pk=lesson_id)

    # Check access: user must be the student OR the teacher
    is_student = lesson.student == request.user
    is_teacher = lesson.teacher == request.user

    if not (is_student or is_teacher):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # For students, only show when lesson status is 'Assigned'
    if not is_teacher and lesson.status != PrivateLesson.Status.ASSIGNED:
        return JsonResponse({'error': 'Lesson not assigned yet'}, status=403)

    pieces_data = []
    collections_data = []

    # Get individual pieces through the PrivateLessonPiece relationship
    lesson_pieces = PrivateLessonPiece.objects.filter(
        lesson=lesson,
        is_visible=True
    ).select_related('piece').prefetch_related('piece__stems').order_by('order')

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
            'svg_image': _score_url(lp.piece, 'svg_image', request.user),
            'pdf_score': _score_url(lp.piece, 'pdf_score', request.user),
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

    # Get collections and their pieces
    lesson_collections = PrivateLessonCollection.objects.filter(
        lesson=lesson,
        is_visible=True
    ).select_related('collection').prefetch_related(
        'collection__collection_memberships__piece',
        'collection__collection_memberships__piece__stems'
    ).order_by('order')

    for lc in lesson_collections:
        collection = lc.collection
        collection_pieces = []

        # Get pieces through the M2M relationship
        for cp in collection.collection_memberships.all().order_by('order'):
            piece = cp.piece
            stems_data = [
                {
                    'audio_file': stem.audio_file.url,
                    'instrument_name': stem.instrument_name
                }
                for stem in piece.stems.all().order_by('order')
            ]

            piece_data = {
                'title': piece.title,
                'stems': stems_data,
                'svg_image': _score_url(piece, 'svg_image', request.user),
                'order': cp.order,
                'description': piece.description if piece.description else None,
            }
            collection_pieces.append(piece_data)

        collection_data = {
            'title': collection.title,
            'pdf_score': _score_url(collection, 'pdf_score', request.user),
            'pdf_score_title': collection.pdf_score_title if collection.pdf_score_title else None,
            'order': lc.order,
            'pieces': collection_pieces,
        }

        # Add lesson-specific instructions for the collection
        if lc.instructions:
            collection_data['instructions'] = lc.instructions

        collections_data.append(collection_data)

    return JsonResponse({
        'pieces_data': pieces_data,
        'collections_data': collections_data
    })


# ===== PLAY-ALONG LIBRARY VIEWS =====

def _is_teacher(user):
    return (
        user.is_authenticated and
        hasattr(user, 'profile') and
        user.profile.is_teacher
    )


def _student_assigned_ids(user):
    """
    Piece and collection IDs assigned to a student, either directly
    (active/completed assignments) or through a paid, accepted lesson.
    Returns (piece_id_q, collection_id_q) as Q objects on 'id'.
    """
    from lessons.models import Lesson as PrivateLesson, PrivateLessonPiece, PrivateLessonCollection
    from apps.private_teaching.models import StudentPieceAssignment, StudentCollectionAssignment

    student_lessons = PrivateLesson.objects.filter(
        student=user,
        approved_status=PrivateLesson.ApprovalStatus.ACCEPTED,
        payment_status='completed',
        status=PrivateLesson.Status.ASSIGNED,
        is_deleted=False
    ).values_list('id', flat=True)

    student_piece_ids = StudentPieceAssignment.objects.filter(
        student=user,
        status__in=['active', 'completed']
    ).values_list('piece_id', flat=True)
    lesson_piece_ids = PrivateLessonPiece.objects.filter(
        lesson_id__in=student_lessons
    ).values_list('piece_id', flat=True)

    student_collection_ids = StudentCollectionAssignment.objects.filter(
        student=user,
        status__in=['active', 'completed']
    ).values_list('collection_id', flat=True)
    lesson_collection_ids = PrivateLessonCollection.objects.filter(
        lesson_id__in=student_lessons,
        is_visible=True
    ).values_list('collection_id', flat=True)

    return (
        Q(id__in=student_piece_ids) | Q(id__in=lesson_piece_ids),
        Q(id__in=student_collection_ids) | Q(id__in=lesson_collection_ids),
    )


def _can_access_collection(user, collection):
    """Public collections, any collection for teachers, or one assigned to the student."""
    if collection.is_public or _is_teacher(user) or user.is_staff:
        return True
    if not user.is_authenticated:
        return False
    _, collection_q = _student_assigned_ids(user)
    return PieceCollection.objects.filter(collection_q, pk=collection.pk).exists()


def _can_access_piece(user, piece):
    """
    Public pieces, any piece for teachers, a piece assigned to the student,
    or a piece inside a collection the user can open.
    """
    if piece.is_public or _is_teacher(user) or user.is_staff:
        return True
    if PieceCollection.objects.filter(
        collection_memberships__piece=piece, is_public=True
    ).exists():
        return True
    if not user.is_authenticated:
        return False
    piece_q, collection_q = _student_assigned_ids(user)
    if Piece.objects.filter(piece_q, pk=piece.pk).exists():
        return True
    return PieceCollection.objects.filter(
        collection_q, collection_memberships__piece=piece
    ).exists()


def _can_access_course_lesson(user, lesson):
    """Same rule as the course lesson pages: owner, enrolled student, or a public preview lesson."""
    from apps.courses.models import Course, CourseEnrollment
    course = lesson.topic.course
    if (lesson.is_preview and lesson.status == Lesson.Status.PUBLISHED
            and course.status == Course.Status.PUBLISHED):
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff or course.is_owned_by(user):
        return True
    return CourseEnrollment.objects.filter(course=course, student=user, is_active=True).exists()


def _deny_library_access(request):
    """Send anonymous visitors to log in; otherwise behave as if it doesn't exist."""
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    raise Http404


def get_viewer(request):
    """
    The user the public library is shown for. Teachers can add ?as_visitor=1
    to see a page exactly as a logged-out visitor would.
    """
    from django.contrib.auth.models import AnonymousUser
    if request.GET.get('as_visitor') == '1' and _is_teacher(request.user):
        return AnonymousUser()
    return request.user


class PlayAlongLibraryView(TemplateView):
    """
    The Play-Along Library. Visitors and teachers browse everything public;
    students also have a tab of what their teacher has given them.
    """
    template_name = 'audioplayer/library.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viewer = get_viewer(self.request)

        # Get filter parameters
        search_query = self.request.GET.get('search', '').strip()
        composer_id = self.request.GET.get('composer', '').strip()
        grade_level = self.request.GET.get('grade', '').strip()
        genre = self.request.GET.get('genre', '').strip()
        difficulty = self.request.GET.get('difficulty', '').strip()
        tag_id = self.request.GET.get('tag', '').strip()
        period = self.request.GET.get('period', '').strip()

        is_teacher = _is_teacher(viewer)
        # Only students have a "From my teacher" tab
        is_student_view = viewer.is_authenticated and not is_teacher
        view_mode = self.request.GET.get('mode', 'my_pieces' if is_student_view else 'browse_all')
        if not is_student_view or view_mode not in ('my_pieces', 'browse_all'):
            view_mode = 'browse_all'

        pieces = Piece.objects.select_related('composer').prefetch_related('tags', 'stems')

        if view_mode == 'my_pieces':
            piece_q, collection_q = _student_assigned_ids(viewer)
            pieces = pieces.filter(piece_q).distinct()
            collections = PieceCollection.objects.filter(
                collection_q
            ).distinct().prefetch_related('collection_memberships__piece__stems', 'tags')
        else:
            # Everything public. Pieces marked "only through collections" stay out of the list.
            pieces = pieces.filter(is_public=True, show_in_library=True)
            collections = PieceCollection.objects.filter(
                is_public=True
            ).prefetch_related('collection_memberships__piece__stems', 'tags')

        # Remember what this user can see before filtering, so the composer
        # dropdown only offers composers that will actually return results
        visible_pieces = pieces
        visible_collections = collections

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

        if period:
            pieces = pieces.filter(composer__period__iexact=period)

        # Apply filters to collections as well. Search and composer also match
        # the pieces inside a collection (collections have no composer of their own)
        if search_query:
            collections = collections.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(collection_memberships__piece__title__icontains=search_query) |
                Q(collection_memberships__piece__composer__name__icontains=search_query)
            )
        if composer_id:
            collections = collections.filter(
                collection_memberships__piece__composer_id=composer_id
            )
        if grade_level:
            collections = collections.filter(grade_level=grade_level)
        if genre:
            collections = collections.filter(genre=genre)
        if difficulty:
            collections = collections.filter(difficulty=difficulty)
        if tag_id:
            collections = collections.filter(tags__id=tag_id)
        if period:
            collections = collections.filter(
                Q(composer__period__iexact=period) |
                Q(collection_memberships__piece__composer__period__iexact=period)
            )

        pieces = pieces.distinct()
        collections = collections.distinct()

        # Show pieces, collections or both. Counts are taken first so the
        # toggle can say how many of each match the other filters.
        show = self.request.GET.get('show', 'all')
        if show not in ('all', 'pieces', 'collections'):
            show = 'all'
        piece_total = pieces.count()
        collection_total = collections.count()
        if show == 'pieces':
            collections = PieceCollection.objects.none()
        elif show == 'collections':
            pieces = Piece.objects.none()

        show_options = []
        for value, label, count in [
            ('all', 'All', piece_total + collection_total),
            ('pieces', 'Pieces', piece_total),
            ('collections', 'Collections', collection_total),
        ]:
            params = self.request.GET.copy()
            if value == 'all':
                params.pop('show', None)
            else:
                params['show'] = value
            show_options.append({
                'value': value, 'label': label, 'count': count,
                'url': '?' + params.urlencode(),
            })

        # Order by title
        pieces = pieces.order_by('title')
        collections = collections.order_by('title')

        # PERFORMANCE FIX: Limit results to prevent loading thousands of items
        # Apply reasonable limit to prevent performance issues
        pieces = pieces[:200]  # Show up to 200 pieces
        collections = collections[:50]  # Show up to 50 collections

        # Get filter options for dropdowns
        composers = Composer.objects.filter(
            Q(pieces__in=visible_pieces) |
            Q(pieces__collection_memberships__collection__in=visible_collections)
        ).distinct().order_by('name')
        tags = Tag.objects.all().order_by('name')

        # Add to context
        context['pieces'] = pieces
        context['collections'] = collections
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
        context['show'] = show
        context['show_options'] = show_options
        context['has_filters'] = any([
            search_query, composer_id, grade_level, genre, difficulty, tag_id, period, show != 'all'
        ])
        context['selected_period'] = period
        context['period_choices'] = sorted({
            p for p in Composer.objects.filter(
                Q(pieces__in=visible_pieces) |
                Q(pieces__collection_memberships__collection__in=visible_collections)
            ).exclude(period='').values_list('period', flat=True)
        }, key=str.lower)
        context['is_student_view'] = is_student_view
        context['as_visitor'] = self.request.GET.get('as_visitor') == '1' and not viewer.is_authenticated

        return context


def library_piece_json(request, piece_id):
    """
    Returns JSON data for a single piece from the library.
    Used by the audio player JavaScript.
    """
    piece = get_object_or_404(Piece, pk=piece_id)
    if not _can_access_piece(request.user, piece):
        return _deny_library_access(request)

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
        'svg_image': _score_url(piece, 'svg_image', request.user),
        'pdf_score': _score_url(piece, 'pdf_score', request.user),
        'pdf_score_title': piece.pdf_score_title if piece.pdf_score_title else None,
        'order': 0,  # Single piece, so order is always 0
        'description': piece.description if piece.description else None,
    }

    return JsonResponse({'pieces_data': [piece_data]})


def library_collection_json(request, collection_id):
    """
    Returns JSON data for a collection from the library.
    Used by the audio player JavaScript.
    """
    collection = get_object_or_404(PieceCollection, pk=collection_id)
    if not _can_access_collection(request.user, collection):
        return _deny_library_access(request)

    collection_pieces = []

    # Get pieces through direct query with proper ordering (matches collection_edit)
    collection_pieces_qs = CollectionPiece.objects.filter(
        collection=collection
    ).select_related('piece').prefetch_related('piece__stems').order_by('order')

    for cp in collection_pieces_qs:
        piece = cp.piece
        stems_data = [
            {
                'audio_file': stem.audio_file.url if stem.audio_file else None,
                'instrument_name': stem.instrument_name
            }
            for stem in piece.stems.all().order_by('order')
        ]

        piece_data = {
            'title': piece.title,
            'stems': stems_data,
            'svg_image': _score_url(piece, 'svg_image', request.user),
            'order': cp.order,
            'description': piece.description if piece.description else None,
        }
        collection_pieces.append(piece_data)

    collection_data = {
        'title': collection.title,
        'pdf_score': _score_url(collection, 'pdf_score', request.user),
        'pdf_score_title': collection.pdf_score_title if collection.pdf_score_title else None,
        'order': 0,
        'pieces': collection_pieces,
    }

    return JsonResponse({
        'pieces_data': [],
        'collections_data': [collection_data]
    })


# ===== DIGITAL PRODUCT PLAYER VIEWS =====

@login_required
def digital_product_player(request, purchase_id):
    """
    Audio player page for a purchased digital product.
    Verifies completed purchase ownership before granting access.
    """
    from apps.digital_products.models import ProductPurchase

    purchase = get_object_or_404(
        ProductPurchase,
        pk=purchase_id,
        student=request.user,
        payment_status='completed'
    )
    product = purchase.product
    piece_count = product.product_pieces.count() + product.product_collections.count()

    context = {
        'purchase': purchase,
        'product': product,
        'piece_count': piece_count,
        'is_digital_product': True,
        'title': product.title,
    }
    return render(request, 'audioplayer/audio_player.html', context)


@login_required
def digital_product_pieces_json(request, purchase_id):
    """
    JSON API endpoint for the digital product audio player.
    Returns all pieces and collections linked to the purchased product.
    Uses the same data structure as private_lesson_pieces_json.
    """
    from apps.digital_products.models import ProductPurchase

    purchase = get_object_or_404(
        ProductPurchase,
        pk=purchase_id,
        student=request.user,
        payment_status='completed'
    )
    product = purchase.product

    pieces_data = []
    collections_data = []

    # Individual pieces linked to this product
    for dp in product.product_pieces.select_related('piece').prefetch_related(
        'piece__stems'
    ).order_by('order'):
        piece = dp.piece
        stems_data = [
            {
                'audio_file': stem.audio_file.url,
                'instrument_name': stem.instrument_name,
            }
            for stem in piece.stems.all().order_by('order')
        ]
        pieces_data.append({
            'title': piece.title,
            'stems': stems_data,
            'svg_image': _score_url(piece, 'svg_image', request.user),
            'pdf_score': _score_url(piece, 'pdf_score', request.user),
            'pdf_score_title': piece.pdf_score_title or None,
            'order': dp.order,
            'description': piece.description or None,
        })

    # Collections linked to this product
    for dc in product.product_collections.select_related('collection').prefetch_related(
        'collection__collection_memberships__piece__stems'
    ).order_by('order'):
        collection = dc.collection
        collection_pieces = []

        for cp in collection.collection_memberships.all().order_by('order'):
            piece = cp.piece
            stems_data = [
                {
                    'audio_file': stem.audio_file.url,
                    'instrument_name': stem.instrument_name,
                }
                for stem in piece.stems.all().order_by('order')
            ]
            collection_pieces.append({
                'title': piece.title,
                'stems': stems_data,
                'svg_image': _score_url(piece, 'svg_image', request.user),
                'pdf_score': _score_url(piece, 'pdf_score', request.user),
                'pdf_score_title': piece.pdf_score_title if hasattr(piece, 'pdf_score_title') else None,
                'order': cp.order,
                'description': piece.description or None,
            })

        collections_data.append({
            'title': collection.title,
            'pdf_score': _score_url(collection, 'pdf_score', request.user),
            'pdf_score_title': collection.pdf_score_title or None,
            'order': dc.order,
            'pieces': collection_pieces,
        })

    return JsonResponse({
        'pieces_data': pieces_data,
        'collections_data': collections_data,
    })


# ===== COMPOSER MANAGEMENT VIEWS =====

@teacher_required
def composer_list(request):
    """List all composers for teacher management"""
    composers = Composer.objects.annotate(
        piece_total=Count('pieces', distinct=True),
        public_total=Count('pieces', filter=Q(pieces__is_public=True), distinct=True),
    ).order_by('name')

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
            fields = ['name', 'dates', 'period', 'in_copyright', 'bio']
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
                ),
                'in_copyright': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            }
            labels = {
                'name': 'Composer Name',
                'dates': 'Dates',
                'period': 'Period/Era',
                'in_copyright': 'Music still in copyright',
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
            fields = ['name', 'dates', 'period', 'in_copyright', 'bio']
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
                ),
                'in_copyright': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            }
            labels = {
                'name': 'Composer Name',
                'dates': 'Dates',
                'period': 'Period/Era',
                'in_copyright': 'Music still in copyright',
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


# ===== COLLECTION MANAGEMENT VIEWS =====

@teacher_required
def collection_list(request):
    """Redirect to unified library with collections filter"""
    return redirect('audioplayer:piece_list')  # Unified library shows both


@teacher_required
@transaction.atomic
def collection_create(request):
    """Create a new collection"""
    if request.method == 'POST':
        form = PieceCollectionForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            collection = form.save(commit=False)
            collection.created_by = request.user
            collection.save()
            form.save_m2m()
            messages.success(request, f'Collection "{collection.title}" created successfully!')
            return redirect('audioplayer:collection_edit', pk=collection.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.replace("_", " ").title()}: {error}')
    else:
        form = PieceCollectionForm(user=request.user)

    context = {
        'form': form,
        'title': 'Create New Collection',
        'submit_text': 'Create Collection'
    }
    return render(request, 'audioplayer/collection_form.html', context)


@teacher_required
@transaction.atomic
def collection_edit(request, pk):
    """Edit collection and manage its pieces"""
    collection = get_object_or_404(PieceCollection, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = PieceCollectionForm(request.POST, request.FILES, instance=collection, user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, f'Collection "{collection.title}" updated successfully!')
            return redirect('audioplayer:collection_edit', pk=collection.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.replace("_", " ").title()}: {error}')
    else:
        form = PieceCollectionForm(instance=collection, user=request.user)

    # Get pieces in this collection through the M2M relationship
    collection_pieces = CollectionPiece.objects.filter(
        collection=collection
    ).select_related('piece').prefetch_related('piece__stems').order_by('order')

    context = {
        'form': form,
        'collection': collection,
        'collection_pieces': collection_pieces,
        'title': f'Edit: {collection.title}',
        'submit_text': 'Update Collection'
    }
    return render(request, 'audioplayer/collection_form.html', context)


@teacher_required
def collection_delete(request, pk):
    """Delete a collection (pieces remain as standalone - M2M relationship)"""
    collection = get_object_or_404(PieceCollection, pk=pk, created_by=request.user)

    pieces_count = collection.collection_memberships.count()

    if request.method == 'POST':
        collection_title = collection.title
        # Delete collection - pieces remain standalone (M2M just removes the link)
        collection.delete()
        messages.success(
            request,
            f'Collection "{collection_title}" deleted. {pieces_count} piece(s) remain in your library.'
        )
        return redirect('audioplayer:piece_list')

    context = {
        'collection': collection,
        'pieces_count': pieces_count,
        'title': f'Delete: {collection.title}'
    }
    return render(request, 'audioplayer/collection_confirm_delete.html', context)


@teacher_required
def collection_detail(request, pk):
    """View collection details and its pieces"""
    collection = get_object_or_404(
        PieceCollection.objects.prefetch_related('collection_memberships__piece__stems', 'tags'),
        pk=pk
    )

    # Check if user owns this collection or if it's public
    is_owner = collection.created_by == request.user

    # Get pieces through the M2M relationship
    collection_pieces = CollectionPiece.objects.filter(
        collection=collection
    ).select_related('piece').prefetch_related('piece__stems').order_by('order')

    context = {
        'collection': collection,
        'collection_pieces': collection_pieces,
        'is_owner': is_owner,
        'title': collection.title
    }
    return render(request, 'audioplayer/collection_detail.html', context)


@teacher_required
def collection_reorder_pieces(request, pk):
    """AJAX endpoint to reorder pieces in a collection"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    collection = get_object_or_404(PieceCollection, pk=pk, created_by=request.user)

    import json
    try:
        data = json.loads(request.body)
        piece_ids = data.get('piece_ids', [])

        for index, piece_id in enumerate(piece_ids):
            CollectionPiece.objects.filter(
                piece_id=piece_id, collection=collection
            ).update(order=index)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ===== PROTECTED PLAYALONG FILES =====

def protected_file(request, token, filename):
    """
    Serve a playalong file (stem, score PDF or notation image) from private
    storage. The signed token is the permission: it is only handed out by
    pages that have already checked access, and it expires within 12 hours.
    """
    from django.conf import settings
    from django.http import FileResponse, HttpResponse
    import mimetypes
    import os
    from .storage import read_token, protected_storage, WINDOW_SECONDS

    name = read_token(token)
    if name is None or os.path.basename(name) != filename:
        raise Http404

    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    if settings.PRIVATE_MEDIA_X_ACCEL:
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = '/protected/' + name
    else:
        try:
            response = FileResponse(protected_storage().open(name, 'rb'), content_type=content_type)
        except FileNotFoundError:
            raise Http404

    # Browsers may keep it for as long as the link is valid, but not shared caches
    response['Cache-Control'] = f'private, max-age={WINDOW_SECONDS}'
    response['X-Content-Type-Options'] = 'nosniff'
    if content_type == 'image/svg+xml':
        # Uploaded SVGs must not be able to run scripts if opened directly
        response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response
