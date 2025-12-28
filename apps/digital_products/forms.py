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
                'class': 'form-input',
                'placeholder': 'e.g., Baroque Ornamentation Workbook'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Brief description (300 characters max)'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'baroque, intermediate, ensemble (comma-separated)'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '12.99'
            }),
            'featured_image': forms.FileInput(attrs={'class': 'form-file'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
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
                'class': 'form-input',
                'placeholder': 'e.g., Main PDF, Video Tutorial'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': '.pdf,.zip,.mp3,.mp4,.wav,.flac,.avi,.mov'
            }),
            'content_url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://youtube.com/watch?v=... or https://vimeo.com/...'
            }),
            'file_role': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={
                'class': 'form-input',
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
