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
        Queries actual tables (not StripePayment) for accurate totals.

        Args:
            teacher: User object (instructor)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with total_revenue, revenue_by_domain, payment_count, etc.
        """
        from apps.workshops.models import WorkshopRegistration
        from apps.courses.models import CourseEnrollment
        from apps.private_teaching.models import Order
        from django.conf import settings

        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100

        # ===== WORKSHOPS =====
        workshop_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=teacher,
            status='registered',
        ).filter(
            Q(payment_status='paid') | Q(payment_status='completed') | Q(payment_status='not_required')
        )

        if start_date:
            workshop_registrations = workshop_registrations.filter(paid_at__gte=start_date)
        if end_date:
            workshop_registrations = workshop_registrations.filter(paid_at__lte=end_date)

        workshops_gross = workshop_registrations.aggregate(
            total=Sum('payment_amount')
        )['total'] or Decimal('0.00')
        workshops_count = workshop_registrations.count()
        workshops_revenue = workshops_gross * (1 - Decimal(str(commission_rate)))

        # ===== COURSES =====
        course_enrollments = CourseEnrollment.objects.filter(
            course__instructor=teacher,
            is_active=True
        ).filter(
            Q(payment_status='completed') | Q(payment_status='not_required')
        )

        if start_date:
            # Use paid_at if available, fallback to enrolled_at for older records
            course_enrollments = course_enrollments.filter(
                Q(paid_at__gte=start_date) | Q(paid_at__isnull=True, enrolled_at__gte=start_date)
            )
        if end_date:
            course_enrollments = course_enrollments.filter(
                Q(paid_at__lte=end_date) | Q(paid_at__isnull=True, enrolled_at__lte=end_date)
            )

        courses_gross = course_enrollments.aggregate(
            total=Sum('payment_amount')
        )['total'] or Decimal('0.00')
        courses_count = course_enrollments.count()
        courses_revenue = courses_gross * (1 - Decimal(str(commission_rate)))

        # ===== PRIVATE TEACHING =====
        private_orders = Order.objects.filter(
            items__lesson__teacher=teacher,
            payment_status='completed'
        ).distinct()

        if start_date:
            private_orders = private_orders.filter(created_at__gte=start_date)
        if end_date:
            private_orders = private_orders.filter(created_at__lte=end_date)

        private_gross = private_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        private_count = private_orders.count()
        private_revenue = private_gross * (1 - Decimal(str(commission_rate)))

        # ===== TOTALS =====
        total_gross = workshops_gross + courses_gross + private_gross
        total_revenue = workshops_revenue + courses_revenue + private_revenue
        total_commission = total_gross - total_revenue
        total_count = workshops_count + courses_count + private_count

        return {
            'total_revenue': total_revenue,
            'total_gross': total_gross,
            'total_commission': total_commission,
            'payment_count': total_count,
            'by_domain': {
                'workshops': {
                    'revenue': workshops_revenue,
                    'count': workshops_count,
                },
                'courses': {
                    'revenue': courses_revenue,
                    'count': courses_count,
                },
                'private_teaching': {
                    'revenue': private_revenue,
                    'count': private_count,
                },
            }
        }

    @staticmethod
    def get_domain_revenue(teacher, domain, start_date=None, end_date=None):
        """
        Get revenue for a specific domain.
        Queries actual tables (not StripePayment) for accurate totals.

        Args:
            teacher: User object
            domain: 'workshops', 'courses', or 'private_teaching'
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with revenue totals and transaction list
        """
        from django.conf import settings
        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100

        if domain == 'workshops':
            from apps.workshops.models import WorkshopRegistration

            query = WorkshopRegistration.objects.filter(
                session__workshop__instructor=teacher,
                status='registered',
            ).filter(
                Q(payment_status='paid') | Q(payment_status='completed') | Q(payment_status='not_required')
            )

            if start_date:
                query = query.filter(paid_at__gte=start_date)
            if end_date:
                query = query.filter(paid_at__lte=end_date)

            total_gross = query.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')
            payment_count = query.count()
            total_revenue = total_gross * (1 - Decimal(str(commission_rate)))
            total_commission = total_gross - total_revenue
            transactions = query.select_related('session__workshop', 'student').order_by('-paid_at')

        elif domain == 'courses':
            from apps.courses.models import CourseEnrollment

            query = CourseEnrollment.objects.filter(
                course__instructor=teacher,
                is_active=True
            ).filter(
                Q(payment_status='completed') | Q(payment_status='not_required')
            )

            if start_date:
                query = query.filter(
                    Q(paid_at__gte=start_date) | Q(paid_at__isnull=True, enrolled_at__gte=start_date)
                )
            if end_date:
                query = query.filter(
                    Q(paid_at__lte=end_date) | Q(paid_at__isnull=True, enrolled_at__lte=end_date)
                )

            total_gross = query.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')
            payment_count = query.count()
            total_revenue = total_gross * (1 - Decimal(str(commission_rate)))
            total_commission = total_gross - total_revenue
            transactions = query.select_related('course', 'student').order_by('-paid_at')

        elif domain == 'private_teaching':
            from apps.private_teaching.models import Order

            query = Order.objects.filter(
                items__lesson__teacher=teacher,
                payment_status='completed'
            ).distinct()

            if start_date:
                query = query.filter(created_at__gte=start_date)
            if end_date:
                query = query.filter(created_at__lte=end_date)

            total_gross = query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            payment_count = query.count()
            total_revenue = total_gross * (1 - Decimal(str(commission_rate)))
            total_commission = total_gross - total_revenue
            transactions = query.select_related('student').order_by('-created_at')

        else:
            return {
                'domain': domain,
                'total_revenue': Decimal('0.00'),
                'total_gross': Decimal('0.00'),
                'total_commission': Decimal('0.00'),
                'payment_count': 0,
                'transactions': [],
            }

        return {
            'domain': domain,
            'total_revenue': total_revenue,
            'total_gross': total_gross,
            'total_commission': total_commission,
            'payment_count': payment_count,
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
                course=course
            ).filter(
                Q(payment_status='completed') | Q(payment_status='not_required')
            )

            if start_date:
                enrollments = enrollments.filter(enrolled_at__gte=start_date)
            if end_date:
                enrollments = enrollments.filter(enrolled_at__lte=end_date)

            total_revenue = enrollments.aggregate(
                revenue=Sum('payment_amount')
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
        from apps.private_teaching.models import Order, OrderItem
        from django.contrib.auth.models import User
        from lessons.models import Lesson

        query = Order.objects.filter(
            items__lesson__teacher=teacher,
            payment_status='completed'
        ).distinct()

        if start_date:
            query = query.filter(created_at__gte=start_date)
        if end_date:
            query = query.filter(created_at__lte=end_date)

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

            # Get all lessons for this student from this teacher
            lessons_query = Lesson.objects.filter(
                student=student,
                teacher=teacher,
                payment_status='Paid',
                is_deleted=False
            ).select_related('subject')

            if start_date:
                lessons_query = lessons_query.filter(lesson_date__gte=start_date)
            if end_date:
                lessons_query = lessons_query.filter(lesson_date__lte=end_date)

            lessons_with_subjects = lessons_query.values(
                'subject__subject'
            ).annotate(
                count=Count('id')
            ).order_by('-count')

            # Format subjects as "Subject Name (x count)"
            subjects_list = [
                f"{item['subject__subject']} ({item['count']})" if item['count'] > 1 else item['subject__subject']
                for item in lessons_with_subjects
            ]

            breakdown.append({
                'student': student,
                'total_revenue': total_revenue,
                'teacher_share': teacher_share,
                'lessons_count': student_data['lessons_count'],
                'subjects': subjects_list,
            })

        return breakdown

    @staticmethod
    def get_private_teaching_subject_breakdown(teacher, start_date=None, end_date=None):
        """
        Get revenue breakdown by subject for private teaching.

        Returns:
            list of dicts with subject info and revenue
        """
        from apps.private_teaching.models import Subject
        from lessons.models import Lesson
        from django.conf import settings

        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100

        # Get all paid lessons for this teacher
        lessons_query = Lesson.objects.filter(
            teacher=teacher,
            payment_status='Paid',
            is_deleted=False
        ).select_related('subject', 'student')

        if start_date:
            lessons_query = lessons_query.filter(lesson_date__gte=start_date)
        if end_date:
            lessons_query = lessons_query.filter(lesson_date__lte=end_date)

        # Group by subject and aggregate
        from django.db.models import Count
        subject_data = lessons_query.values(
            'subject__id',
            'subject__subject'
        ).annotate(
            total_lessons=Count('id'),
            total_students=Count('student', distinct=True),
            total_revenue=Sum('fee')
        ).order_by('-total_revenue')

        breakdown = []
        total_all_revenue = Decimal('0.00')

        # First pass to calculate total revenue for percentages
        for item in subject_data:
            revenue = item['total_revenue']
            total_all_revenue += Decimal(str(revenue)) if revenue else Decimal('0.00')

        # Second pass to build breakdown with percentages
        for item in subject_data:
            revenue = item['total_revenue']
            subject_revenue = Decimal(str(revenue)) if revenue else Decimal('0.00')
            teacher_share = subject_revenue * (1 - Decimal(str(commission_rate)))

            # Calculate percentage of total revenue
            if total_all_revenue > 0:
                percentage = (subject_revenue / total_all_revenue) * 100
            else:
                percentage = 0

            # Calculate average per lesson
            if item['total_lessons'] > 0:
                avg_per_lesson = subject_revenue / Decimal(str(item['total_lessons']))
            else:
                avg_per_lesson = Decimal('0.00')

            breakdown.append({
                'subject_name': item['subject__subject'],
                'subject_id': item['subject__id'],
                'total_students': item['total_students'],
                'total_lessons': item['total_lessons'],
                'total_revenue': subject_revenue,
                'teacher_share': teacher_share,
                'percentage': percentage,
                'avg_per_lesson': avg_per_lesson,
            })

        return breakdown

    @staticmethod
    def get_recent_transactions(teacher, limit=10):
        """
        Get most recent completed transactions for a teacher across all domains.
        Queries actual source tables for accurate transaction list.

        Returns:
            list of dicts with transaction details
        """
        from apps.workshops.models import WorkshopRegistration
        from apps.courses.models import CourseEnrollment
        from apps.private_teaching.models import Order
        from django.conf import settings

        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100
        transactions = []

        # Get workshop registrations
        workshop_regs = WorkshopRegistration.objects.filter(
            session__workshop__instructor=teacher,
            status='registered',
        ).filter(
            Q(payment_status='paid') | Q(payment_status='completed') | Q(payment_status='not_required')
        ).select_related('session__workshop', 'student').order_by('-paid_at')[:limit]

        for reg in workshop_regs:
            amount = reg.payment_amount
            teacher_share = amount * (1 - Decimal(str(commission_rate)))
            transactions.append({
                'date': reg.paid_at or reg.registration_date,
                'domain': 'workshops',
                'domain_display': 'Workshop',
                'description': f"{reg.session.workshop.title} - {reg.session.start_datetime.strftime('%b %d, %Y')}",
                'student': reg.student,
                'amount': amount,
                'teacher_share': teacher_share,
            })

        # Get course enrollments
        course_enrollments = CourseEnrollment.objects.filter(
            course__instructor=teacher,
            is_active=True
        ).filter(
            Q(payment_status='completed') | Q(payment_status='not_required')
        ).select_related('course', 'student').order_by('-paid_at')[:limit]

        for enrollment in course_enrollments:
            amount = enrollment.payment_amount
            teacher_share = amount * (1 - Decimal(str(commission_rate)))
            transactions.append({
                'date': enrollment.paid_at or enrollment.enrolled_at,
                'domain': 'courses',
                'domain_display': 'Course',
                'description': enrollment.course.title,
                'student': enrollment.student,
                'amount': amount,
                'teacher_share': teacher_share,
            })

        # Get private teaching orders
        private_orders = Order.objects.filter(
            items__lesson__teacher=teacher,
            payment_status='completed'
        ).distinct().select_related('student').prefetch_related('items__lesson').order_by('-created_at')[:limit]

        for order in private_orders:
            amount = order.total_amount
            teacher_share = amount * (1 - Decimal(str(commission_rate)))

            # Get lesson subjects from order items
            lessons = [item.lesson for item in order.items.all() if item.lesson.teacher == teacher]
            if lessons:
                if len(lessons) == 1:
                    description = lessons[0].subject
                else:
                    description = f"{lessons[0].subject} + {len(lessons)-1} more"
            else:
                description = f"Order #{order.order_number}"

            transactions.append({
                'date': order.created_at,
                'domain': 'private_teaching',
                'domain_display': 'Private Lesson',
                'description': description,
                'student': order.student,
                'amount': amount,
                'teacher_share': teacher_share,
            })

        # Sort all transactions by date (most recent first) and limit
        transactions.sort(key=lambda x: x['date'], reverse=True)
        return transactions[:limit]

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
