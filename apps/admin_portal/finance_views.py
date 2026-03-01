"""
Admin Portal Finance views.
Platform-level financial reporting for the platform owner.
"""
import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from django.contrib import messages

from .decorators import admin_required


@admin_required
def platform_finance_dashboard(request):
    """
    Platform finance dashboard showing commission income, Stripe fees, and net profit.
    """
    from apps.payments.finance_service import FinanceService
    from apps.expenses.models import Expense

    # Get date range from query params
    days = request.GET.get('days', '30')
    start_date = None
    end_date = None

    now = timezone.now()

    if days == '7':
        start_date = now - timedelta(days=7)
        date_label = 'Last 7 days'
    elif days == '30':
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'
    elif days == '90':
        start_date = now - timedelta(days=90)
        date_label = 'Last 90 days'
    elif days == '365':
        start_date = now - timedelta(days=365)
        date_label = 'Last 12 months'
    elif days == 'all':
        date_label = 'All time'
    else:
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'

    end_date = now

    # Get platform finance summary
    summary = FinanceService.get_platform_finance_summary(start_date, end_date)

    # Get recent transactions
    recent_transactions = FinanceService.get_platform_recent_transactions(limit=10)

    # Get operating expenses (general business expenses)
    expenses_query = Expense.objects.filter(business_area='general')
    if start_date:
        expenses_query = expenses_query.filter(date__gte=start_date.date())
    if end_date:
        expenses_query = expenses_query.filter(date__lte=end_date.date())

    total_expenses = expenses_query.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Calculate total platform expenses (Stripe fees + operating expenses)
    total_platform_expenses = summary['total_stripe_fees'] + total_expenses

    # Calculate net platform profit
    net_platform_profit = summary['net_platform_income'] - total_expenses

    # Domain display names
    domain_display = {
        'workshops': 'Workshops',
        'courses': 'Courses',
        'private_teaching': 'Private Teaching',
        'digital_products': 'Digital Products',
    }

    # Build domain summary with display names
    domain_summary = []
    for domain, data in summary['by_domain'].items():
        domain_summary.append({
            'domain': domain,
            'display_name': domain_display.get(domain, domain.title()),
            'gross': data['gross'],
            'commission': data['commission'],
            'stripe_fees': data['stripe_fees'],
            'net_income': data['net_income'],
            'count': data['count'],
        })

    # Sort by commission descending
    domain_summary.sort(key=lambda x: x['commission'], reverse=True)

    # Serialize monthly trend for Chart.js (Decimal/datetime aren't JSON-serialisable)
    trend = summary['monthly_trend']
    monthly_trend_json = json.dumps({
        'labels': [item['month'].strftime('%b %Y') for item in trend],
        'commission': [float(item['commission']) for item in trend],
        'stripe_fees': [float(item['stripe_fees']) for item in trend],
        'net_income': [float(item['net_income']) for item in trend],
    })

    context = {
        # Date range
        'days': days,
        'date_label': date_label,
        'start_date': start_date,
        'end_date': end_date,

        # Summary metrics
        'total_gross': summary['total_gross'],
        'total_commission': summary['total_commission'],
        'total_stripe_fees': summary['total_stripe_fees'],
        'net_platform_income': summary['net_platform_income'],
        'transaction_count': summary['transaction_count'],

        # Expenses and profit
        'total_expenses': total_expenses,
        'total_platform_expenses': total_platform_expenses,
        'net_platform_profit': net_platform_profit,

        # Domain breakdown
        'domain_summary': domain_summary,

        # Monthly trend for charts
        'monthly_trend_json': monthly_trend_json,

        # Recent transactions
        'recent_transactions': recent_transactions,
    }

    return render(request, 'admin_portal/finance/dashboard.html', context)


