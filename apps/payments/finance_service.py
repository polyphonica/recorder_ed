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
        # Get all enrollments (both active and cancelled) for accurate revenue tracking
        course_enrollments = CourseEnrollment.objects.filter(
            course__instructor=teacher
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

        # Calculate gross from ALL enrollments (including cancelled ones)
        # This ensures refunds are netted against the original revenue
        courses_gross = course_enrollments.aggregate(
            total=Sum('payment_amount')
        )['total'] or Decimal('0.00')

        # Count only active enrollments for enrollment count
        courses_count = course_enrollments.filter(is_active=True).count()

        # Calculate refunds from cancelled course enrollments
        from apps.courses.models import CourseCancellationRequest

        course_refunds = CourseCancellationRequest.objects.filter(
            enrollment__course__instructor=teacher,
            status=CourseCancellationRequest.COMPLETED,
            refund_processed_at__isnull=False
        )

        if start_date:
            course_refunds = course_refunds.filter(refund_processed_at__gte=start_date)
        if end_date:
            course_refunds = course_refunds.filter(refund_processed_at__lte=end_date)

        total_course_refunds = course_refunds.aggregate(
            total=Sum('refund_amount')
        )['total'] or Decimal('0.00')

        # Subtract refunds from gross revenue (can result in zero or negative if all refunded)
        courses_gross = courses_gross - total_course_refunds
        courses_revenue = courses_gross * (1 - Decimal(str(commission_rate)))

        # ===== PRIVATE TEACHING - LESSONS =====
        private_orders = Order.objects.filter(
            items__lesson__teacher=teacher,
            payment_status='completed'
        ).distinct()

        if start_date:
            private_orders = private_orders.filter(created_at__gte=start_date)
        if end_date:
            private_orders = private_orders.filter(created_at__lte=end_date)

        private_lessons_gross = private_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        private_lessons_count = private_orders.count()

        # Calculate refunds from cancelled lessons
        from apps.private_teaching.models import LessonCancellationRequest
        from lessons.models import Lesson

        refund_requests = LessonCancellationRequest.objects.filter(
            teacher=teacher,
            status=LessonCancellationRequest.COMPLETED,
            refund_processed_at__isnull=False
        ).select_related('lesson')

        if start_date:
            refund_requests = refund_requests.filter(refund_processed_at__gte=start_date)
        if end_date:
            refund_requests = refund_requests.filter(refund_processed_at__lte=end_date)

        # Sum up refund amounts (these are already minus platform fee)
        total_refunds = refund_requests.aggregate(
            total=Sum('refund_amount')
        )['total'] or Decimal('0.00')

        # Subtract refunds from gross revenue
        private_lessons_gross = private_lessons_gross - total_refunds

        # ===== PRIVATE TEACHING - EXAM REGISTRATIONS =====
        from apps.private_teaching.models import ExamRegistration

        exam_registrations = ExamRegistration.objects.filter(
            teacher=teacher,
            payment_status='completed'
        )

        if start_date:
            exam_registrations = exam_registrations.filter(paid_at__gte=start_date)
        if end_date:
            exam_registrations = exam_registrations.filter(paid_at__lte=end_date)

        exams_gross = exam_registrations.aggregate(
            total=Sum('fee_amount')
        )['total'] or Decimal('0.00')
        exams_count = exam_registrations.count()

        # Combine private teaching revenue
        private_gross = private_lessons_gross + exams_gross
        private_count = private_lessons_count + exams_count
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
                    'breakdown': {
                        'lessons': {
                            'revenue': private_lessons_gross * (1 - Decimal(str(commission_rate))),
                            'count': private_lessons_count,
                        },
                        'exams': {
                            'revenue': exams_gross * (1 - Decimal(str(commission_rate))),
                            'count': exams_count,
                        },
                    },
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
            from apps.courses.models import CourseEnrollment, CourseCancellationRequest

            # Get ALL enrollments (including cancelled) to properly account for refunds
            query = CourseEnrollment.objects.filter(
                course__instructor=teacher
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
            # Count only active enrollments
            payment_count = query.filter(is_active=True).count()

            # Calculate refunds
            course_refunds = CourseCancellationRequest.objects.filter(
                enrollment__course__instructor=teacher,
                status=CourseCancellationRequest.COMPLETED,
                refund_processed_at__isnull=False
            )

            if start_date:
                course_refunds = course_refunds.filter(refund_processed_at__gte=start_date)
            if end_date:
                course_refunds = course_refunds.filter(refund_processed_at__lte=end_date)

            total_refunds = course_refunds.aggregate(
                total=Sum('refund_amount')
            )['total'] or Decimal('0.00')

            # Net revenue after refunds (can be zero or negative if fully refunded)
            total_gross = total_gross - total_refunds
            total_revenue = total_gross * (1 - Decimal(str(commission_rate)))
            total_commission = total_gross - total_revenue
            transactions = query.select_related('course', 'student').order_by('-paid_at')

        elif domain == 'private_teaching':
            from apps.private_teaching.models import Order, ExamRegistration

            # Lesson orders
            orders_query = Order.objects.filter(
                items__lesson__teacher=teacher,
                payment_status='completed'
            ).distinct()

            if start_date:
                orders_query = orders_query.filter(created_at__gte=start_date)
            if end_date:
                orders_query = orders_query.filter(created_at__lte=end_date)

            lessons_gross = orders_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            lessons_count = orders_query.count()

            # Exam registrations
            exams_query = ExamRegistration.objects.filter(
                teacher=teacher,
                payment_status='completed'
            )

            if start_date:
                exams_query = exams_query.filter(paid_at__gte=start_date)
            if end_date:
                exams_query = exams_query.filter(paid_at__lte=end_date)

            exams_gross = exams_query.aggregate(total=Sum('fee_amount'))['total'] or Decimal('0.00')
            exams_count = exams_query.count()

            # Combine totals
            total_gross = lessons_gross + exams_gross
            payment_count = lessons_count + exams_count
            total_revenue = total_gross * (1 - Decimal(str(commission_rate)))
            total_commission = total_gross - total_revenue

            # Combine transactions (orders and exams)
            # Note: This returns a list instead of queryset since we're combining two models
            transactions = list(orders_query.select_related('student').order_by('-created_at')) + \
                          list(exams_query.select_related('student', 'teacher', 'exam_board').order_by('-paid_at'))

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
        Includes both active and refunded registrations.

        Returns:
            list of dicts with workshop info, revenue, and individual transactions
        """
        from apps.workshops.models import Workshop, WorkshopRegistration
        from django.conf import settings

        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100

        # Get all workshops for this teacher
        workshops = Workshop.objects.filter(instructor=teacher)

        breakdown = []
        for workshop in workshops:
            # Get all registrations for this workshop (including cancelled with refunds)
            registrations = WorkshopRegistration.objects.filter(
                session__workshop=workshop,
            ).filter(
                Q(payment_status='completed', status='registered') |  # Active paid registrations
                Q(payment_status='completed', status='cancelled')     # Cancelled/refunded registrations
            )

            if start_date:
                registrations = registrations.filter(paid_at__gte=start_date)
            if end_date:
                registrations = registrations.filter(paid_at__lte=end_date)

            # Calculate revenue only from active (non-cancelled) registrations
            active_registrations = registrations.filter(status='registered')
            total_revenue = active_registrations.aggregate(
                revenue=Sum('payment_amount')
            )['revenue'] or Decimal('0.00')

            # Get refunded registrations
            refunded_registrations = registrations.filter(status='cancelled')
            refunded_amount = refunded_registrations.aggregate(
                revenue=Sum('payment_amount')
            )['revenue'] or Decimal('0.00')

            # Calculate teacher share (after commission) - only on active revenue
            teacher_share = total_revenue * (1 - Decimal(str(commission_rate)))

            # Include workshops that have any transactions (active or refunded)
            if total_revenue > 0 or refunded_amount > 0:
                breakdown.append({
                    'workshop': workshop,
                    'total_revenue': total_revenue,
                    'teacher_share': teacher_share,
                    'registrations_count': active_registrations.count(),
                    'refunded_count': refunded_registrations.count(),
                    'refunded_amount': refunded_amount,
                    'transactions': registrations.select_related('student', 'session').order_by('-paid_at'),
                })

        # Sort by total revenue (active + refunded) descending to show busiest workshops first
        breakdown.sort(key=lambda x: x['total_revenue'] + x['refunded_amount'], reverse=True)

        return breakdown

    @staticmethod
    def get_course_revenue_breakdown(teacher, start_date=None, end_date=None):
        """
        Get revenue breakdown by individual courses.
        Includes both active and refunded enrollments.

        Returns:
            list of dicts with course info, revenue, and refund details
        """
        from apps.courses.models import Course, CourseEnrollment, CourseCancellationRequest
        from django.conf import settings

        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100

        # Get all courses for this teacher
        courses = Course.objects.filter(instructor=teacher)

        breakdown = []
        for course in courses:
            # Get all enrollments for this course (including cancelled with refunds)
            enrollments = CourseEnrollment.objects.filter(
                course=course
            ).filter(
                Q(payment_status='completed', is_active=True) |  # Active paid enrollments
                Q(payment_status='completed', is_active=False)   # Cancelled/refunded enrollments
            )

            if start_date:
                enrollments = enrollments.filter(
                    Q(paid_at__gte=start_date) | Q(paid_at__isnull=True, enrolled_at__gte=start_date)
                )
            if end_date:
                enrollments = enrollments.filter(
                    Q(paid_at__lte=end_date) | Q(paid_at__isnull=True, enrolled_at__lte=end_date)
                )

            # Calculate revenue only from active (non-cancelled) enrollments
            active_enrollments = enrollments.filter(is_active=True)
            total_revenue = active_enrollments.aggregate(
                revenue=Sum('payment_amount')
            )['revenue'] or Decimal('0.00')

            # Get refunded enrollments
            course_refunds = CourseCancellationRequest.objects.filter(
                enrollment__course=course,
                status=CourseCancellationRequest.COMPLETED,
                refund_processed_at__isnull=False
            )

            if start_date:
                course_refunds = course_refunds.filter(refund_processed_at__gte=start_date)
            if end_date:
                course_refunds = course_refunds.filter(refund_processed_at__lte=end_date)

            refunded_amount = course_refunds.aggregate(
                revenue=Sum('refund_amount')
            )['revenue'] or Decimal('0.00')

            # Calculate teacher share (after commission) - only on active revenue
            teacher_share = total_revenue * (1 - Decimal(str(commission_rate)))

            # Include courses that have any transactions (active or refunded)
            if total_revenue > 0 or refunded_amount > 0:
                breakdown.append({
                    'course': course,
                    'total_revenue': total_revenue,
                    'teacher_share': teacher_share,
                    'enrollments_count': active_enrollments.count(),
                    'refunded_count': course_refunds.count(),
                    'refunded_amount': refunded_amount,
                    'transactions': enrollments.select_related('student').order_by('-paid_at'),
                })

        # Sort by total revenue (active + refunded) descending to show busiest courses first
        breakdown.sort(key=lambda x: x['total_revenue'] + x['refunded_amount'], reverse=True)

        return breakdown

    @staticmethod
    def get_private_teaching_revenue_breakdown(teacher, start_date=None, end_date=None):
        """
        Get revenue breakdown by student and subject for private teaching.
        Returns one row per subject per student, showing lessons and exam revenue separately.
        Includes refunded lessons as negative amounts.

        Returns:
            list of dicts with student, subject, and revenue info
        """
        from apps.private_teaching.models import Order, OrderItem, ExamRegistration, Subject, LessonCancellationRequest
        from django.contrib.auth.models import User
        from lessons.models import Lesson
        from django.conf import settings

        commission_rate = settings.PLATFORM_COMMISSION_PERCENTAGE / 100
        breakdown_dict = {}  # Key: (student_id, subject_id)

        # Get paid lessons and group by student and subject
        lessons_query = Lesson.objects.filter(
            teacher=teacher,
            payment_status='Paid',
            is_deleted=False
        ).select_related('student', 'subject', 'order_item__order')

        if start_date:
            lessons_query = lessons_query.filter(lesson_date__gte=start_date)
        if end_date:
            lessons_query = lessons_query.filter(lesson_date__lte=end_date)

        for lesson in lessons_query:
            key = (lesson.student.id, lesson.subject.id)
            if key not in breakdown_dict:
                breakdown_dict[key] = {
                    'student': lesson.student,
                    'subject': lesson.subject,
                    'lessons_count': 0,
                    'lessons_revenue': Decimal('0.00'),
                    'refunded_count': 0,
                    'refunded_amount': Decimal('0.00'),
                    'exams_count': 0,
                    'exams_revenue': Decimal('0.00'),
                }

            breakdown_dict[key]['lessons_count'] += 1
            # Get the price from the order item
            if hasattr(lesson, 'order_item') and lesson.order_item:
                breakdown_dict[key]['lessons_revenue'] += lesson.order_item.price_paid

        # Get refunded lessons and subtract from revenue
        refund_requests = LessonCancellationRequest.objects.filter(
            teacher=teacher,
            status=LessonCancellationRequest.COMPLETED,
            refund_processed_at__isnull=False
        ).select_related('lesson__subject', 'student')

        if start_date:
            refund_requests = refund_requests.filter(refund_processed_at__gte=start_date)
        if end_date:
            refund_requests = refund_requests.filter(refund_processed_at__lte=end_date)

        for refund in refund_requests:
            lesson = refund.lesson
            key = (refund.student.id, lesson.subject.id)

            if key not in breakdown_dict:
                breakdown_dict[key] = {
                    'student': refund.student,
                    'subject': lesson.subject,
                    'lessons_count': 0,
                    'lessons_revenue': Decimal('0.00'),
                    'refunded_count': 0,
                    'refunded_amount': Decimal('0.00'),
                    'exams_count': 0,
                    'exams_revenue': Decimal('0.00'),
                }

            # Track refunded lessons separately
            breakdown_dict[key]['refunded_count'] += 1
            # Original lesson fee (before platform fee deduction)
            breakdown_dict[key]['refunded_amount'] += lesson.fee if lesson.fee else Decimal('0.00')

        # Get paid exam registrations and group by student and subject
        exams_query = ExamRegistration.objects.filter(
            teacher=teacher,
            payment_status='completed'
        ).select_related('student', 'subject')

        if start_date:
            exams_query = exams_query.filter(paid_at__gte=start_date)
        if end_date:
            exams_query = exams_query.filter(paid_at__lte=end_date)

        for exam in exams_query:
            key = (exam.student.id, exam.subject.id)
            if key not in breakdown_dict:
                breakdown_dict[key] = {
                    'student': exam.student,
                    'subject': exam.subject,
                    'lessons_count': 0,
                    'lessons_revenue': Decimal('0.00'),
                    'exams_count': 0,
                    'exams_revenue': Decimal('0.00'),
                }

            breakdown_dict[key]['exams_count'] += 1
            breakdown_dict[key]['exams_revenue'] += exam.fee_amount

        # Build final breakdown list
        breakdown = []
        for data in breakdown_dict.values():
            # Net revenue = lessons + exams - refunds
            net_lessons_revenue = data['lessons_revenue'] - data['refunded_amount']
            total_revenue = net_lessons_revenue + data['exams_revenue']
            teacher_share = total_revenue * (1 - Decimal(str(commission_rate)))

            breakdown.append({
                'student': data['student'],
                'subject': data['subject'],
                'lessons_count': data['lessons_count'],
                'lessons_revenue': data['lessons_revenue'],
                'refunded_count': data['refunded_count'],
                'refunded_amount': data['refunded_amount'],
                'net_lessons_revenue': net_lessons_revenue,
                'exams_count': data['exams_count'],
                'exams_revenue': data['exams_revenue'],
                'total_revenue': total_revenue,
                'teacher_share': teacher_share,
            })

        # Sort by student name, then subject name
        breakdown.sort(key=lambda x: (x['student'].get_full_name() or x['student'].username, x['subject'].subject))

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

        # Get workshop registrations (both active and refunded)
        workshop_regs = WorkshopRegistration.objects.filter(
            session__workshop__instructor=teacher,
        ).filter(
            Q(payment_status='paid', status='registered') |
            Q(payment_status='completed', status='registered') |
            Q(payment_status='not_required', status='registered') |
            Q(payment_status='completed', status='cancelled')  # Include refunded registrations
        ).select_related('session__workshop', 'student').order_by('-paid_at')[:limit * 2]  # Get more to ensure we have enough after filtering

        for reg in workshop_regs:
            amount = reg.payment_amount
            is_refunded = reg.status == 'cancelled'

            if is_refunded:
                # Refunded transaction shows as negative
                teacher_share = Decimal('0.00')
                display_amount = -amount
            else:
                # Active transaction
                teacher_share = amount * (1 - Decimal(str(commission_rate)))
                display_amount = amount

            transactions.append({
                'date': reg.paid_at or reg.registration_date,
                'domain': 'workshops',
                'domain_display': 'Workshop (Refunded)' if is_refunded else 'Workshop',
                'description': f"{reg.session.workshop.title} - {reg.session.start_datetime.strftime('%b %d, %Y')}",
                'student': reg.student,
                'amount': display_amount,
                'teacher_share': teacher_share,
                'is_refunded': is_refunded,
            })

        # Get course enrollments (both active and refunded)
        course_enrollments = CourseEnrollment.objects.filter(
            course__instructor=teacher
        ).filter(
            Q(payment_status='completed') | Q(payment_status='not_required')
        ).select_related('course', 'student').order_by('-paid_at')[:limit * 2]  # Get more to ensure we have enough after filtering

        for enrollment in course_enrollments:
            amount = enrollment.payment_amount
            is_refunded = not enrollment.is_active

            if is_refunded:
                # Refunded transaction shows as negative
                teacher_share = Decimal('0.00')
                display_amount = -amount
            else:
                # Active transaction
                teacher_share = amount * (1 - Decimal(str(commission_rate)))
                display_amount = amount

            transactions.append({
                'date': enrollment.paid_at or enrollment.enrolled_at,
                'domain': 'courses',
                'domain_display': 'Course (Refunded)' if is_refunded else 'Course',
                'description': enrollment.course.title,
                'student': enrollment.student,
                'amount': display_amount,
                'teacher_share': teacher_share,
                'is_refunded': is_refunded,
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
                'is_refunded': False,
            })

        # Get refunded private lessons
        from apps.private_teaching.models import LessonCancellationRequest

        refund_requests = LessonCancellationRequest.objects.filter(
            teacher=teacher,
            status=LessonCancellationRequest.COMPLETED,
            refund_processed_at__isnull=False
        ).select_related('lesson__subject', 'student').order_by('-refund_processed_at')[:limit]

        for refund in refund_requests:
            # Refund shows as negative amount
            # The refund_amount is already net of platform fee, but we need to show the original lesson fee
            lesson = refund.lesson
            original_amount = lesson.fee if lesson.fee else Decimal('0.00')

            # Teacher loses their share of this lesson
            teacher_lost = refund.refund_amount  # This is what student gets back (net of platform fee)

            transactions.append({
                'date': refund.refund_processed_at,
                'domain': 'private_teaching',
                'domain_display': 'Private Lesson (Refunded)',
                'description': f"{lesson.subject.subject} - {lesson.lesson_date.strftime('%b %d, %Y')}",
                'student': refund.student,
                'amount': -original_amount,  # Show as negative
                'teacher_share': -teacher_lost,  # Teacher loses this amount
                'is_refunded': True,
            })

        # Get exam registrations
        from apps.private_teaching.models import ExamRegistration

        exam_registrations = ExamRegistration.objects.filter(
            teacher=teacher,
            payment_status='completed'
        ).select_related('student', 'exam_board', 'subject', 'child_profile').order_by('-paid_at')[:limit]

        for exam in exam_registrations:
            amount = exam.fee_amount
            teacher_share = amount * (1 - Decimal(str(commission_rate)))

            transactions.append({
                'date': exam.paid_at,
                'domain': 'private_teaching',
                'domain_display': 'Exam Registration',
                'description': f"{exam.display_name} - {exam.subject.subject}",
                'student': exam.student,
                'amount': amount,
                'teacher_share': teacher_share,
            })

        # Sort all transactions by date (most recent first) and limit
        transactions.sort(key=lambda x: x['date'] if x['date'] else timezone.now() - timedelta(days=365), reverse=True)
        return transactions[:limit]

    @staticmethod
    def get_revenue_trend(teacher, domain=None, days=30):
        """
        Get daily revenue trend for the last N days.
        Excludes refunded payments from revenue calculations.

        Returns:
            list of dicts with date and revenue
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Only include completed payments, exclude refunded
        query = StripePayment.objects.filter(
            teacher=teacher,
            status='completed',  # Exclude 'refunded', 'pending', 'failed'
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
