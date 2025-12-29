from django import forms
from django.forms import inlineformset_factory
from .models import Piece, Stem, LessonPiece, Composer, Tag


class PieceForm(forms.ModelForm):
    """Form for creating/editing playalong pieces"""

    # Additional fields for creating a new composer inline
    new_composer_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Johann Sebastian Bach'
        }),
        label='Composer Name',
        help_text='Enter the full name of the composer'
    )

    new_composer_dates = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., 1685-1750 or c.1547 - c.1601'
        }),
        label='Dates (Optional)',
        help_text='Birth and death dates (approximate dates OK)'
    )

    new_composer_period = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Baroque, Classical, Traditional'
        }),
        label='Period (Optional)',
        help_text='Musical period or era'
    )

    # Additional field for creating new tags inline
    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Christmas, Duet, Folk Song'
        }),
        label='New Tags',
        help_text='Enter tag names separated by commas to create and add them to this piece'
    )

    class Meta:
        model = Piece
        fields = [
            'title', 'composer', 'grade_level', 'genre', 'difficulty',
            'tags', 'description', 'svg_image', 'pdf_score', 'pdf_score_title', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Hot Cross Buns'
            }),
            'composer': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'grade_level': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'genre': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'select select-bordered w-full',
                'size': '5'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Performance notes, context, or tips...'
            }),
            'svg_image': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full'
            }),
            'pdf_score': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': '.pdf'
            }),
            'pdf_score_title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Full Score, Recorder Part, Piano Accompaniment'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'checkbox'
            }),
        }
        labels = {
            'title': 'Piece Title',
            'composer': 'Composer/Artist',
            'grade_level': 'Grade Level',
            'genre': 'Genre',
            'difficulty': 'Difficulty',
            'tags': 'Tags',
            'description': 'Description/Notes',
            'svg_image': 'Sheet Music Image (SVG/PNG/JPG)',
            'pdf_score': 'Printable PDF Score',
            'pdf_score_title': 'PDF Title (Optional)',
            'is_public': 'Make publicly visible in library',
        }
        help_texts = {
            'svg_image': 'Upload an image to display below the player for on-screen practice',
            'pdf_score': 'Upload a PDF file for students to download and print',
            'pdf_score_title': 'Descriptive title for the PDF (e.g., "Full Score with Piano Accompaniment")',
            'composer': 'Select existing composer, or create a new one below',
            'grade_level': 'Associated exam grade (if applicable)',
            'is_public': 'If checked, piece will be visible to all students in the library',
            'tags': 'Additional categorization (e.g., Christmas, Duet, etc.)',
        }

    def clean(self):
        cleaned_data = super().clean()
        composer = cleaned_data.get('composer')
        new_composer_name = cleaned_data.get('new_composer_name')

        # If a new composer name is provided, create or get that composer
        if new_composer_name:
            new_composer_dates = cleaned_data.get('new_composer_dates', '')
            new_composer_period = cleaned_data.get('new_composer_period', '')

            # Check if composer already exists (case-insensitive)
            existing_composer = Composer.objects.filter(
                name__iexact=new_composer_name
            ).first()

            if existing_composer:
                # Use existing composer
                cleaned_data['composer'] = existing_composer
            else:
                # Create new composer
                new_composer = Composer.objects.create(
                    name=new_composer_name,
                    dates=new_composer_dates,
                    period=new_composer_period,
                    bio=''  # Can be added later via admin or piece edit
                )
                cleaned_data['composer'] = new_composer

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)

        # Handle new tags if provided
        new_tags_str = self.cleaned_data.get('new_tags', '')
        if new_tags_str:
            # Parse comma-separated tags
            tag_names = [name.strip() for name in new_tags_str.split(',') if name.strip()]

            for tag_name in tag_names:
                # Get or create tag (case-insensitive check)
                tag, created = Tag.objects.get_or_create(
                    name__iexact=tag_name,
                    defaults={'name': tag_name}
                )
                # If tag exists but with different case, use the existing one
                if not created:
                    tag = Tag.objects.filter(name__iexact=tag_name).first()

                # Add tag to piece
                instance.tags.add(tag)

        return instance


# Formset for adding multiple stems to a piece
StemFormSet = inlineformset_factory(
    Piece,
    Stem,
    fields=['instrument_name', 'audio_file', 'order'],
    extra=3,  # Show 3 empty forms by default
    can_delete=True,
    validate_min=False,  # Don't require minimum number of stems
    validate_max=False,  # Don't enforce maximum
    widgets={
        'instrument_name': forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Piano, Metronome, Backing Track'
        }),
        'audio_file': forms.FileInput(attrs={
            'class': 'file-input file-input-bordered w-full'
        }),
        'order': forms.NumberInput(attrs={
            'class': 'input input-bordered w-full',
            'min': '0'
        }),
    },
    labels={
        'instrument_name': 'Instrument/Track Name',
        'audio_file': 'Audio File (MP3)',
        'order': 'Display Order'
    }
)


class LessonPieceForm(forms.ModelForm):
    """Form for adding/editing piece assignments to lessons"""

    class Meta:
        model = LessonPiece
        fields = ['piece', 'order', 'is_visible', 'instructions', 'is_optional']
        widgets = {
            'piece': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_optional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add custom instructions for this piece in this lesson...'
            }),
        }
        labels = {
            'piece': 'Select Piece',
            'order': 'Display Order',
            'is_visible': 'Visible to Students',
            'is_optional': 'Optional Practice',
            'instructions': 'Lesson-Specific Instructions'
        }


# Note: LessonPieceFormSet should be created in the courses app where Lesson model is available
# This is just a placeholder - actual formset will be created in courses/forms.py if needed
#
# from apps.courses.models import Lesson
# LessonPieceFormSet = inlineformset_factory(
#     Lesson,
#     LessonPiece,
#     form=LessonPieceForm,
#     extra=1,
#     can_delete=True
# )
