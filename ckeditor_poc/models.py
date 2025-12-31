from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class TestDocument(models.Model):
    """Simple model for testing CKEditor 5 in isolation"""
    title = models.CharField(max_length=200)
    content = CKEditor5Field(config_name='default')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
