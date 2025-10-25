from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from django.forms.widgets import Select

from apps.private_teaching.models import Subject

from .models import (
    Lesson, Document, LessonAttachedUrl
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
            'teacher_notes': forms.Textarea(attrs={'rows': 4}),
            'homework': forms.Textarea(attrs={'rows': 4}),
            'private_note': forms.Textarea(attrs={'rows': 4}),
        }


class StudentLessonForm(forms.ModelForm):
    """Form for students to create lesson requests (kept for compatibility)"""
    fee = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(StudentLessonForm, self).__init__(*args, **kwargs)
        data = {'data-base-price': {'': ''}} # empty option
        for f in Subject.objects.all():
            data['data-base-price'][f.id] = f.base_price
        self.fields['subject'].widget = DataAttributesSelect(
            choices= [(f.id, str(f)) for f in Subject.objects.all()],
            data=data
        )
        self.fields['subject'].widget.attrs['onchange'] = "getSubject(this.id);"
        self.fields['subject'].widget.attrs['data-bs-toggle'] = "tooltip"
        self.fields['subject'].widget.attrs['data-bs-placement'] = "top"
        self.fields['subject'].widget.attrs['title'] = "Click to choose subject"
        self.fields['subject'].widget.attrs['data-container'] = "body"
        self.fields['subject'].widget.attrs['data-animation'] = "true"
        self.fields['duration_in_minutes'].widget.attrs['onchange'] = "getDuration(this.id);"
        self.fields['duration_in_minutes'].widget.attrs['data-bs-toggle'] = "tooltip"
        self.fields['duration_in_minutes'].widget.attrs['data-bs-placement'] = "top"
        self.fields['duration_in_minutes'].widget.attrs['title'] = "Click to choose duration"
        self.fields['duration_in_minutes'].widget.attrs['data-container'] = "body"
        self.fields['duration_in_minutes'].widget.attrs['data-animation'] = "true"
        self.fields['lesson_date'].widget = forms.widgets.DateInput(
            attrs={'type': 'date','placeholder': 'yyyy-mm-dd (lesson_date)', 'class': 'form-control'}
            )
        self.fields['lesson_date'].widget.attrs['data-bs-toggle'] = "tooltip"
        self.fields['lesson_date'].widget.attrs['data-bs-placement'] = "top"
        self.fields['lesson_date'].widget.attrs['title'] = "Click to choose date"
        self.fields['lesson_date'].widget.attrs['data-container'] = "body"
        self.fields['lesson_date'].widget.attrs['data-animation'] = "true"
        self.fields['lesson_time'].widget = forms.widgets.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}
            )
        self.fields['lesson_time'].widget.attrs['data-bs-toggle'] = "tooltip"
        self.fields['lesson_time'].widget.attrs['data-bs-placement'] = "top"
        self.fields['lesson_time'].widget.attrs['title'] = "Click to choose time"
        self.fields['lesson_time'].widget.attrs['data-container'] = "body"
        self.fields['lesson_time'].widget.attrs['data-animation'] = "true"
        self.fields['fee'].widget.attrs['disabled'] = "true"
        self.fields['fee'].widget.attrs['placeholder'] = "Price"
        self.fields['fee'].widget.attrs['class'] = "form-control"
        self.fields['duration_in_minutes'].widget.attrs['class'] = "form-control"
        self.fields['subject'].widget.attrs['class'] = "form-control"
        self.fields['location'].widget.attrs['class'] = "form-control"
        self.fields['location'].widget.attrs['data-bs-toggle'] = "tooltip"
        self.fields['location'].widget.attrs['data-bs-placement'] = "top"
        self.fields['location'].widget.attrs['title'] = "Click to choose location"
        self.fields['location'].widget.attrs['data-container'] = "body"
        self.fields['location'].widget.attrs['data-animation'] = "true"

    class Meta:
        model = Lesson
        fields = ('subject', 'lesson_date', 'lesson_time', 'duration_in_minutes', 'location',)

    def save(self, commit=True):
        lesson_form = super(StudentLessonForm, self).save(commit=False)
        duration = lesson_form.duration_in_minutes
        subject_price = lesson_form.subject.base_price
        lesson_form.fee = subject_price * (int(duration)/60)
        if commit:
            lesson_form.save()
        return lesson_form


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


# Formsets for inline editing
DocumentFormSet = inlineformset_factory(
    Lesson, Document, form=DocumentForm,
    extra=1, can_delete=True, can_delete_extra=True
)

LessonUrlsFormSet = inlineformset_factory(
    Lesson, LessonAttachedUrl, form=LessonUrlForm,
    extra=1, can_delete=True, can_delete_extra=True
)