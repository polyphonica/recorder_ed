from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import TestDocument


class TestDocumentForm(forms.ModelForm):
    class Meta:
        model = TestDocument
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'style': 'width: 100%; padding: 8px; font-size: 16px;'}),
            'content': CKEditor5Widget(config_name='default'),
        }
