from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import TestDocument
from .forms import TestDocumentForm


def index(request):
    """List all test documents"""
    documents = TestDocument.objects.all()
    return render(request, 'ckeditor_poc/index.html', {'documents': documents})


def create(request):
    """Create a new test document"""
    if request.method == 'POST':
        form = TestDocumentForm(request.POST)
        if form.is_valid():
            document = form.save()
            messages.success(request, 'Document created successfully!')
            return redirect('ckeditor_poc:view', pk=document.pk)
    else:
        form = TestDocumentForm()

    return render(request, 'ckeditor_poc/create.html', {'form': form})


def edit(request, pk):
    """Edit an existing test document"""
    document = get_object_or_404(TestDocument, pk=pk)

    if request.method == 'POST':
        form = TestDocumentForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Document updated successfully!')
            return redirect('ckeditor_poc:view', pk=document.pk)
    else:
        form = TestDocumentForm(instance=document)

    return render(request, 'ckeditor_poc/edit.html', {'form': form, 'document': document})


def view(request, pk):
    """View a test document"""
    document = get_object_or_404(TestDocument, pk=pk)
    return render(request, 'ckeditor_poc/view.html', {'document': document})


def delete(request, pk):
    """Delete a test document"""
    document = get_object_or_404(TestDocument, pk=pk)

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted successfully!')
        return redirect('ckeditor_poc:index')

    return render(request, 'ckeditor_poc/delete.html', {'document': document})
