"""
Admin Portal Finance views.
Platform-level financial reporting for the platform owner.
"""
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum

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
        'net_platform_profit': net_platform_profit,

        # Domain breakdown
        'domain_summary': domain_summary,

        # Monthly trend for charts
        'monthly_trend': summary['monthly_trend'],

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

    context = {
        'days': days,
        'date_label': date_label,
        'expenses': expenses,
        'expenses_by_category': expenses_by_category,
        'total_expenses': total_expenses,
    }

    return render(request, 'admin_portal/finance/expenses.html', context)
