"""
Centralized finance service for all revenue calculations across domains.
Single source of truth for financial data.
"""
from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import StripePayment


class FinanceService:
    """
    Centralized service for all financial calculations.
    Used by all domains (workshops, courses, private_teaching) to ensure consistency.
    """

    @staticmethod
    def get_teacher_revenue_summary(teacher, start_date=None, end_date=None):
        """
        Get complete revenue summary for a teacher across all domains.

        Args:
            teacher: User object (instructor)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with total_revenue, revenue_by_domain, payment_count, etc.
        """
        query = StripePayment.objects.filter(
            teacher=teacher,
            status='completed'
        )

        if start_date:
            query = query.filter(completed_at__gte=start_date)
        if end_date:
            query = query.filter(completed_at__lte=end_date)

        # Overall totals
        totals = query.aggregate(
            total_revenue=Sum('teacher_share'),
            total_gross=Sum('total_amount'),
            total_commission=Sum('platform_commission'),
            payment_count=Count('id')
        )

        # Revenue by domain
        workshops_revenue = query.filter(domain='workshops').aggregate(
            revenue=Sum('teacher_share'),
            count=Count('id')
        )

        courses_revenue = query.filter(domain='courses').aggregate(
            revenue=Sum('teacher_share'),
            count=Count('id')
        )

        private_revenue = query.filter(domain='private_teaching').aggregate(
            revenue=Sum('teacher_share'),
            count=Count('id')
        )

        return {
            'total_revenue': totals['total_revenue'] or Decimal('0.00'),
            'total_gross': totals['total_gross'] or Decimal('0.00'),
            'total_commission': totals['total_commission'] or Decimal('0.00'),
            'payment_count': totals['payment_count'] or 0,
            'by_domain': {
                'workshops': {
                    'revenue': workshops_revenue['revenue'] or Decimal('0.00'),
                    'count': workshops_revenue['count'] or 0,
                },
                'courses': {
                    'revenue': courses_revenue['revenue'] or Decimal('0.00'),
                    'count': courses_revenue['count'] or 0,
                },
                'private_teaching': {
                    'revenue': private_revenue['revenue'] or Decimal('0.00'),
                    'count': private_revenue['count'] or 0,
                },
            }
        }

    @staticmethod
    def get_domain_revenue(teacher, domain, start_date=None, end_date=None):
        """
        Get revenue for a specific domain.

        Args:
            teacher: User object
            domain: 'workshops', 'courses', or 'private_teaching'
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with revenue totals and transaction list
        """
        query = StripePayment.objects.filter(
            teacher=teacher,
            domain=domain,
            status='completed'
        )

        if start_date:
            query = query.filter(completed_at__gte=start_date)
        if end_date:
            query = query.filter(completed_at__lte=end_date)

        totals = query.aggregate(
            total_revenue=Sum('teacher_share'),
            total_gross=Sum('total_amount'),
            total_commission=Sum('platform_commission'),
            payment_count=Count('id')
        )

        # Get transaction list
        transactions = query.order_by('-completed_at')

        return {
            'domain': domain,
            'total_revenue': totals['total_revenue'] or Decimal('0.00'),
            'total_gross': totals['total_gross'] or Decimal('0.00'),
            'total_commission': totals['total_commission'] or Decimal('0.00'),
            'payment_count': totals['payment_count'] or 0,
            'transactions': transactions,
        }

    @staticmethod
    def get_workshop_revenue_breakdown(teacher, start_date=None, end_date=None):
        """
        Get revenue breakdown by individual workshops.

        Returns:
            list of dicts with workshop info and revenue
        """
        from apps.workshops.models import Workshop, WorkshopRegistration

        query = StripePayment.objects.filter(
            teacher=teacher,
            domain='workshops',
            status='completed'
        )

        if start_date:
            query = query.filter(completed_at__gte=start_date)
        if end_date:
            query = query.filter(completed_at__lte=end_date)

        # Get all workshops for this teacher
        workshops = Workshop.objects.filter(instructor=teacher)

        breakdown = []
        for workshop in workshops:
            # Get registrations for this workshop
            registrations = WorkshopRegistration.objects.filter(
                session__workshop=workshop,
                payment_status='completed'
            )

            if start_date:
                registrations = registrations.filter(paid_at__gte=start_date)
            if end_date:
                registrations = registrations.filter(paid_at__lte=end_date)

            total_revenue = registrations.aggregate(
                revenue=Sum('payment_amount')
            )['revenue'] or Decimal('0.00')

            # Calculate teacher share (after commission)
            from django.conf import settings
            commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100
            teacher_share = total_revenue * (1 - Decimal(str(commission_rate)))

            if total_revenue > 0:  # Only include workshops with revenue
                breakdown.append({
                    'workshop': workshop,
                    'total_revenue': total_revenue,
                    'teacher_share': teacher_share,
                    'registrations_count': registrations.count(),
                })

        # Sort by revenue descending
        breakdown.sort(key=lambda x: x['total_revenue'], reverse=True)

        return breakdown

    @staticmethod
    def get_course_revenue_breakdown(teacher, start_date=None, end_date=None):
        """
        Get revenue breakdown by individual courses.

        Returns:
            list of dicts with course info and revenue
        """
        from apps.courses.models import Course, CourseEnrollment

        # Get all courses for this teacher
        courses = Course.objects.filter(instructor=teacher)

        breakdown = []
        for course in courses:
            # Get enrollments for this course
            enrollments = CourseEnrollment.objects.filter(
                course=course,
                payment_status='completed'
            )

            if start_date:
                enrollments = enrollments.filter(enrolled_at__gte=start_date)
            if end_date:
                enrollments = enrollments.filter(enrolled_at__lte=end_date)

            total_revenue = enrollments.aggregate(
                revenue=Sum('amount_paid')
            )['revenue'] or Decimal('0.00')

            # Calculate teacher share (after commission)
            from django.conf import settings
            commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100
            teacher_share = total_revenue * (1 - Decimal(str(commission_rate)))

            if total_revenue > 0:  # Only include courses with revenue
                breakdown.append({
                    'course': course,
                    'total_revenue': total_revenue,
                    'teacher_share': teacher_share,
                    'enrollments_count': enrollments.count(),
                })

        # Sort by revenue descending
        breakdown.sort(key=lambda x: x['total_revenue'], reverse=True)

        return breakdown

    @staticmethod
    def get_private_teaching_revenue_breakdown(teacher, start_date=None, end_date=None):
        """
        Get revenue breakdown by individual students for private teaching.

        Returns:
            list of dicts with student info and revenue
        """
        from apps.private_teaching.models import Order
        from django.contrib.auth.models import User

        query = Order.objects.filter(
            teacher=teacher,
            payment_status='completed'
        )

        if start_date:
            query = query.filter(paid_at__gte=start_date)
        if end_date:
            query = query.filter(paid_at__lte=end_date)

        # Group by student
        students_data = query.values('student').annotate(
            total_revenue=Sum('total_amount'),
            lessons_count=Count('id')
        ).order_by('-total_revenue')

        breakdown = []
        for student_data in students_data:
            student = User.objects.get(id=student_data['student'])

            # Calculate teacher share (after commission)
            from django.conf import settings
            commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100
            total_revenue = student_data['total_revenue']
            teacher_share = total_revenue * (1 - Decimal(str(commission_rate)))

            breakdown.append({
                'student': student,
                'total_revenue': total_revenue,
                'teacher_share': teacher_share,
                'lessons_count': student_data['lessons_count'],
            })

        return breakdown

    @staticmethod
    def get_recent_transactions(teacher, limit=10):
        """
        Get most recent completed transactions for a teacher across all domains.

        Returns:
            QuerySet of StripePayment objects
        """
        return StripePayment.objects.filter(
            teacher=teacher,
            status='completed'
        ).order_by('-completed_at')[:limit]

    @staticmethod
    def get_revenue_trend(teacher, domain=None, days=30):
        """
        Get daily revenue trend for the last N days.

        Returns:
            list of dicts with date and revenue
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        query = StripePayment.objects.filter(
            teacher=teacher,
            status='completed',
            completed_at__gte=start_date
        )

        if domain:
            query = query.filter(domain=domain)

        # Group by date
        from django.db.models.functions import TruncDate
        daily_revenue = query.annotate(
            date=TruncDate('completed_at')
        ).values('date').annotate(
            revenue=Sum('teacher_share'),
            count=Count('id')
        ).order_by('date')

        return list(daily_revenue)
