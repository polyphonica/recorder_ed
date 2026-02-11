from django.views.generic import TemplateView
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
from pathlib import Path


def robots_txt(request):
    """Serve robots.txt file for search engine crawlers"""
    content = render_to_string('robots.txt')
    return HttpResponse(content, content_type='text/plain')


class DomainSelectorView(TemplateView):
    """Landing page — unified dashboard for teachers, domain selector for everyone else"""
    template_name = 'domain_selector.html'

    def get_template_names(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'profile') and user.profile.is_teacher:
            return ['instructor_overview.html']
        return ['domain_selector.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_authenticated and hasattr(user, 'profile') and user.profile.is_teacher:
            return self._get_teacher_context(context, user)

        # Domain selector for students and anonymous visitors
        context['domains'] = [
            {
                'name': 'Workshops',
                'url': 'workshops:list',
                'description': 'Group music workshops and masterclasses',
                'icon': '🎼',
                'color': 'bg-blue-500',
                'features': ['Group Learning', 'Expert Instructor', 'Online & In-person', 'All Skill Levels']
            },
            {
                'name': 'Private Lessons',
                'url': 'private_teaching:home',
                'description': 'One-on-one personalized music lessons',
                'icon': '🎵',
                'color': 'bg-green-500',
                'features': ['Personal Attention', 'Flexible Scheduling', 'Customized Learning', 'Individual Progress']
            },
            {
                'name': 'Courses',
                'url': 'courses:list',
                'description': 'Structured music education programs',
                'icon': '🎓',
                'color': 'bg-orange-500',
                'features': ['Comprehensive Curriculum', 'Progressive Learning', 'Certification', 'Self-Paced'],
                'coming_soon': False
            },
            {
                'name': 'Digital Products',
                'url': 'digital_products:catalog',
                'description': 'Sheet music, practice materials and educational resources',
                'icon': '📦',
                'color': 'bg-purple-500',
                'features': ['Sheet Music & Scores', 'Practice Materials', 'Instant Download'],
            }
        ]

        return context

    def _get_teacher_context(self, context, user):
        now = timezone.now()
        today = now.date()

        # --- Workshops ---
        from apps.workshops.models import (
            Workshop, WorkshopSession, WorkshopRegistration, WorkshopInterest
        )
        workshops = Workshop.objects.filter(instructor=user)
        upcoming_sessions = WorkshopSession.objects.filter(
            workshop__instructor=user, start_datetime__gte=now,
            is_active=True, is_cancelled=False
        ).count()
        workshop_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=user, status='registered'
        ).count()
        interest_requests = WorkshopInterest.objects.filter(
            workshop__instructor=user, is_active=True
        ).count()

        context['workshops'] = {
            'total': workshops.count(),
            'published': workshops.filter(status='published').count(),
            'upcoming_sessions': upcoming_sessions,
            'registrations': workshop_registrations,
            'interest_requests': interest_requests,
        }

        # --- Private Lessons ---
        from lessons.models import Lesson
        from apps.private_teaching.models import (
            LessonRequest, TeacherStudentApplication,
            LessonCancellationRequest
        )
        today_lessons = Lesson.objects.filter(
            teacher=user, lesson_date=today, is_deleted=False
        ).exclude(status='Cancelled').count()
        pending_requests = LessonRequest.objects.filter(
            lessons__subject__teacher=user, lessons__approved_status='Pending'
        ).distinct().count()
        pending_applications = TeacherStudentApplication.objects.filter(
            teacher=user, status='pending'
        ).count()
        pending_cancellations = LessonCancellationRequest.objects.filter(
            teacher=user, status='pending'
        ).count()

        context['private_lessons'] = {
            'today_lessons': today_lessons,
            'pending_requests': pending_requests,
            'pending_applications': pending_applications,
            'pending_cancellations': pending_cancellations,
        }

        # --- Courses ---
        from apps.courses.models import Course, CourseEnrollment
        courses = Course.objects.filter(instructor=user)
        total_students = CourseEnrollment.objects.filter(
            course__instructor=user, is_active=True
        ).values('student').distinct().count()

        context['courses'] = {
            'total': courses.count(),
            'published': courses.filter(status='published').count(),
            'total_students': total_students,
        }

        # --- Digital Products ---
        from apps.digital_products.models import DigitalProduct, ProductPurchase
        products = DigitalProduct.objects.filter(teacher=user)
        total_sales = sum(p.total_sales for p in products)

        context['digital_products'] = {
            'total': products.count(),
            'published': products.filter(status='published').count(),
            'total_sales': total_sales,
        }

        # --- Revenue (lightweight total) ---
        workshop_rev = WorkshopRegistration.objects.filter(
            session__workshop__instructor=user, status='registered'
        ).filter(
            Q(payment_status='paid') | Q(payment_status='completed')
        ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')

        course_rev = CourseEnrollment.objects.filter(
            course__instructor=user
        ).filter(
            Q(payment_status='completed') | Q(payment_status='not_required')
        ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')

        product_rev = ProductPurchase.objects.filter(
            product__teacher=user, payment_status='completed'
        ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')

        context['revenue'] = {
            'total': workshop_rev + course_rev + product_rev,
        }

        return context


def aural_training_poc(request):
    """Serve the aural training POC HTML file"""
    poc_file = Path(__file__).parent / 'aural_training_progressive_poc.html'
    with open(poc_file, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/html')
