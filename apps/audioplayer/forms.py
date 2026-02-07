from django import forms
from django.forms import inlineformset_factory
from .models import Piece, Stem, LessonPiece, Composer, Tag, PieceCollection, CollectionPiece
from .fields import AutoConvertAudioFileField


class PieceForm(forms.ModelForm):
    """Form for creating/editing playalong pieces"""

    # Additional fields for creating a new composer inline
    new_composer_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
            'placeholder': 'e.g., Johann Sebastian Bach'
        }),
        label='Composer Name',
        help_text='Enter the full name of the composer'
    )

    new_composer_dates = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
            'placeholder': 'e.g., 1685-1750 or c.1547 - c.1601'
        }),
        label='Dates (Optional)',
        help_text='Birth and death dates (approximate dates OK)'
    )

    new_composer_period = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
            'placeholder': 'e.g., Baroque, Classical, Traditional'
        }),
        label='Period (Optional)',
        help_text='Musical period or era'
    )

    # Additional field for creating new tags inline
    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all',
            'placeholder': 'e.g., Christmas, Duet, Folk Song'
        }),
        label='New Tags',
        help_text='Enter tag names separated by commas to create and add them to this piece'
    )

    class Meta:
        model = Piece
        fields = [
            'title', 'composer', 'grade_level', 'genre', 'difficulty',
            'tags', 'description', 'svg_image', 'pdf_score', 'pdf_score_title', 'is_public', 'show_in_library'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., Hot Cross Buns'
            }),
            'composer': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all bg-white cursor-pointer'
            }),
            'grade_level': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'genre': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white',
                'size': '5'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'rows': 4,
                'placeholder': 'Performance notes, context, or tips...'
            }),
            'svg_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100'
            }),
            'pdf_score': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100',
                'accept': '.pdf'
            }),
            'pdf_score_title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all',
                'placeholder': 'e.g., Full Score, Recorder Part, Piano Accompaniment'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-2 border-gray-300 rounded focus:ring-4 focus:ring-blue-100 cursor-pointer'
            }),
            'show_in_library': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-2 border-gray-300 rounded focus:ring-4 focus:ring-blue-100 cursor-pointer'
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
            'show_in_library': 'Show as individual piece in library',
        }
        help_texts = {
            'svg_image': 'Upload an image to display below the player for on-screen practice',
            'pdf_score': 'Upload a PDF file for students to download and print',
            'pdf_score_title': 'Descriptive title for the PDF (e.g., "Full Score with Piano Accompaniment")',
            'composer': 'Select existing composer, or create a new one below',
            'grade_level': 'Associated exam grade (if applicable)',
            'is_public': 'If checked, piece will be visible to all students in the library',
            'tags': 'Additional categorization (e.g., Christmas, Duet, etc.)',
            'show_in_library': 'Uncheck for pieces only accessed through collections (e.g., exercises in a collection)',
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
                    bio=''
                )
                cleaned_data['composer'] = new_composer

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)

        self._new_tags_to_add = []
        new_tags_str = self.cleaned_data.get('new_tags', '')
        if new_tags_str:
            tag_names = [name.strip() for name in new_tags_str.split(',') if name.strip()]
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    name__iexact=tag_name,
                    defaults={'name': tag_name}
                )
                if not created:
                    tag = Tag.objects.filter(name__iexact=tag_name).first()
                self._new_tags_to_add.append(tag)

        if commit and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                instance.tags.add(tag)

        return instance

    def save_m2m(self):
        """Override to also save new tags after the instance has been saved"""
        super().save_m2m()
        if hasattr(self, '_new_tags_to_add') and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                self.instance.tags.add(tag)


class BaseStemFormSet(forms.BaseInlineFormSet):
    """Custom formset that only validates forms with data"""

    def clean(self):
        """Override clean to ignore completely empty forms"""
        super().clean()

        has_filled_form = False
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            if form.cleaned_data.get('instrument_name') or form.cleaned_data.get('audio_file'):
                has_filled_form = True
                break

    def is_valid(self):
        """Override is_valid to skip validation on empty forms"""
        if not super().is_valid():
            for i, form in enumerate(self.forms):
                if not form.instance.pk and not form.has_changed():
                    form._errors = {}
            return not any(form.errors for form in self.forms if not self._should_delete_form(form))
        return True


class StemForm(forms.ModelForm):
    """
    Form for individual stem uploads with auto-AIFF conversion.

    Uses AutoConvertAudioFileField to automatically convert AIFF files to MP3.
    """

    audio_file = AutoConvertAudioFileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
            'accept': '.mp3,.wav,.aiff,.aif,audio/*'
        }),
        label='Audio File (MP3, WAV, AIFF)',
        help_text='AIFF files will be automatically converted to MP3'
    )

    class Meta:
        model = Stem
        fields = ['instrument_name', 'audio_file', 'order']
        widgets = {
            'instrument_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'placeholder': 'e.g., Piano, Metronome, Backing Track'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'min': '0'
            }),
        }
        labels = {
            'instrument_name': 'Instrument/Track Name',
            'order': 'Display Order'
        }


