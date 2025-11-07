from django import forms
from django.forms import inlineformset_factory
from .models import Piece, Stem, LessonPiece


class PieceForm(forms.ModelForm):
    """Form for creating/editing playalong pieces"""

    class Meta:
        model = Piece
        fields = ['title', 'svg_image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Hot Cross Buns'
            }),
        }
        labels = {
            'title': 'Piece Title',
            'svg_image': 'Sheet Music Image (SVG/PNG/JPG)',
        }
        help_texts = {
            'svg_image': 'Upload an image to display below the player for on-screen practice',
        }


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
            'class': 'form-control',
            'placeholder': 'e.g., Piano, Metronome, Backing Track'
        }),
        'order': forms.NumberInput(attrs={
            'class': 'form-control',
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
