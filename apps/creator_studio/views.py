"""
Creator Studio Views

Tools for creating teaching resources accessible to all instructors.
"""

import os
import shutil

from django.views.generic import TemplateView, FormView, View
from django.http import FileResponse, JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings

from apps.core.mixins import InstructorRequiredMixin
from .forms import AudioConverterForm, SaveAsStemForm


# =============================================================================
# LANDING PAGE
# =============================================================================

class CreatorStudioHomeView(InstructorRequiredMixin, TemplateView):
    """
    Landing page for Creator Studio - lists all available tools.
    """
    template_name = 'creator_studio/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creator Studio'
        return context


# =============================================================================
# NOTATION TOOLS
# =============================================================================

class FingeringDiagramCreatorView(InstructorRequiredMixin, TemplateView):
    """
    Interactive recorder fingering diagram creator.
    Generates SVG that can be copied into CKEditor.
    """
    template_name = 'creator_studio/fingering_diagram.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Recorder Fingering Diagram Creator'
        return context


class TimeSignatureGeneratorView(InstructorRequiredMixin, TemplateView):
    """
    Time signature SVG generator.
    Generates customizable time signature notation that can be copied into CKEditor.
    """
    template_name = 'creator_studio/time_signature.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        # Set defaults
        context.update({
            'top': '4',
            'bottom': '4',
            'top_right': '',
            'bottom_right': '',
            'font_size': 48,
            'spacing': 24,
            'viewbox_w': 60,
            'viewbox_h': 120,
            'display_w': 90,
            'display_h': 140,
            'svg_code': self._generate_svg('4', '4', '', '', 48, 24, 60, 120, 90, 140)
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        # Get values from POST
        top = request.POST.get('top', '4')
        bottom = request.POST.get('bottom', '4')
        top_right = request.POST.get('top_right', '')
        bottom_right = request.POST.get('bottom_right', '')
        font_size = int(request.POST.get('font_size', 48))
        spacing = int(request.POST.get('spacing', 24))
        viewbox_w = int(request.POST.get('viewbox_w', 60))
        viewbox_h = int(request.POST.get('viewbox_h', 120))
        display_w = int(request.POST.get('display_w', 90))
        display_h = int(request.POST.get('display_h', 140))

        svg_code = self._generate_svg(top, bottom, top_right, bottom_right,
                                      font_size, spacing, viewbox_w, viewbox_h,
                                      display_w, display_h)

        context.update({
            'top': top,
            'bottom': bottom,
            'top_right': top_right,
            'bottom_right': bottom_right,
            'font_size': font_size,
            'spacing': spacing,
            'viewbox_w': viewbox_w,
            'viewbox_h': viewbox_h,
            'display_w': display_w,
            'display_h': display_h,
            'svg_code': svg_code
        })

        return self.render_to_response(context)

    def _generate_svg(self, top, bottom, top_right, bottom_right,
                     font_size, spacing, viewbox_w, viewbox_h, display_w, display_h):
        """Generate the time signature SVG code"""
        top_y = 56
        bottom_y = top_y + spacing

        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {viewbox_w} {viewbox_h}" width="{display_w}" height="{display_h}">
  <text x="{viewbox_w/2}" y="{top_y}" font-family="Opus" font-size="{font_size}" text-anchor="middle" fill="#000">{top}</text>
  <text x="{viewbox_w/2 + font_size}" y="{top_y}" font-family="Arial" font-size="14" text-anchor="start" fill="#000">{top_right}</text>
  <text x="{viewbox_w/2}" y="{bottom_y}" font-family="Opus" font-size="{font_size}" text-anchor="middle" fill="#000">{bottom}</text>
  <text x="{viewbox_w/2 + font_size}" y="{bottom_y}" font-family="Arial" font-size="14" text-anchor="start" fill="#000">{bottom_right}</text>
</svg>'''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Time Signature Generator'
        return context


# =============================================================================
# AUDIO CONVERTER
# =============================================================================

class AudioConverterView(InstructorRequiredMixin, FormView):
    """
    Audio converter tool using FFmpeg.
    Supports format conversion, speed adjustment, trimming, and normalization.
    """
    template_name = 'creator_studio/audio_converter.html'
    form_class = AudioConverterForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Audio Converter'
        context['max_file_size_mb'] = 20
        return context

    def form_valid(self, form):
        from .services.audio_processor import AudioProcessor

        uploaded_file = form.cleaned_data['audio_file']
        output_format = form.cleaned_data['output_format']
        playback_speed = form.cleaned_data.get('playback_speed') or 1.0
        trim_start = form.cleaned_data.get('trim_start')
        trim_end = form.cleaned_data.get('trim_end')
        normalize = form.cleaned_data.get('normalize', False)

        processor = AudioProcessor()
        try:
            result_path, original_name = processor.process(
                uploaded_file,
                output_format=output_format,
                speed=playback_speed,
                trim_start=trim_start,
                trim_end=trim_end,
                normalize=normalize
            )
            # Store result path in session for download
            self.request.session['audio_result'] = {
                'path': result_path,
                'original_name': original_name,
                'format': output_format
            }
            return redirect('creator_studio:audio_result')
        except Exception as e:
            messages.error(self.request, f'Error processing audio: {str(e)}')
            return self.form_invalid(form)


class AudioConverterResultView(InstructorRequiredMixin, TemplateView):
    """
    Shows the result of audio processing with download option.
    """
    template_name = 'creator_studio/audio_converter_result.html'

    def get_context_data(self, **kwargs):
        import os
        context = super().get_context_data(**kwargs)
        result = self.request.session.get('audio_result', {})
        context['result'] = result
        if result:
            base_name = os.path.splitext(result.get('original_name', ''))[0]
            context['download_filename'] = f"{base_name}_converted.{result.get('format', '')}"
        context['title'] = 'Audio Conversion Complete'
        return context


class AudioDownloadView(InstructorRequiredMixin, View):
    """
    Serves the processed audio file for download and cleans up temp file.
    """
    def get(self, request):
        import os

        result = request.session.get('audio_result')
        if not result:
            messages.error(request, 'No processed file available.')
            return redirect('creator_studio:audio_converter')

        file_path = result['path']
        if not os.path.exists(file_path):
            messages.error(request, 'Processed file not found.')
            return redirect('creator_studio:audio_converter')

        # Build download filename
        original_name = result['original_name']
        base_name = os.path.splitext(original_name)[0]
        new_name = f"{base_name}_converted.{result['format']}"

        # Use a file wrapper that deletes the temp file when closed
        response = FileResponse(
            self._get_file_wrapper(file_path),
            as_attachment=True,
            filename=new_name
        )

        # Clear session data after initiating download
        if 'audio_result' in request.session:
            del request.session['audio_result']

        return response

    def _get_file_wrapper(self, file_path):
        """
        Generator that reads the file and deletes it after reading.
        """
        import os

        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
        finally:
            # Delete the temp file after streaming
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass  # File may already be deleted


class PieceSearchAPIView(InstructorRequiredMixin, View):
    """
    API endpoint for searching user's pieces.
    Returns JSON for the Save as Stem modal.
    """
    def get(self, request):
        from apps.audioplayer.models import Piece

        query = request.GET.get('q', '').strip()
        pieces = Piece.objects.filter(created_by=request.user)

        if query:
            pieces = pieces.filter(title__icontains=query)

        pieces = pieces.order_by('-updated_at')[:20]

        results = [
            {
                'id': p.id,
                'title': p.title,
                'stem_count': p.stems.count()
            }
            for p in pieces
        ]

        return JsonResponse({'pieces': results})


class AudioSaveAsStemView(InstructorRequiredMixin, View):
    """
    Saves the converted audio file as a stem on a piece.
    """
    def post(self, request):
        import uuid
        from django.core.files.base import ContentFile
        from apps.audioplayer.models import Piece, Stem

        # Validate form
        form = SaveAsStemForm(request.POST)
        if not form.is_valid():
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)

        # Get the converted file from session
        result = request.session.get('audio_result')
        if not result:
            return JsonResponse({
                'success': False,
                'error': 'No converted file available. Please convert a file first.'
            }, status=400)

        temp_file_path = result['path']
        if not os.path.exists(temp_file_path):
            return JsonResponse({
                'success': False,
                'error': 'Converted file not found. Please try converting again.'
            }, status=400)

        # Get or create the piece
        piece_choice = form.cleaned_data['piece_choice']

        if piece_choice == 'existing':
            piece_id = form.cleaned_data['piece_id']
            try:
                piece = Piece.objects.get(id=piece_id, created_by=request.user)
            except Piece.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Piece not found or you do not have permission.'
                }, status=404)
        else:
            # Create new piece
            piece = Piece.objects.create(
                title=form.cleaned_data['new_piece_title'],
                created_by=request.user,
                is_public=False,
                show_in_library=False
            )

        # Create the stem
        instrument_name = form.cleaned_data['instrument_name']
        stem_order = form.cleaned_data.get('stem_order') or 0

        # Read the temp file and create stem
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()

        # Generate a unique filename
        original_name = result['original_name']
        base_name = os.path.splitext(original_name)[0]
        file_ext = result['format']
        unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.{file_ext}"

        stem = Stem(
            piece=piece,
            instrument_name=instrument_name,
            order=stem_order
        )
        stem.audio_file.save(unique_filename, ContentFile(file_content))
        stem.save()

        # Clean up temp file and session
        try:
            os.remove(temp_file_path)
        except OSError:
            pass

        if 'audio_result' in request.session:
            del request.session['audio_result']

        return JsonResponse({
            'success': True,
            'message': f'Audio saved as "{instrument_name}" on "{piece.title}"',
            'piece_id': piece.id,
            'stem_id': stem.id,
            'is_new_piece': piece_choice == 'new'
        })
