"""
Public pages of the Play-Along Library, served under /playalongs/.

The player and its JSON endpoints stay in views.py; these pages wrap the
player with what a visitor needs: the composer, the edition or "Get the
music" details, and links to related pieces.
"""
import json
from urllib.parse import quote

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Composer, Piece, PieceCollection
from .views import (
    _can_access_collection,
    _can_access_piece,
    _deny_library_access,
    _is_teacher,
    get_viewer,
)

SITE_NAME = 'Recorder-ed'


def _public_pieces():
    return Piece.objects.filter(is_public=True, show_in_library=True).select_related('composer')


def _public_collections():
    return PieceCollection.objects.filter(is_public=True).select_related('composer')


def _seo(request, title, description, url_name=None, **kwargs):
    url = request.build_absolute_uri(reverse(url_name, kwargs=kwargs) if url_name else request.path)
    return {'page_title': title, 'page_description': description[:300], 'page_url': url}


def _deny(request, item):
    """Teachers viewing as a visitor get told why; everyone else gets the usual denial."""
    if request.GET.get('as_visitor') == '1' and _is_teacher(request.user):
        messages.info(request, f'Visitors can\'t see "{item}" because it is private.')
        return redirect(request.path)
    return _deny_library_access(request)


def _music_context(item, status, music_source, permission_source):
    """What the page says about the sheet music."""
    return {
        'copyright_status': status,
        'music_source': music_source,
        'permission_source': permission_source,
        'edition_item': item if status == 'public_domain' else None,
    }


def _player_context(request, viewer):
    is_teacher = _is_teacher(viewer)
    return {
        'is_preview': not viewer.is_authenticated,
        'show_lessons_prompt': viewer.is_authenticated and not is_teacher,
        'can_manage': _is_teacher(request.user),
        'as_visitor': request.GET.get('as_visitor') == '1' and not viewer.is_authenticated,
        'login_url': f"{reverse('accounts:login')}?next={quote(request.path)}",
        'signup_url': f"{reverse('accounts:signup')}?next={quote(request.path)}",
    }


def _schema(request, name, description, composer=None, url=None):
    data = {
        '@context': 'https://schema.org',
        '@type': 'MusicComposition',
        'name': name,
        'description': description,
        'url': url or request.build_absolute_uri(),
        'isAccessibleForFree': True,
        'provider': {'@type': 'Organization', 'name': SITE_NAME},
    }
    if composer:
        data['composer'] = {'@type': 'Person', 'name': composer.name}
    # Escape '<' so text such as '</script>' can't end the script tag early
    return json.dumps(data).replace('<', '\\u003c')


# ----- Landing page -----------------------------------------------------------

def library_home(request):
    pieces = _public_pieces()
    collections = _public_collections()

    featured = list(collections.filter(is_featured=True)) + list(pieces.filter(is_featured=True))
    if not featured:
        # Until something is marked as featured, show the newest items
        featured = list(collections.order_by('-created_at')[:3]) + list(pieces.order_by('-created_at')[:3])

    composers = Composer.objects.filter(
        Q(pieces__in=pieces) | Q(pieces__collection_memberships__collection__in=collections)
    ).distinct().order_by('name')
    periods = sorted({c.period for c in composers if c.period}, key=str.lower)
    grade_values = set(pieces.values_list('grade_level', flat=True)) | set(
        collections.values_list('grade_level', flat=True))
    grades = [(v, label) for v, label in Piece.GRADE_CHOICES if v in grade_values and v != 'N/A']

    context = {
        'featured': featured[:6],
        'composers': composers,
        'periods': periods,
        'grades': grades,
        'piece_total': pieces.count(),
        'collection_total': collections.count(),
        'edition_total': pieces.exclude(pdf_score='').exclude(pdf_score__isnull=True).count()
        + collections.exclude(pdf_score='').exclude(pdf_score__isnull=True).count(),
    }
    context.update(_seo(
        request,
        'Free Recorder Play-Along Library | Recorder-ed',
        'Free multi-track play-alongs for recorder players: mute your part and play along. '
        'Recorder-ed Editions of early music to download.',
    ))
    return render(request, 'playalongs/home.html', context)


# ----- Piece and collection pages --------------------------------------------

