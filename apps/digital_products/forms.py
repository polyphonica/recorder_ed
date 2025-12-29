from django import forms
from django.forms import inlineformset_factory
from .models import DigitalProduct, ProductFile, ProductReview


class ProductForm(forms.ModelForm):
    """Form for creating/editing digital products"""

    class Meta:
        model = DigitalProduct
        fields = [
            'title',
            'short_description',
            'description',
            'category',
            'product_type',
            'tags',
            'price',
            'featured_image',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'placeholder': 'e.g., Baroque Ornamentation Workbook'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all resize-none',
                'rows': 3,
                'placeholder': 'Brief summary that will appear in product listings'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all',
                'rows': 6,
                'placeholder': 'Detailed description of your product, including what students will learn and receive'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'product_type': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all bg-white cursor-pointer'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all',
                'placeholder': 'baroque, intermediate, ensemble'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '12.99'
            }),
            'featured_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-orange-500 focus:ring-4 focus:ring-orange-100 transition-all bg-white cursor-pointer'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

        # Make description optional for drafts
        if not self.instance.pk or self.instance.status == 'draft':
            self.fields['description'].required = False
            self.fields['featured_image'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.teacher:
            instance.teacher = self.teacher
        if commit:
            instance.save()
        return instance


class ProductFileForm(forms.ModelForm):
    """Form for uploading product files or providing URLs"""

    class Meta:
        model = ProductFile
        fields = ['title', 'file', 'content_url', 'file_role', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'placeholder': 'e.g., Main PDF, Video Tutorial'
            }),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all bg-white cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
                'accept': '.pdf,.zip,.mp3,.mp4,.wav,.flac,.avi,.mov'
            }),
            'content_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'placeholder': 'https://youtube.com/watch?v=... or https://vimeo.com/...'
            }),
            'file_role': forms.Select(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all bg-white cursor-pointer'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 text-base border-2 border-gray-300 rounded-lg focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all',
                'min': '0'
            }),
        }

    def clean(self):
        """Validate that at least file or URL is provided (can have both)"""
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        content_url = cleaned_data.get('content_url')

        if not file and not content_url:
            raise forms.ValidationError(
                'Please provide at least a file upload or a URL (or both).'
            )

        return cleaned_data

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (50 MB max)
            if file.size > 50 * 1024 * 1024:  # 50 MB in bytes
                raise forms.ValidationError(
                    f"File too large. Maximum size is 50 MB. Your file is {file.size / (1024 * 1024):.2f} MB."
                )
        return file


# Formset for managing multiple files per product
ProductFileFormSet = inlineformset_factory(
    DigitalProduct,
    ProductFile,
    form=ProductFileForm,
    extra=1,  # Show 1 empty form by default
    can_delete=True,
    min_num=0,  # Files are optional during creation
    validate_min=False
)


class ProductReviewForm(forms.ModelForm):
    """Form for submitting product reviews"""

    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Stars') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Summarize your review (e.g., Excellent practice materials)'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Share your experience with this product...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.purchase = kwargs.pop('purchase', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.purchase:
            instance.purchase = self.purchase
            instance.student = self.purchase.student
            instance.product = self.purchase.product
        if commit:
            instance.save()
        return instance
