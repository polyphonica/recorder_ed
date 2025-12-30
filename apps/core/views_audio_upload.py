"""
Custom audio upload view for CKEditor 5
"""
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.conf import settings


@login_required
@require_http_methods(["POST"])
def audio_upload(request):
    """
    Handle audio file uploads for CKEditor 5.
    Similar to image upload but accepts audio file types.
    """
    try:
        # Get the uploaded file
        upload_file = request.FILES.get('upload')

        if not upload_file:
            return JsonResponse({
                'error': {
                    'message': 'No file uploaded'
                }
            }, status=400)

        # Get file extension
        file_name = upload_file.name
        file_ext = os.path.splitext(file_name)[1].lower().lstrip('.')

        # Validate audio file type
        allowed_audio_types = ['mp3', 'wav', 'ogg', 'm4a', 'aac']
        if file_ext not in allowed_audio_types:
            return JsonResponse({
                'error': {
                    'message': f'Invalid file type. Allowed: {", ".join(allowed_audio_types)}'
                }
            }, status=400)

        # Validate file size (max 50MB for audio)
        max_size = 50 * 1024 * 1024  # 50MB
        if upload_file.size > max_size:
            return JsonResponse({
                'error': {
                    'message': f'File too large. Maximum size: 50MB'
                }
            }, status=400)

        # Generate unique filename
        import uuid
        unique_filename = f"{uuid.uuid4().hex}_{file_name}"

        # Save file to uploads directory
        file_path = os.path.join('uploads', unique_filename)
        saved_path = default_storage.save(file_path, upload_file)

        # Get file URL
        file_url = default_storage.url(saved_path)

        # Return success response in CKEditor format
        return JsonResponse({
            'url': file_url
        })

    except Exception as e:
        return JsonResponse({
            'error': {
                'message': str(e)
            }
        }, status=500)