@admin_required
def platform_revenue_detail(request):
    """
    Detailed revenue breakdown by domain.
    """
    from apps.payments.finance_service import FinanceService

    # Get date range from query params
    days = request.GET.get('days', '30')
    start_date = None
    end_date = None

    now = timezone.now()

    if days == '7':
        start_date = now - timedelta(days=7)
        date_label = 'Last 7 days'
    elif days == '30':
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'
    elif days == '90':
        start_date = now - timedelta(days=90)
        date_label = 'Last 90 days'
    elif days == '365':
        start_date = now - timedelta(days=365)
        date_label = 'Last 12 months'
    elif days == 'all':
        date_label = 'All time'
    else:
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'

    end_date = now

    # Get platform finance summary
    summary = FinanceService.get_platform_finance_summary(start_date, end_date)

    # Domain display names
    domain_display = {
        'workshops': 'Workshops',
        'courses': 'Courses',
        'private_teaching': 'Private Teaching',
        'digital_products': 'Digital Products',
    }

    # Build detailed domain breakdown
    domain_details = []
    for domain, data in summary['by_domain'].items():
        # Calculate commission percentage of gross
        if data['gross'] > 0:
            commission_pct = (data['commission'] / data['gross']) * 100
            fees_pct = (data['stripe_fees'] / data['gross']) * 100 if data['stripe_fees'] else Decimal('0')
        else:
            commission_pct = Decimal('0')
            fees_pct = Decimal('0')

        domain_details.append({
            'domain': domain,
            'display_name': domain_display.get(domain, domain.title()),
            'gross': data['gross'],
            'commission': data['commission'],
            'commission_pct': commission_pct,
            'stripe_fees': data['stripe_fees'],
            'fees_pct': fees_pct,
            'net_income': data['net_income'],
            'count': data['count'],
        })

    # Sort by commission descending
    domain_details.sort(key=lambda x: x['commission'], reverse=True)

    if request.GET.get('export') == 'csv':
        period = 'all_time' if days == 'all' else f'last_{days}days'
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="revenue_detail_{period}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Domain', 'Transactions', 'Gross Revenue (£)', 'Commission (£)',
                         'Stripe Fees (£)', 'Fee %', 'Net Income (£)'])
        for d in domain_details:
            writer.writerow([
                d['display_name'],
                d['count'],
                f"{d['gross']:.2f}",
                f"{d['commission']:.2f}",
                f"{d['stripe_fees']:.2f}" if d['stripe_fees'] else '0.00',
                f"{d['fees_pct']:.2f}" if d['fees_pct'] else '0.00',
                f"{d['net_income']:.2f}",
            ])
        writer.writerow([
            'TOTAL', '',
            f"{summary['total_gross']:.2f}",
            f"{summary['total_commission']:.2f}",
            f"{summary['total_stripe_fees']:.2f}",
            '',
            f"{summary['net_platform_income']:.2f}",
        ])
        return response

    context = {
        'days': days,
        'date_label': date_label,
        'domain_details': domain_details,
        'total_gross': summary['total_gross'],
        'total_commission': summary['total_commission'],
        'total_stripe_fees': summary['total_stripe_fees'],
        'net_platform_income': summary['net_platform_income'],
    }

    return render(request, 'admin_portal/finance/revenue_detail.html', context)


