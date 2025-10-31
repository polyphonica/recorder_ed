"""
Teacher Revenue Dashboard Views
Consolidates revenue from all teaching domains: Workshops, Courses, and Private Teaching
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


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

        # Time periods for filtering
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        this_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # =====================================================================
        # WORKSHOPS REVENUE
        # =====================================================================
        from apps.workshops.models import WorkshopRegistration

        workshop_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=user,
            status='registered',  # Only confirmed registrations
            payment_status='paid'  # Only paid registrations
        ).select_related('session__workshop')

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
        # BUILD CONTEXT
        # =====================================================================
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

            # Time period labels
            'current_month': now.strftime('%B %Y'),
            'current_year': now.year,
        })

        return context
