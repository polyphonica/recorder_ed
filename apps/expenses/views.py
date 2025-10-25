from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
import csv
import json
from datetime import datetime, timedelta

from .models import Expense, ExpenseCategory
from .forms import ExpenseForm, ExpenseCategoryForm, ExpenseFilterForm
from .mixins import TeacherOrAdminRequiredMixin


class ExpenseDashboardView(TeacherOrAdminRequiredMixin, TemplateView):
    """Dashboard view showing expense analytics and summaries"""
    template_name = 'expenses/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        # Build base queryset
        expenses = Expense.objects.filter(created_by=self.request.user)

        # Apply date filters
        if date_from:
            expenses = expenses.filter(date__gte=date_from)
        if date_to:
            expenses = expenses.filter(date__lte=date_to)

        # Total expenses
        total = expenses.aggregate(total=Sum('amount'))['total'] or 0

        # Breakdown by business area
        by_business_area = expenses.values('business_area').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        # Breakdown by category
        by_category = expenses.values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]  # Top 10 categories

        # Monthly trend (last 12 months)
        twelve_months_ago = timezone.now().date() - timedelta(days=365)
        monthly_expenses = expenses.filter(
            date__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        # Recent expenses
        recent_expenses = expenses.order_by('-date', '-created_at')[:10]

        context.update({
            'total_expenses': total,
            'by_business_area': by_business_area,
            'by_category': by_category,
            'monthly_expenses': list(monthly_expenses),
            'recent_expenses': recent_expenses,
            'date_from': date_from,
            'date_to': date_to,
            'expense_count': expenses.count(),
        })

        return context


class ExpenseListView(TeacherOrAdminRequiredMixin, ListView):
    """List view of all expenses with filtering"""
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 25

    def get_queryset(self):
        queryset = Expense.objects.filter(created_by=self.request.user).select_related(
            'category', 'workshop'
        )

        # Get filter parameters
        business_area = self.request.GET.get('business_area', '')
        category = self.request.GET.get('category', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        search = self.request.GET.get('search', '')

        # Apply filters
        if business_area:
            queryset = queryset.filter(business_area=business_area)

        if category:
            queryset = queryset.filter(category_id=category)

        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(supplier__icontains=search) |
                Q(notes__icontains=search)
            )

        return queryset.order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ExpenseFilterForm(self.request.GET)

        # Calculate total for filtered results
        total = self.get_queryset().aggregate(total=Sum('amount'))['total'] or 0
        context['filtered_total'] = total

        return context


class ExpenseCreateView(TeacherOrAdminRequiredMixin, CreateView):
    """View for creating new expense"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Expense added successfully!')
        return super().form_valid(form)


class ExpenseUpdateView(TeacherOrAdminRequiredMixin, UpdateView):
    """View for updating existing expense"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def get_queryset(self):
        # Only allow editing own expenses
        return Expense.objects.filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Expense updated successfully!')
        return super().form_valid(form)


class ExpenseDeleteView(TeacherOrAdminRequiredMixin, DeleteView):
    """View for deleting expense"""
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expenses:expense_list')

    def get_queryset(self):
        # Only allow deleting own expenses
        return Expense.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expense deleted successfully!')
        return super().delete(request, *args, **kwargs)


class CategoryListView(TeacherOrAdminRequiredMixin, ListView):
    """List view of all expense categories"""
    model = ExpenseCategory
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'
    ordering = ['name']


class CategoryCreateView(TeacherOrAdminRequiredMixin, CreateView):
    """View for creating new category"""
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('expenses:category_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Category "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class CategoryUpdateView(TeacherOrAdminRequiredMixin, UpdateView):
    """View for updating category"""
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('expenses:category_list')

    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class CategoryDeleteView(TeacherOrAdminRequiredMixin, DeleteView):
    """View for deactivating category (soft delete)"""
    model = ExpenseCategory
    template_name = 'expenses/category_confirm_delete.html'
    success_url = reverse_lazy('expenses:category_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete - just deactivate
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Category "{self.object.name}" has been deactivated.')
        return redirect(self.success_url)


class ExpenseExportCSVView(TeacherOrAdminRequiredMixin, View):
    """Export expenses to CSV"""

    def get(self, request, *args, **kwargs):
        # Get filtered queryset using same logic as list view
        expenses = Expense.objects.filter(created_by=request.user).select_related(
            'category', 'workshop'
        )

        # Apply same filters as list view
        business_area = request.GET.get('business_area', '')
        category = request.GET.get('category', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        search = request.GET.get('search', '')

        if business_area:
            expenses = expenses.filter(business_area=business_area)
        if category:
            expenses = expenses.filter(category_id=category)
        if date_from:
            expenses = expenses.filter(date__gte=date_from)
        if date_to:
            expenses = expenses.filter(date__lte=date_to)
        if search:
            expenses = expenses.filter(
                Q(description__icontains=search) |
                Q(supplier__icontains=search) |
                Q(notes__icontains=search)
            )

        expenses = expenses.order_by('-date')

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="expenses_{timezone.now().strftime("%Y%m%d")}.csv"'

        writer = csv.writer(response)

        # Write header
        writer.writerow([
            'Date',
            'Business Area',
            'Category',
            'Description',
            'Supplier',
            'Amount (£)',
            'Payment Method',
            'Workshop',
            'Notes',
            'Receipt File'
        ])

        # Write data
        for expense in expenses:
            writer.writerow([
                expense.date.strftime('%Y-%m-%d'),
                expense.get_business_area_display(),
                expense.category.name,
                expense.description,
                expense.supplier,
                f'{expense.amount:.2f}',
                expense.get_payment_method_display(),
                expense.workshop.title if expense.workshop else '',
                expense.notes,
                'Yes' if expense.receipt_file else 'No'
            ])

        return response
