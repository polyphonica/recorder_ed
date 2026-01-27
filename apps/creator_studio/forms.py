"""
Creator Studio Forms
"""

import os
from django import forms


class AudioConverterForm(forms.Form):
    """Form for audio conversion parameters."""

    FORMAT_CHOICES = [
        ('mp3', 'MP3 - Compressed, widely compatible'),
        ('wav', 'WAV - Uncompressed, high quality'),
        ('ogg', 'OGG - Open format, good compression'),
        ('m4a', 'M4A - Apple format, good quality'),
        ('aac', 'AAC - Advanced Audio Coding'),
    ]

    audio_file = forms.FileField(
        label='Audio File',
        help_text='Supported formats: MP3, WAV, OGG, M4A, AAC, AIFF. Max size: 20MB.'
    )

    output_format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='mp3',
        label='Output Format'
    )

    playback_speed = forms.FloatField(
        min_value=0.5,
        max_value=2.0,
        initial=1.0,
        required=False,
        label='Playback Speed',
        help_text='0.5x (slower) to 2.0x (faster). Default: 1.0x'
    )

    trim_start = forms.FloatField(
        min_value=0,
        required=False,
        label='Trim Start (seconds)',
        help_text='Leave empty to start from beginning'
    )

    trim_end = forms.FloatField(
        min_value=0,
        required=False,
        label='Trim End (seconds)',
        help_text='Leave empty to use full duration'
    )

    normalize = forms.BooleanField(
        required=False,
        initial=False,
        label='Normalize Volume',
        help_text='Adjust volume to consistent level'
    )

    def clean_audio_file(self):
        file = self.cleaned_data['audio_file']

        # Check file size (20MB limit from settings)
        max_size = 20 * 1024 * 1024
        if file.size > max_size:
            raise forms.ValidationError(
                f'File size exceeds {max_size // (1024*1024)}MB limit.'
            )

        # Check file extension
        valid_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.aiff', '.aif']
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in valid_extensions:
            raise forms.ValidationError(
                f'Unsupported file type. Allowed: {", ".join(valid_extensions)}'
            )

        return file

    def clean(self):
        cleaned_data = super().clean()
        trim_start = cleaned_data.get('trim_start')
        trim_end = cleaned_data.get('trim_end')

        if trim_start is not None and trim_end is not None:
            if trim_start >= trim_end:
                raise forms.ValidationError(
                    'Trim end must be greater than trim start.'
                )

        return cleaned_data


class SaveAsStemForm(forms.Form):
    """
    Form for saving a converted audio file directly as a stem on a piece.
    """

    PIECE_CHOICES = [
        ('existing', 'Add to existing piece'),
        ('new', 'Create new piece'),
    ]

    piece_choice = forms.ChoiceField(
        choices=PIECE_CHOICES,
        initial='existing',
        widget=forms.RadioSelect(attrs={'class': 'radio radio-primary'})
    )

    piece_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )

    new_piece_title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter piece title...'
        })
    )

    instrument_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Piano, Metronome, Backing Track'
        }),
        help_text='Name for this audio track'
    )

    stem_order = forms.IntegerField(
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-24',
            'min': '0'
        }),
        help_text='Display order (0 = first)'
    )

    def clean(self):
        cleaned_data = super().clean()
        piece_choice = cleaned_data.get('piece_choice')
        piece_id = cleaned_data.get('piece_id')
        new_piece_title = cleaned_data.get('new_piece_title')

        if piece_choice == 'existing' and not piece_id:
            raise forms.ValidationError(
                'Please select an existing piece.'
            )

        if piece_choice == 'new' and not new_piece_title:
            raise forms.ValidationError(
                'Please enter a title for the new piece.'
            )

        return cleaned_data
