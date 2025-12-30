from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import LessonContentTemplate, Tag


class LessonContentTemplateForm(forms.ModelForm):
    """Form for creating/editing lesson content templates"""

    # Additional field for creating new tags inline
    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all',
            'placeholder': 'e.g., Notation, Scales, Theory'
        }),
        label='New Tags',
        help_text='Enter tag names separated by commas to create and add them to this template'
    )

    class Meta:
        model = LessonContentTemplate
        fields = [
            'title',
            'content',
            'subject',
            'syllabus',
            'grade_level',
            'lesson_number',
            'tags',
            'is_public',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., ABRSM Grade 1 - Lesson 1: Introduction to Notation'
            }),
            'content': CKEditor5Widget(config_name='default'),
            'subject': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all bg-white cursor-pointer'
            }),
            'syllabus': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all bg-white cursor-pointer'
            }),
            'grade_level': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., 1, 2, Beginner, Intermediate'
            }),
            'lesson_number': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., 1, 2, 3...',
                'min': '1'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white',
                'size': '5'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-2 border-gray-300 rounded focus:ring-4 focus:ring-blue-100 cursor-pointer'
            }),
        }
        labels = {
            'title': 'Template Title',
            'content': 'Lesson Content',
            'subject': 'Subject',
            'syllabus': 'Syllabus',
            'grade_level': 'Grade Level',
            'lesson_number': 'Lesson Number',
            'tags': 'Existing Tags',
            'is_public': 'Make Public',
        }
        help_texts = {
            'title': 'Give your template a descriptive title',
            'content': 'Create your lesson content with rich text formatting',
            'subject': 'Select the subject this template is for',
            'syllabus': 'Select the examination board or syllabus',
            'grade_level': 'Specify the grade level (e.g., 1, 2, Beginner, Intermediate)',
            'lesson_number': 'Position of this lesson in a course sequence (optional)',
            'tags': 'Select existing tags (Ctrl+Click to select multiple)',
            'is_public': 'Allow other teachers to browse and use this template',
        }

    def _save_new_tags(self, instance):
        """Helper method to save new tags after instance exists in database"""
        new_tags_str = self.cleaned_data.get('new_tags', '')
        if new_tags_str:
            # Split by commas, strip whitespace, and create tags
            tag_names = [name.strip() for name in new_tags_str.split(',') if name.strip()]
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)

    def save(self, commit=True):
        # Store the original save_m2m so we can wrap it
        if commit:
            instance = super().save(commit=True)
            self._save_new_tags(instance)
        else:
            instance = super().save(commit=False)
            # Override save_m2m to also save new tags
            old_save_m2m = self.save_m2m
            def save_m2m():
                old_save_m2m()
                self._save_new_tags(instance)
            self.save_m2m = save_m2m

        return instance
