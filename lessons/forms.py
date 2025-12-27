from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from django.forms.widgets import Select
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.private_teaching.models import Subject

from .models import (
    Lesson, Document, LessonAttachedUrl, PrivateLessonPiece, LessonAssignment
)


User = settings.AUTH_USER_MODEL


class DataAttributesSelect(Select):
    # https://www.abidibo.net/blog/2017/10/16/add-data-attributes-option-tags-django-admin-select-field/
 
    def __init__(self, attrs=None, choices=(), data={}):
        super(DataAttributesSelect, self).__init__(attrs, choices)
        self.data = data
 
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super(DataAttributesSelect, self).create_option(name, value, label, selected, index, subindex=None, attrs=None)
        # adds the data-attributes to the attrs context var
        for data_attr, values in self.data.items():
            option['attrs'][data_attr] = values[option['value']]
        return option


class LessonForm(forms.ModelForm):
    zoom_link = forms.URLField(required=False)

    def __init__(self, *args, **kwargs):
        super(LessonForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            # Skip CKEditor field - it has its own styling
            if visible.name != 'lesson_content':
                visible.field.widget.attrs['class'] = 'form-control'
                visible.field.widget.attrs['placeholder'] = visible.field.label

    def clean_zoom_link(self):
        """Ensure empty zoom links are saved as empty string, not invalid URL"""
        zoom_link = self.cleaned_data.get('zoom_link')
        if zoom_link:
            zoom_link = zoom_link.strip()
        # Return empty string if blank, otherwise return the URL
        return zoom_link if zoom_link else ''

    class Meta:
        model = Lesson
        fields = (
            'location', 'attendance', 'zoom_link', 'lesson_content',
            'teacher_notes', 'homework', 'private_note', 'status'
        )
        widgets = {
            'lesson_content': CKEditor5Widget(config_name='default'),
            'teacher_notes': forms.Textarea(attrs={'rows': 4}),
            'homework': forms.Textarea(attrs={'rows': 4}),
            'private_note': forms.Textarea(attrs={'rows': 4}),
        }


class DocumentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['placeholder'] = visible.field.label

    class Meta:
        model = Document
        exclude = ('lesson',)


class LessonUrlForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(LessonUrlForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['placeholder'] = visible.field.label

    class Meta:
        model = LessonAttachedUrl
        exclude = ('lesson',)


class PrivateLessonPieceForm(forms.ModelForm):
    """Form for assigning playalong pieces to private lessons"""

    def __init__(self, *args, **kwargs):
        super(PrivateLessonPieceForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = PrivateLessonPiece
        fields = ('piece', 'order', 'is_visible', 'is_optional', 'instructions')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 3}),
        }


# Formsets for inline editing
DocumentFormSet = inlineformset_factory(
    Lesson, Document, form=DocumentForm,
    extra=1, can_delete=True, can_delete_extra=True
)

LessonUrlsFormSet = inlineformset_factory(
    Lesson, LessonAttachedUrl, form=LessonUrlForm,
    extra=1, can_delete=True, can_delete_extra=True
)

PrivateLessonPieceFormSet = inlineformset_factory(
    Lesson, PrivateLessonPiece, form=PrivateLessonPieceForm,
    extra=1, can_delete=True, can_delete_extra=True
)


class LessonAssignmentForm(forms.ModelForm):
    """Form for assigning homework assignments to lessons"""

    def __init__(self, *args, **kwargs):
        super(LessonAssignmentForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = LessonAssignment
        fields = ('assignment', 'due_date', 'order', 'instructions')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


LessonAssignmentFormSet = inlineformset_factory(
    Lesson, LessonAssignment, form=LessonAssignmentForm,
    extra=1, can_delete=True, can_delete_extra=True
)