def piece_page(request, slug):
    piece = get_object_or_404(Piece.objects.select_related('composer'), slug=slug)
    viewer = get_viewer(request)
    if not _can_access_piece(viewer, piece):
        return _deny(request, piece)

    status = piece.copyright_status
    collections = PieceCollection.objects.filter(collection_memberships__piece=piece, is_public=True)
    related = _public_pieces().exclude(pk=piece.pk)
    related = related.filter(composer=piece.composer)[:6] if piece.composer_id else related.none()

    description = piece.description or (
        f"Free recorder play-along of {piece.title}"
        + (f" by {piece.composer.name}" if piece.composer_id else '')
        + ". Mute your part and play along."
    )
    title = f"{piece.title}{' — ' + piece.composer.name if piece.composer_id else ''}"

    context = {
        'piece': piece,
        'piece_count': 1,
        'is_library_player': True,
        'is_library_page': True,
        'title': title,
        'collections': collections,
        'related_pieces': related,
        'composer': piece.composer,
        'schema_json': _schema(request, piece.title, description, piece.composer),
        'edit_url': reverse('audioplayer:piece_edit', kwargs={'pk': piece.pk}),
    }
    context.update(_music_context(piece, status, piece.music_source(), piece.permission_source()))
    context.update(_player_context(request, viewer))
    context.update(_seo(request, f'{title} — free recorder play-along | {SITE_NAME}', description))
    return render(request, 'playalongs/piece.html', context)


def collection_page(request, slug):
    collection = get_object_or_404(PieceCollection.objects.select_related('composer'), slug=slug)
    viewer = get_viewer(request)
    if not _can_access_collection(viewer, collection):
        return _deny(request, collection)

    status = collection.copyright_status
    member_pieces = Piece.objects.filter(
        collection_memberships__collection=collection
    ).select_related('composer').order_by('collection_memberships__order')
    composers = Composer.objects.filter(pieces__in=member_pieces).distinct()

    description = collection.description or (
        f"Free recorder play-alongs: {collection.title}. Mute your part and play along."
    )
    music_source = collection if collection.music_source_title else None
    permission_source = collection if collection.has_valid_permission else None

    context = {
        'collection': collection,
        'piece_count': member_pieces.count(),
        'member_pieces': member_pieces,
        'is_library_collection': True,
        'is_library_page': True,
        'title': collection.title,
        'composers': composers,
        'composer': collection.composer or (composers[0] if len(composers) == 1 else None),
        'schema_json': _schema(request, collection.title, description, collection.composer),
        'edit_url': reverse('audioplayer:collection_edit', kwargs={'pk': collection.pk}),
    }
    context.update(_music_context(collection, status, music_source, permission_source))
    context.update(_player_context(request, viewer))
    context.update(_seo(request, f'{collection.title} — free recorder play-alongs | {SITE_NAME}', description))
    return render(request, 'playalongs/collection.html', context)


def composer_page(request, slug):
    composer = get_object_or_404(Composer, slug=slug)
    pieces = _public_pieces().filter(composer=composer)
    collections = _public_collections().filter(
        Q(composer=composer) | Q(collection_memberships__piece__composer=composer)
    ).distinct()
    if not pieces.exists() and not collections.exists() and not _is_teacher(request.user):
        # Nothing public by this composer: don't publish an empty page
        return redirect('playalongs:library')

    description = (
        f"Free recorder play-alongs of music by {composer.name}"
        + (f" ({composer.dates})" if composer.dates else '')
        + ", with biography."
    )
    context = {
        'composer': composer,
        'pieces': pieces,
        'collections': collections,
    }
    context.update(_seo(request, f'{composer.name} — recorder play-alongs | {SITE_NAME}', description))
    return render(request, 'playalongs/composer.html', context)


def editions_page(request):
    context = _seo(
        request,
        f'About our editions & copyright | {SITE_NAME}',
        'How Recorder-ed Editions are made, how you may use them, and why some '
        'play-alongs need your own copy of the music.',
    )
    return render(request, 'playalongs/editions.html', context)


# ----- Old addresses ------------------------------------------------------------

def old_library_redirect(request):
    url = reverse('playalongs:library')
    if request.META.get('QUERY_STRING'):
        url += '?' + request.META['QUERY_STRING']
    return redirect(url, permanent=True)


def old_piece_player_redirect(request, piece_id):
    piece = get_object_or_404(Piece, pk=piece_id)
    return redirect(piece.get_absolute_url(), permanent=True)


def old_collection_player_redirect(request, collection_id):
    collection = get_object_or_404(PieceCollection, pk=collection_id)
    return redirect(collection.get_absolute_url(), permanent=True)
