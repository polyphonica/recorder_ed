"""
Teacher Revenue Dashboard Views
Consolidates revenue from all teaching domains: Workshops, Courses, and Private Teaching
"""
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta, datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import csv


class TeacherRevenueDashboardView(LoginRequiredMixin, TemplateView):
    """
    Unified revenue dashboard for teachers across all teaching domains.
    Single source of truth: Database payment records only.
    """
    template_name = 'accounts/teacher_revenue_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Ensure user is a teacher
        if not hasattr(user, 'profile') or not user.profile.is_teacher:
            context['error'] = 'Access denied: Teacher account required'
            return context

        # Get date range from GET parameters (if provided)
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        # Time periods for filtering
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        this_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Parse custom date range if provided
        custom_start = None
        custom_end = None
        date_range_error = None

        if date_from:
            try:
                custom_start = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
            except ValueError:
                date_range_error = 'Invalid start date format'
        if date_to:
            try:
                custom_end = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            except ValueError:
                date_range_error = 'Invalid end date format'

        # Validate date range
        if custom_start and custom_end and custom_start > custom_end:
            date_range_error = 'Start date must be before end date'
            custom_start = None
            custom_end = None

        # =====================================================================
        # WORKSHOPS REVENUE
        # =====================================================================
        from apps.workshops.models import WorkshopRegistration

        workshop_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=user,
            status='registered',  # Only confirmed registrations
            payment_status='paid'  # Only paid registrations
        ).select_related('session__workshop')

        # Apply custom date range if provided
        if custom_start:
            workshop_registrations = workshop_registrations.filter(registration_date__gte=custom_start)
        if custom_end:
            workshop_registrations = workshop_registrations.filter(registration_date__lte=custom_end)

        workshops_total = workshop_registrations.aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0.00')

        workshops_this_month = workshop_registrations.filter(
            registration_date__gte=this_month_start
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

        workshops_this_year = workshop_registrations.filter(
            registration_date__gte=this_year_start
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

        workshops_count = workshop_registrations.count()

        # =====================================================================
        # COURSES REVENUE
        # =====================================================================
        from apps.courses.models import CourseEnrollment

        course_enrollments = CourseEnrollment.objects.filter(
            course__instructor=user,
            payment_status='completed',  # Only completed payments
            is_active=True
        ).select_related('course')

        # Apply custom date range if provided
        if custom_start:
            course_enrollments = course_enrollments.filter(paid_at__gte=custom_start)
        if custom_end:
            course_enrollments = course_enrollments.filter(paid_at__lte=custom_end)

        courses_total = course_enrollments.aggregate(
            total=Sum('payment_amount')
        )['total'] or Decimal('0.00')

        courses_this_month = course_enrollments.filter(
            paid_at__gte=this_month_start
        ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')

        courses_this_year = course_enrollments.filter(
            paid_at__gte=this_year_start
        ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')

        courses_count = course_enrollments.count()

        # =====================================================================
        # PRIVATE TEACHING REVENUE
        # =====================================================================
        from apps.private_teaching.models import Order

        private_orders = Order.objects.filter(
            teacher=user,
            payment_status='completed'  # Only completed payments
        ).prefetch_related('items')

        # Apply custom date range if provided
        if custom_start:
            private_orders = private_orders.filter(created_at__gte=custom_start)
        if custom_end:
            private_orders = private_orders.filter(created_at__lte=custom_end)

        private_total = private_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        private_this_month = private_orders.filter(
            created_at__gte=this_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        private_this_year = private_orders.filter(
            created_at__gte=this_year_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        # Count lessons (not orders)
        private_lessons_count = sum(order.items.count() for order in private_orders)

        # =====================================================================
        # COMBINED TOTALS
        # =====================================================================
        grand_total = workshops_total + courses_total + private_total
        total_this_month = workshops_this_month + courses_this_month + private_this_month
        total_this_year = workshops_this_year + courses_this_year + private_this_year

        # =====================================================================
        # RECENT TRANSACTIONS (Last 10 across all domains)
        # =====================================================================
        recent_transactions = []

        # Add workshop registrations
        for reg in workshop_registrations.order_by('-registration_date')[:10]:
            recent_transactions.append({
                'date': reg.registration_date,
                'type': 'Workshop',
                'description': f"{reg.session.workshop.title} - {reg.session.start_datetime.strftime('%b %d, %Y')}",
                'student': reg.student.get_full_name() or reg.student.username,
                'amount': reg.amount_paid,
            })

        # Add course enrollments
        for enrollment in course_enrollments.filter(paid_at__isnull=False).order_by('-paid_at')[:10]:
            recent_transactions.append({
                'date': enrollment.paid_at,
                'type': 'Course',
                'description': enrollment.course.title,
                'student': enrollment.student.get_full_name() or enrollment.student.username,
                'amount': enrollment.payment_amount,
            })

        # Add private teaching orders
        for order in private_orders.order_by('-created_at')[:10]:
            recent_transactions.append({
                'date': order.created_at,
                'type': 'Private Lesson',
                'description': f"{order.items.count()} lesson(s)",
                'student': order.student.get_full_name() or order.student.username,
                'amount': order.total_amount,
            })

        # Sort all transactions by date (most recent first)
        recent_transactions.sort(key=lambda x: x['date'], reverse=True)
        recent_transactions = recent_transactions[:10]  # Keep only top 10

        # =====================================================================
        # MONTHLY BREAKDOWN (Last 6 months)
        # =====================================================================
        six_months_ago = now - relativedelta(months=6)
        monthly_data = []

        for i in range(6):
            month_start = (now - relativedelta(months=5-i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)

            # Workshops for this month
            workshops_month = workshop_registrations.filter(
                registration_date__gte=month_start,
                registration_date__lte=month_end
            ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

            # Courses for this month
            courses_month = course_enrollments.filter(
                paid_at__gte=month_start,
                paid_at__lte=month_end
            ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')

            # Private for this month
            private_month = private_orders.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

            monthly_data.append({
                'month': month_start.strftime('%b %Y'),
                'workshops': float(workshops_month),
                'courses': float(courses_month),
                'private': float(private_month),
                'total': float(workshops_month + courses_month + private_month),
            })

        # =====================================================================
        # BUILD CONTEXT
        # =====================================================================

        # Build human-readable date range description
        date_range_description = "All Time"
        if custom_start and custom_end:
            date_range_description = f"{custom_start.strftime('%b %d, %Y')} - {custom_end.strftime('%b %d, %Y')}"
        elif custom_start:
            date_range_description = f"Since {custom_start.strftime('%b %d, %Y')}"
        elif custom_end:
            date_range_description = f"Until {custom_end.strftime('%b %d, %Y')}"

        context.update({
            # Overall totals
            'grand_total': grand_total,
            'total_this_month': total_this_month,
            'total_this_year': total_this_year,

            # Workshops
            'workshops_total': workshops_total,
            'workshops_this_month': workshops_this_month,
            'workshops_this_year': workshops_this_year,
            'workshops_count': workshops_count,

            # Courses
            'courses_total': courses_total,
            'courses_this_month': courses_this_month,
            'courses_this_year': courses_this_year,
            'courses_count': courses_count,

            # Private Teaching
            'private_total': private_total,
            'private_this_month': private_this_month,
            'private_this_year': private_this_year,
            'private_lessons_count': private_lessons_count,

            # Recent activity
            'recent_transactions': recent_transactions,

            # Monthly breakdown
            'monthly_data': monthly_data,
            'monthly_data_json': str(monthly_data),  # For JavaScript charting

            # Time period labels
            'current_month': now.strftime('%B %Y'),
            'current_year': now.year,

            # Filter parameters
            'date_from': date_from or '',
            'date_to': date_to or '',
            'has_custom_filter': bool(custom_start or custom_end),
            'date_range_description': date_range_description,
            'date_range_error': date_range_error,
        })

        return context


class TeacherRevenueExportView(LoginRequiredMixin, View):
    """
    Export revenue data as CSV file
    """
    def get(self, request):
        user = request.user

        # Ensure user is a teacher
        if not hasattr(user, 'profile') or not user.profile.is_teacher:
            return HttpResponse('Access denied', status=403)

        # Get date range from GET parameters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        # Parse custom date range if provided
        custom_start = None
        custom_end = None
        if date_from:
            try:
                custom_start = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
            except ValueError:
                pass
        if date_to:
            try:
                custom_end = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            except ValueError:
                pass

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        filename = f'revenue_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Description', 'Student', 'Amount (£)'])

        # =====================================================================
        # FETCH ALL TRANSACTIONS
        # =====================================================================
        from apps.workshops.models import WorkshopRegistration
        from apps.courses.models import CourseEnrollment
        from apps.private_teaching.models import Order

        all_transactions = []

        # Workshop registrations
        workshop_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=user,
            status='registered',
            payment_status='paid'
        ).select_related('session__workshop', 'student')

        if custom_start:
            workshop_registrations = workshop_registrations.filter(registration_date__gte=custom_start)
        if custom_end:
            workshop_registrations = workshop_registrations.filter(registration_date__lte=custom_end)

        for reg in workshop_registrations:
            all_transactions.append({
                'date': reg.registration_date,
                'type': 'Workshop',
                'description': f"{reg.session.workshop.title} - {reg.session.start_datetime.strftime('%b %d, %Y')}",
                'student': reg.student.get_full_name() or reg.student.username,
                'amount': float(reg.amount_paid),
            })

        # Course enrollments
        course_enrollments = CourseEnrollment.objects.filter(
            course__instructor=user,
            payment_status='completed',
            is_active=True,
            paid_at__isnull=False
        ).select_related('course', 'student')

        if custom_start:
            course_enrollments = course_enrollments.filter(paid_at__gte=custom_start)
        if custom_end:
            course_enrollments = course_enrollments.filter(paid_at__lte=custom_end)

        for enrollment in course_enrollments:
            all_transactions.append({
                'date': enrollment.paid_at,
                'type': 'Course',
                'description': enrollment.course.title,
                'student': enrollment.student.get_full_name() or enrollment.student.username,
                'amount': float(enrollment.payment_amount),
            })

        # Private teaching orders
        private_orders = Order.objects.filter(
            teacher=user,
            payment_status='completed'
        ).select_related('student').prefetch_related('items')

        if custom_start:
            private_orders = private_orders.filter(created_at__gte=custom_start)
        if custom_end:
            private_orders = private_orders.filter(created_at__lte=custom_end)

        for order in private_orders:
            all_transactions.append({
                'date': order.created_at,
                'type': 'Private Lesson',
                'description': f"{order.items.count()} lesson(s)",
                'student': order.student.get_full_name() or order.student.username,
                'amount': float(order.total_amount),
            })

        # Sort by date (most recent first)
        all_transactions.sort(key=lambda x: x['date'], reverse=True)

        # Write transactions to CSV
        for transaction in all_transactions:
            writer.writerow([
                transaction['date'].strftime('%Y-%m-%d %H:%M'),
                transaction['type'],
                transaction['description'],
                transaction['student'],
                f"{transaction['amount']:.2f}",
            ])

        return response