# Formset for adding multiple stems to a piece
StemFormSet = inlineformset_factory(
    Piece,
    Stem,
    form=StemForm,
    formset=BaseStemFormSet,
    extra=0,  # Don't show empty forms by default - use "Add Another Stem" button
    can_delete=True,
    validate_min=False,
    validate_max=False,
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


class PieceCollectionForm(forms.ModelForm):
    """Form for creating/editing piece collections"""

    # Field for selecting existing pieces to include in collection
    pieces = forms.ModelMultipleChoiceField(
        queryset=Piece.objects.none(),  # Will be set in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'piece-checkbox'
        }),
        label='Select Pieces',
        help_text='Choose pieces to include in this collection'
    )

    # Additional field for creating new tags inline
    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all',
            'placeholder': 'e.g., Exercises, Grade 2, Syncopation'
        }),
        label='New Tags',
        help_text='Enter tag names separated by commas to create and add them'
    )

    class Meta:
        model = PieceCollection
        fields = [
            'title', 'description', 'composer', 'grade_level', 'genre',
            'difficulty', 'tags', 'pdf_score', 'pdf_score_title', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., Syncopation Exercises Grade 2'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'rows': 4,
                'placeholder': 'Description, learning objectives, instructions...'
            }),
            'composer': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all bg-white cursor-pointer'
            }),
            'grade_level': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'genre': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white',
                'size': '5'
            }),
            'pdf_score': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100',
                'accept': '.pdf'
            }),
            'pdf_score_title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all',
                'placeholder': 'e.g., Complete Worksheet, Full Score'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-2 border-gray-300 rounded focus:ring-4 focus:ring-blue-100 cursor-pointer'
            }),
        }
        labels = {
            'title': 'Collection Title',
            'description': 'Description',
            'composer': 'Composer/Arranger',
            'grade_level': 'Grade Level',
            'genre': 'Genre',
            'difficulty': 'Difficulty',
            'tags': 'Tags',
            'pdf_score': 'Full Score PDF',
            'pdf_score_title': 'PDF Title',
            'is_public': 'Make publicly visible in library',
        }
        help_texts = {
            'pdf_score': 'Upload a PDF containing the full score/worksheet for all pieces in this collection',
            'pdf_score_title': 'Descriptive title for the PDF download button',
            'is_public': 'If checked, collection will be visible to all students in the library',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the queryset for pieces based on the user
        if user:
            self.fields['pieces'].queryset = Piece.objects.filter(
                created_by=user
            ).order_by('title')

        # If editing, pre-select pieces that are already in the collection (ordered correctly)
        if self.instance and self.instance.pk:
            # Get pieces in correct order via CollectionPiece
            ordered_piece_ids = list(
                CollectionPiece.objects.filter(collection=self.instance)
                .order_by('order')
                .values_list('piece_id', flat=True)
            )
            # Preserve order using Case/When
            from django.db.models import Case, When
            if ordered_piece_ids:
                preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_piece_ids)])
                self.fields['pieces'].initial = Piece.objects.filter(
                    pk__in=ordered_piece_ids
                ).order_by(preserved_order)
            else:
                self.fields['pieces'].initial = Piece.objects.none()

    def save(self, commit=True):
        instance = super().save(commit=commit)

        # Store new tags for later
        self._new_tags_to_add = []
        new_tags_str = self.cleaned_data.get('new_tags', '')
        if new_tags_str:
            tag_names = [name.strip() for name in new_tags_str.split(',') if name.strip()]
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    name__iexact=tag_name,
                    defaults={'name': tag_name}
                )
                if not created:
                    tag = Tag.objects.filter(name__iexact=tag_name).first()
                self._new_tags_to_add.append(tag)

        if commit and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                instance.tags.add(tag)

        # Handle piece selection
        if commit:
            self._save_pieces(instance)

        return instance

    def _save_pieces(self, collection):
        """Save the selected pieces to the collection, preserving order from form"""
        # IMPORTANT: Use raw form data to preserve the order of submitted hidden inputs.
        # Django's ModelMultipleChoiceField.clean() returns a QuerySet ordered by the
        # queryset's ordering (title), not the order the values were submitted.
        # The hidden inputs are created in order by JavaScript, so we use self.data.getlist()
        # to get the piece IDs in their submitted order.
        raw_piece_ids = self.data.getlist('pieces')
        # Convert to integers and filter out any invalid values
        selected_piece_ids = []
        for pid in raw_piece_ids:
            try:
                selected_piece_ids.append(int(pid))
            except (ValueError, TypeError):
                pass

        # Get current pieces in collection
        current_piece_ids = set(
            CollectionPiece.objects.filter(collection=collection).values_list('piece_id', flat=True)
        )

        # Remove pieces no longer selected
        to_remove = current_piece_ids - set(selected_piece_ids)
        CollectionPiece.objects.filter(collection=collection, piece_id__in=to_remove).delete()

        # Update or add pieces with correct order
        for order, piece_id in enumerate(selected_piece_ids):
            CollectionPiece.objects.update_or_create(
                collection=collection,
                piece_id=piece_id,
                defaults={'order': order}
            )

    def save_m2m(self):
        """Override to also save new tags after the instance has been saved"""
        super().save_m2m()
        if hasattr(self, '_new_tags_to_add') and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                self.instance.tags.add(tag)
        # Also save pieces if not already saved
        if hasattr(self, 'instance') and self.instance.pk:
            self._save_pieces(self.instance)
