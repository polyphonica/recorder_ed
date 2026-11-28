from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'area', 'due_date', 'done_at']
    list_filter = ['area', 'done_at']
    search_fields = ['title', 'owner__username']
