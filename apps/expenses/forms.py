from django import forms
from .models import Expense, ExpenseCategory


class ExpenseCategoryForm(forms.ModelForm):
    """Form for creating and editing expense categories"""

    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'e.g., Travel, Sheet Music, Professional Fees'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Optional description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }


class ExpenseForm(forms.ModelForm):
    """Form for creating and editing expenses"""

    # Override category field to allow creating new category on the fly
    new_category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter new category name'
        }),
        help_text='If the category you need doesn\'t exist, enter a new one here'
    )

    class Meta:
        model = Expense
        fields = [
            'date', 'business_area', 'category', 'description',
            'supplier', 'amount', 'payment_method',
            'receipt_file', 'notes', 'workshop'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'business_area': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'category': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'What was purchased?'}),
            'supplier': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Vendor or supplier name'}),
            'amount': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01', 'placeholder': '0.00'}),
            'payment_method': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'receipt_file': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Additional notes (optional)'}),
            'workshop': forms.Select(attrs={'class': 'select select-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Only show active categories
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)

        # Make category not required if new_category is provided
        self.fields['category'].required = False

        # Only show workshops for this user (if they're a teacher)
        if user:
            from apps.workshops.models import Workshop
            self.fields['workshop'].queryset = Workshop.objects.filter(
                instructor=user
            ).order_by('-created_at')

        # Set default date to today
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        new_category = cleaned_data.get('new_category')

        # If new category is provided, create it
        if new_category:
            category_obj, created = ExpenseCategory.objects.get_or_create(
                name=new_category.strip(),
                defaults={'created_by': self.instance.created_by if self.instance.pk else None}
            )
            cleaned_data['category'] = category_obj
        elif not category:
            raise forms.ValidationError('Please select an existing category or create a new one.')

        return cleaned_data


class ExpenseFilterForm(forms.Form):
    """Form for filtering expenses"""

    business_area = forms.ChoiceField(
        required=False,
        choices=[('', 'All Business Areas')] + list(Expense.BUSINESS_AREA_CHOICES),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )

    category = forms.ModelChoiceField(
        required=False,
        queryset=ExpenseCategory.objects.filter(is_active=True),
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'})
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Search description or supplier...'})
    )
