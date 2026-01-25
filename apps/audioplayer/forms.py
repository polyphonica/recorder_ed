from django import forms
from django.forms import inlineformset_factory
from .models import Piece, Stem, LessonPiece, Composer, Tag, PieceCollection


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
            'tags', 'description', 'svg_image', 'pdf_score', 'pdf_score_title', 'is_public'
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

        # Store new tags for later - they'll be added in _save_new_tags
        # which is called after the instance has a pk
        self._new_tags_to_add = []
        new_tags_str = self.cleaned_data.get('new_tags', '')
        if new_tags_str:
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
                self._new_tags_to_add.append(tag)

        # If commit=True, we can add tags now since instance has pk
        if commit and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                instance.tags.add(tag)

        return instance

    def save_m2m(self):
        """Override to also save new tags after the instance has been saved"""
        super().save_m2m()
        # Add any new tags that were created
        if hasattr(self, '_new_tags_to_add') and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                self.instance.tags.add(tag)


class BaseStemFormSet(forms.BaseInlineFormSet):
    """Custom formset that only validates forms with data"""

    def clean(self):
        """Override clean to ignore completely empty forms"""
        super().clean()

        # Check if at least one valid stem exists (not required, but good to know)
        has_filled_form = False
        for form in self.forms:
            # Skip deleted forms and forms without data
            if self.can_delete and self._should_delete_form(form):
                continue

            # Check if this form has any meaningful data
            if form.cleaned_data.get('instrument_name') or form.cleaned_data.get('audio_file'):
                has_filled_form = True
                break

    def is_valid(self):
        """Override is_valid to skip validation on empty forms"""
        # First check basic validity
        if not super().is_valid():
            # Filter out errors from completely empty forms
            for i, form in enumerate(self.forms):
                if not form.instance.pk and not form.has_changed():
                    # This is an empty new form - clear its errors
                    form._errors = {}
            return not any(form.errors for form in self.forms if form not in self.deleted_forms)
        return True


# Formset for adding multiple stems to a piece
StemFormSet = inlineformset_factory(
    Piece,
    Stem,
    formset=BaseStemFormSet,  # Use custom formset
    fields=['instrument_name', 'audio_file', 'order'],
    extra=3,  # Show 3 empty forms by default
    can_delete=True,
    validate_min=False,  # Don't require minimum number of stems
    validate_max=False,  # Don't enforce maximum
    widgets={
        'instrument_name': forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
            'placeholder': 'e.g., Piano, Metronome, Backing Track'
        }),
        'audio_file': forms.FileInput(attrs={
            'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
        }),
        'order': forms.NumberInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
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


class PieceCollectionForm(forms.ModelForm):
    """Form for creating/editing piece collections"""

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

        return instance

    def save_m2m(self):
        """Override to also save new tags after the instance has been saved"""
        super().save_m2m()
        if hasattr(self, '_new_tags_to_add') and self._new_tags_to_add:
            for tag in self._new_tags_to_add:
                self.instance.tags.add(tag)


class CollectionPieceForm(forms.ModelForm):
    """Simplified form for adding/editing pieces within a collection"""

    class Meta:
        model = Piece
        fields = ['title', 'order_in_collection', 'svg_image', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'placeholder': 'e.g., Exercise 1'
            }),
            'order_in_collection': forms.NumberInput(attrs={
                'class': 'w-24 px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'min': '0'
            }),
            'svg_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'rows': 2,
                'placeholder': 'Optional notes for this piece...'
            }),
        }
        labels = {
            'title': 'Piece Title',
            'order_in_collection': 'Order',
            'svg_image': 'Score Image (Optional)',
            'description': 'Notes (Optional)',
        }


class BaseCollectionPieceFormSet(forms.BaseInlineFormSet):
    """Custom formset for pieces in a collection"""

    def clean(self):
        super().clean()
        # Could add validation here if needed

    def is_valid(self):
        if not super().is_valid():
            for i, form in enumerate(self.forms):
                if not form.instance.pk and not form.has_changed():
                    form._errors = {}
            return not any(form.errors for form in self.forms if form not in self.deleted_forms)
        return True


# Formset for adding/editing pieces within a collection
CollectionPieceFormSet = inlineformset_factory(
    PieceCollection,
    Piece,
    form=CollectionPieceForm,
    formset=BaseCollectionPieceFormSet,
    fk_name='collection',
    fields=['title', 'order_in_collection', 'svg_image', 'description'],
    extra=3,
    can_delete=True,
    validate_min=False,
    validate_max=False,
)


class QuickAddPiecesForm(forms.Form):
    """
    Form for quickly adding multiple simple pieces to a collection.
    Allows batch creation with auto-generated titles and single audio track per piece.
    """
    title_prefix = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
            'placeholder': 'e.g., Exercise, Pattern, Rhythm'
        }),
        label='Title Prefix',
        help_text='Each piece will be named: "[Prefix] 1", "[Prefix] 2", etc.'
    )

    start_number = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-32 px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
            'min': '1'
        }),
        label='Starting Number',
        help_text='Number to start counting from'
    )

    track_name = forms.CharField(
        max_length=100,
        initial='Backing Track',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
            'placeholder': 'e.g., Backing Track, Piano, Full Mix'
        }),
        label='Track Name',
        help_text='Name for the audio track (same for all pieces)'
    )

    audio_files = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
            'multiple': True,
            'accept': 'audio/*'
        }),
        label='Audio Files',
        help_text='Select multiple audio files. They will be assigned to pieces in alphabetical order by filename.',
        required=False  # We validate in the view since FileField doesn't handle multiple natively
    )

    def clean_audio_files(self):
        """Validate that files are audio files"""
        # This is handled in the view since FileField doesn't support multiple files natively
        return self.cleaned_data.get('audio_files')