@admin_required
def stripe_fees_detail(request):
    """
    Detailed Stripe fees analysis.
    """
    from apps.payments.finance_service import FinanceService

    # Get date range from query params
    days = request.GET.get('days', '30')
    start_date = None
    end_date = None

    now = timezone.now()

    if days == '7':
        start_date = now - timedelta(days=7)
        date_label = 'Last 7 days'
    elif days == '30':
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'
    elif days == '90':
        start_date = now - timedelta(days=90)
        date_label = 'Last 90 days'
    elif days == '365':
        start_date = now - timedelta(days=365)
        date_label = 'Last 12 months'
    elif days == 'all':
        date_label = 'All time'
    else:
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'

    end_date = now

    # Get Stripe fees summary
    fees_summary = FinanceService.get_platform_stripe_fees_summary(start_date, end_date)

    # Get recent transactions with fees
    from apps.payments.models import StripePayment

    recent_with_fees = StripePayment.objects.filter(
        status='completed',
        stripe_fee__isnull=False
    ).select_related('student', 'teacher').order_by('-created_at')[:20]

    if request.GET.get('export') == 'csv':
        period = 'all_time' if days == 'all' else f'last_{days}days'
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="stripe_fees_{period}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Domain', 'Student', 'Gross Amount (£)', 'Stripe Fee (£)', 'Fee %'])
        all_transactions = StripePayment.objects.filter(
            status='completed',
            stripe_fee__isnull=False,
        ).select_related('student').order_by('-created_at')
        if start_date:
            all_transactions = all_transactions.filter(created_at__gte=start_date)
        if end_date:
            all_transactions = all_transactions.filter(created_at__lte=end_date)
        for tx in all_transactions:
            fee_pct = (tx.stripe_fee / tx.total_amount * 100) if tx.total_amount else Decimal('0')
            writer.writerow([
                tx.created_at.strftime('%Y-%m-%d'),
                tx.get_domain_display(),
                tx.student.get_full_name() if tx.student else '',
                f"{tx.total_amount:.2f}",
                f"{tx.stripe_fee:.2f}",
                f"{fee_pct:.2f}",
            ])
        return response

    context = {
        'days': days,
        'date_label': date_label,
        'fees_summary': fees_summary,
        'recent_with_fees': recent_with_fees,
    }

    return render(request, 'admin_portal/finance/stripe_fees.html', context)


@admin_required
def platform_expenses_list(request):
    """
    Platform operating expenses (general business area).
    """
    from apps.expenses.models import Expense

    # Get date range from query params
    days = request.GET.get('days', '30')
    start_date = None
    end_date = None

    now = timezone.now()

    if days == '7':
        start_date = now - timedelta(days=7)
        date_label = 'Last 7 days'
    elif days == '30':
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'
    elif days == '90':
        start_date = now - timedelta(days=90)
        date_label = 'Last 90 days'
    elif days == '365':
        start_date = now - timedelta(days=365)
        date_label = 'Last 12 months'
    elif days == 'all':
        date_label = 'All time'
    else:
        start_date = now - timedelta(days=30)
        date_label = 'Last 30 days'

    end_date = now

    # Get general expenses
    expenses = Expense.objects.filter(business_area='general')
    if start_date:
        expenses = expenses.filter(date__gte=start_date.date())
    if end_date:
        expenses = expenses.filter(date__lte=end_date.date())

    expenses = expenses.select_related('category').order_by('-date')

    # Aggregate by category
    expenses_by_category = Expense.objects.filter(business_area='general')
    if start_date:
        expenses_by_category = expenses_by_category.filter(date__gte=start_date.date())
    if end_date:
        expenses_by_category = expenses_by_category.filter(date__lte=end_date.date())

    expenses_by_category = expenses_by_category.values(
        'category__name'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total')

    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    if request.GET.get('export') == 'csv':
        period = 'all_time' if days == 'all' else f'last_{days}days'
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="expenses_{period}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Category', 'Description', 'Supplier', 'Amount (£)',
                         'Payment Method', 'Notes'])
        for expense in expenses:
            writer.writerow([
                expense.date.strftime('%Y-%m-%d'),
                expense.category.name if expense.category else '',
                expense.description,
                expense.supplier or '',
                f"{expense.amount:.2f}",
                expense.get_payment_method_display(),
                expense.notes or '',
            ])
        return response

    context = {
        'days': days,
        'date_label': date_label,
        'expenses': expenses,
        'expenses_by_category': expenses_by_category,
        'total_expenses': total_expenses,
    }

    return render(request, 'admin_portal/finance/expenses.html', context)


