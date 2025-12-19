"""
Pytest configuration and fixtures for E2E tests.

Provides reusable fixtures for authentication, test data, and page objects.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from playwright.sync_api import Page, Browser, BrowserContext
from apps.accounts.models import UserProfile

User = get_user_model()


# ============================================================================
# Django Database Setup
# ============================================================================

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Set up test database with required data before E2E tests.

    Creates test users (teacher and student) that can be used across all tests.
    """
    with django_db_blocker.unblock():
        # Create test teacher
        teacher_user = User.objects.create_user(
            username='test_teacher',
            email='teacher@example.com',
            password='TestPass123!',
            first_name='John',
            last_name='Teacher'
        )

        # Create teacher profile
        teacher_profile, _ = UserProfile.objects.get_or_create(
            user=teacher_user,
            defaults={
                'is_teacher': True,
                'profile_completed': True,
                'phone': '07700900123'
            }
        )

        # Create test student
        student_user = User.objects.create_user(
            username='test_student',
            email='student@example.com',
            password='TestPass123!',
            first_name='Jane',
            last_name='Student'
        )

        # Create student profile
        student_profile, _ = UserProfile.objects.get_or_create(
            user=student_user,
            defaults={
                'is_teacher': False,
                'profile_completed': True,
                'phone': '07700900456'
            }
        )

        # Create another teacher for multi-teacher tests
        teacher2_user = User.objects.create_user(
            username='test_teacher2',
            email='teacher2@example.com',
            password='TestPass123!',
            first_name='Sarah',
            last_name='Instructor'
        )

        teacher2_profile, _ = UserProfile.objects.get_or_create(
            user=teacher2_user,
            defaults={
                'is_teacher': True,
                'profile_completed': True,
                'phone': '07700900789'
            }
        )


# ============================================================================
# Browser & Context Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def context(browser: Browser) -> BrowserContext:
    """Create a new browser context for each test (isolated cookies/storage)."""
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        # Uncomment to emulate mobile
        # **playwright.devices['iPhone 13']
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Page:
    """Create a new page for each test."""
    page = context.new_page()
    yield page
    page.close()


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def login_page(page: Page, live_server):
    """Navigate to login page."""
    from e2e_tests.pages.login_page import LoginPage
    page.goto(f"{live_server.url}/private-teaching/login/")
    return LoginPage(page)


@pytest.fixture
def authenticated_student_page(page: Page, live_server):
    """
    Returns a page authenticated as a student.

    Use this fixture when you need a logged-in student for your test.
    Example:
        def test_student_dashboard(authenticated_student_page):
            page = authenticated_student_page
            page.goto(f"{live_server.url}/private-teaching/student-dashboard/")
            # ... test student-specific functionality
    """
    from e2e_tests.pages.login_page import LoginPage

    page.goto(f"{live_server.url}/private-teaching/login/")
    login_page = LoginPage(page)
    login_page.login('test_student', 'TestPass123!')

    # Wait for redirect after successful login
    page.wait_for_url('**/private-teaching/**', timeout=5000)

    return page


@pytest.fixture
def authenticated_teacher_page(page: Page, live_server):
    """
    Returns a page authenticated as a teacher.

    Use this fixture when you need a logged-in teacher for your test.
    Example:
        def test_teacher_dashboard(authenticated_teacher_page):
            page = authenticated_teacher_page
            page.goto(f"{live_server.url}/private-teaching/teacher-dashboard/")
            # ... test teacher-specific functionality
    """
    from e2e_tests.pages.login_page import LoginPage

    page.goto(f"{live_server.url}/private-teaching/login/")
    login_page = LoginPage(page)
    login_page.login('test_teacher', 'TestPass123!')

    # Wait for redirect after successful login
    page.wait_for_url('**/private-teaching/**', timeout=5000)

    return page


# ============================================================================
# Page Object Fixtures
# ============================================================================

@pytest.fixture
def reschedule_page(authenticated_student_page: Page, live_server):
    """Returns the reschedule page for a student."""
    from e2e_tests.pages.reschedule_page import ReschedulePage
    # Note: Requires a lesson to exist - may need to create one in the test
    return ReschedulePage(authenticated_student_page)


@pytest.fixture
def teacher_cancellation_requests_page(authenticated_teacher_page: Page, live_server):
    """Returns the teacher's cancellation requests page."""
    from e2e_tests.pages.teacher_cancellation_requests_page import TeacherCancellationRequestsPage
    authenticated_teacher_page.goto(f"{live_server.url}/private-teaching/teacher/cancellation-requests/")
    return TeacherCancellationRequestsPage(authenticated_teacher_page)


# ============================================================================
# Helper Functions
# ============================================================================

@pytest.fixture
def create_test_lesson(django_db_blocker):
    """
    Helper fixture to create a test lesson.

    Usage:
        def test_something(create_test_lesson, authenticated_student_page):
            lesson = create_test_lesson(student_username='test_student', teacher_username='test_teacher')
            # ... use the lesson in your test
    """
    def _create_lesson(student_username: str, teacher_username: str, **kwargs):
        with django_db_blocker.unblock():
            from apps.private_teaching.models import Subject, LessonRequest
            from lessons.models import Lesson
            from datetime import datetime, timedelta

            student = User.objects.get(username=student_username)
            teacher = User.objects.get(username=teacher_username)

            # Create or get a subject for the teacher
            subject, _ = Subject.objects.get_or_create(
                teacher=teacher,
                subject='Piano',
                defaults={
                    'base_price_60min': 50.00,
                    'base_price_30min': 30.00,
                    'base_price_90min': 70.00,
                }
            )

            # Create lesson request
            lesson_request = LessonRequest.objects.create(
                student=student,
            )

            # Create lesson
            lesson_date = kwargs.get('lesson_date', datetime.now().date() + timedelta(days=7))
            lesson_time = kwargs.get('lesson_time', datetime.strptime('14:00', '%H:%M').time())

            lesson = Lesson.objects.create(
                lesson_request=lesson_request,
                subject=subject,
                student=student,
                teacher=teacher,
                lesson_date=lesson_date,
                lesson_time=lesson_time,
                duration_in_minutes=kwargs.get('duration', '60'),
                fee=50.00,
                location='Online',
                approved_status='Accepted',
                payment_status='Paid',
                **{k: v for k, v in kwargs.items() if k not in ['lesson_date', 'lesson_time', 'duration']}
            )

            return lesson

    return _create_lesson
