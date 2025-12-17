from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os


def optimize_workshop_image(image_field, target_width=1600, target_height=800, quality=85):
    """
    Resize and optimize an uploaded workshop image.

    This function:
    - Converts images to RGB (handles PNG transparency)
    - Crops to 2:1 aspect ratio (centered)
    - Resizes to target dimensions
    - Optimizes for web delivery

    Args:
        image_field: Django ImageField instance
        target_width: Desired width in pixels (default: 1600)
        target_height: Desired height in pixels (default: 800)
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

        # Calculate aspect ratio
        original_width, original_height = img.size
        target_ratio = target_width / target_height
        original_ratio = original_width / original_height

        # Crop to target aspect ratio (2:1) using center crop
        if original_ratio > target_ratio:
            # Image is wider than target ratio - crop width (left/right)
            new_width = int(original_height * target_ratio)
            left = (original_width - new_width) // 2
            img = img.crop((left, 0, left + new_width, original_height))
        elif original_ratio < target_ratio:
            # Image is taller than target ratio - crop height (top/bottom)
            new_height = int(original_width / target_ratio)
            top = (original_height - new_height) // 2
            img = img.crop((0, top, original_width, top + new_height))

        # Resize to target dimensions using high-quality Lanczos resampling
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

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
