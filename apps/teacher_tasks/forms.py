from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'notes', 'area', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Add a task…',
                                            'maxlength': 300}),
            'notes': forms.Textarea(attrs={'class': 'textarea w-full', 'rows': 3, 'placeholder': 'Notes'}),
            'area': forms.Select(attrs={'class': 'select select-bordered'}),
            'due_date': forms.DateInput(attrs={'class': 'input input-bordered', 'type': 'date'}, format='%Y-%m-%d'),
        }
        labels = {'due_date': 'Due'}
