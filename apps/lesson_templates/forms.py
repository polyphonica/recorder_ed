from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import LessonContentTemplate, TemplateCategory, Tag


class TemplateCategoryForm(forms.ModelForm):
    """Form for creating/editing template categories"""

    class Meta:
        model = TemplateCategory
        fields = [
            'name',
            'description',
            'subject',
            'syllabus',
            'grade_level',
            'color',
            'display_order',
            'is_public',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., Rhythm Fundamentals, ABRSM Grade 1 Theory'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'rows': 3,
                'placeholder': 'Optional description of what this category covers'
            }),
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
            'color': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all bg-white cursor-pointer'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': '0',
                'min': '0'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-2 border-gray-300 rounded focus:ring-4 focus:ring-blue-100 cursor-pointer'
            }),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'subject': 'Subject (Optional)',
            'syllabus': 'Syllabus (Optional)',
            'grade_level': 'Grade Level (Optional)',
            'color': 'Badge Color',
            'display_order': 'Display Order',
            'is_public': 'Make Public',
        }
        help_texts = {
            'name': 'Give your category a clear, descriptive name',
            'description': 'Briefly describe what lessons in this category cover',
            'subject': 'Link to a specific subject, or leave blank for general categories',
            'syllabus': 'Link to an examination board, or leave blank',
            'grade_level': 'Specify a grade level, or leave blank',
            'color': 'Choose a color for the category badge',
            'display_order': 'Lower numbers appear first in the list',
            'is_public': 'Allow other teachers to see this category',
        }


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
            'category',
            'lesson_number',
            'subject',
            'syllabus',
            'grade_level',
            'tags',
            'is_public',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., Introduction to Note Values'
            }),
            'content': CKEditor5Widget(config_name='default'),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all bg-white cursor-pointer'
            }),
            'lesson_number': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., 1, 2, 3...',
                'min': '1'
            }),
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
            'category': 'Category',
            'lesson_number': 'Lesson Number',
            'subject': 'Subject (Override)',
            'syllabus': 'Syllabus (Override)',
            'grade_level': 'Grade Level (Override)',
            'tags': 'Existing Tags',
            'is_public': 'Make Public',
        }
        help_texts = {
            'title': 'Give your template a descriptive title',
            'content': 'Create your lesson content with rich text formatting',
            'category': 'Select a category/series for this template, or leave blank for standalone lessons',
            'lesson_number': 'Position within the category (1, 2, 3...). Numbers are independent per category.',
            'subject': 'Override category subject, or set for standalone templates',
            'syllabus': 'Override category syllabus, or set for standalone templates',
            'grade_level': 'Override category grade, or set for standalone templates',
            'tags': 'Select existing tags (Ctrl+Click to select multiple)',
            'is_public': 'Allow other teachers to browse and use this template',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter categories to show only user's own or public categories
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = TemplateCategory.objects.filter(
                Q(created_by=user) | Q(is_public=True)
            ).distinct().order_by('display_order', 'name')
        self.fields['category'].empty_label = '-- Standalone (no category) --'

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
