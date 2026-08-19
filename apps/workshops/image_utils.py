from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os


def optimize_workshop_image(image_field, max_width=1600, max_height=800, quality=85):
    """
    Resize and optimize an uploaded workshop image.

    This function:
    - Converts images to RGB (handles PNG transparency)
    - Shrinks the image to fit within max_width x max_height, preserving its
      original aspect ratio — never crops and never enlarges a smaller image
    - Optimizes for web delivery

    Cropping to a fixed aspect ratio was deliberately removed: it destructively
    cut off content (e.g. staves from sheet-music exports) that didn't happen to
    be centered in the source image. Display-time framing (letterboxing to a
    consistent card size) is handled in the templates instead, via `object-fit`.

    Args:
        image_field: Django ImageField instance
        max_width: Maximum width in pixels (default: 1600)
        max_height: Maximum height in pixels (default: 800)
        quality: JPEG quality 1-100 (default: 85 - good balance)

    Returns:
        InMemoryUploadedFile: Optimized image ready to save
        None: If image_field is None or processing fails
    """
    if not image_field:
        return None

    try:
        # Open the image using Pillow
        img = Image.open(image_field)

        # Convert RGBA/PNG to RGB (for PNG with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            # Paste image on white background, preserving transparency
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Shrink to fit within the bounding box (no-op if already smaller);
        # preserves aspect ratio and never upscales
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Save to BytesIO buffer
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)

        # Extract original filename without extension
        original_name = os.path.splitext(os.path.basename(image_field.name))[0]

        # Create Django-compatible uploaded file
        return InMemoryUploadedFile(
            output,
            'ImageField',
            f"{original_name}_optimized.jpg",
            'image/jpeg',
            sys.getsizeof(output),
            None
        )

    except Exception as e:
        # Return None if processing fails - caller will handle gracefully
        print(f"Image optimization failed: {str(e)}")
        return None