@admin_required
def platform_expense_add(request):
    """
    Add a new platform operating expense.
    Business area is automatically set to 'general'.
    """
    from apps.expenses.models import Expense, ExpenseCategory

    if request.method == 'POST':
        # Get form data
        date = request.POST.get('date')
        category_id = request.POST.get('category')
        new_category_name = request.POST.get('new_category', '').strip()
        description = request.POST.get('description')
        supplier = request.POST.get('supplier')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        notes = request.POST.get('notes', '')
        receipt_file = request.FILES.get('receipt_file')

        # Handle category - either existing or create new
        if new_category_name:
            category, created = ExpenseCategory.objects.get_or_create(
                name=new_category_name,
                defaults={'created_by': request.user}
            )
        elif category_id:
            category = get_object_or_404(ExpenseCategory, pk=category_id)
        else:
            messages.error(request, 'Please select a category or create a new one.')
            return redirect('admin_portal:finance:expense_add')

        # Create expense
        expense = Expense.objects.create(
            date=date,
            business_area='general',  # Always 'general' for admin expenses
            category=category,
            description=description,
            supplier=supplier,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            receipt_file=receipt_file,
            created_by=request.user
        )

        messages.success(request, f'Expense "{expense.description}" added successfully.')
        return redirect('admin_portal:finance:expenses')

    # GET request - show form
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    payment_methods = Expense.PAYMENT_METHOD_CHOICES

    context = {
        'categories': categories,
        'payment_methods': payment_methods,
        'today': timezone.now().date(),
    }

    return render(request, 'admin_portal/finance/expense_form.html', context)


@admin_required
def platform_expense_edit(request, pk):
    """
    Edit an existing platform operating expense.
    """
    from apps.expenses.models import Expense, ExpenseCategory

    expense = get_object_or_404(Expense, pk=pk, business_area='general')

    if request.method == 'POST':
        # Get form data
        expense.date = request.POST.get('date')
        category_id = request.POST.get('category')
        new_category_name = request.POST.get('new_category', '').strip()
        expense.description = request.POST.get('description')
        expense.supplier = request.POST.get('supplier')
        expense.amount = request.POST.get('amount')
        expense.payment_method = request.POST.get('payment_method')
        expense.notes = request.POST.get('notes', '')

        # Handle receipt file
        if request.FILES.get('receipt_file'):
            expense.receipt_file = request.FILES.get('receipt_file')
        elif request.POST.get('clear_receipt'):
            expense.receipt_file = None

        # Handle category
        if new_category_name:
            category, created = ExpenseCategory.objects.get_or_create(
                name=new_category_name,
                defaults={'created_by': request.user}
            )
            expense.category = category
        elif category_id:
            expense.category = get_object_or_404(ExpenseCategory, pk=category_id)
        else:
            messages.error(request, 'Please select a category or create a new one.')
            return redirect('admin_portal:finance:expense_edit', pk=pk)

        expense.save()
        messages.success(request, f'Expense "{expense.description}" updated successfully.')
        return redirect('admin_portal:finance:expenses')

    # GET request - show form with existing data
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    payment_methods = Expense.PAYMENT_METHOD_CHOICES

    context = {
        'expense': expense,
        'categories': categories,
        'payment_methods': payment_methods,
        'editing': True,
    }

    return render(request, 'admin_portal/finance/expense_form.html', context)


@admin_required
def platform_expense_delete(request, pk):
    """
    Delete a platform operating expense.
    """
    from apps.expenses.models import Expense

    expense = get_object_or_404(Expense, pk=pk, business_area='general')

    if request.method == 'POST':
        description = expense.description
        expense.delete()
        messages.success(request, f'Expense "{description}" deleted successfully.')
        return redirect('admin_portal:finance:expenses')

    context = {
        'expense': expense,
    }

    return render(request, 'admin_portal/finance/expense_confirm_delete.html', context)
