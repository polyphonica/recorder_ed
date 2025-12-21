"""
Unit tests for Teacher Availability Calendar Engine
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, date, time, timedelta
from apps.private_teaching.models import (
    TeacherAvailability,
    AvailabilityException,
    TeacherAvailabilitySettings
)
from apps.private_teaching.availability_engine import (
    calculate_available_slots,
    check_slot_availability,
    _get_available_ranges_for_date,
    _subtract_time_range,
    _merge_time_ranges,
    _generate_slots_in_range,
    _is_slot_available
)
from lessons.models import Lesson
from apps.accounts.models import UserProfile

User = get_user_model()


class AvailabilityEngineTestCase(TestCase):
    """Test cases for availability calculation engine"""

    def setUp(self):
        """Create test teacher with availability"""
        # Create teacher user
        self.teacher = User.objects.create_user(
            username='testteacher',
            email='teacher@test.com',
            password='testpass123'
        )

        # Get or create teacher profile (may auto-create on user creation)
        self.teacher_profile, created = UserProfile.objects.get_or_create(
            user=self.teacher,
            defaults={
                'is_teacher': True,
                'profile_completed': True
            }
        )
        if not created:
            self.teacher_profile.is_teacher = True
            self.teacher_profile.profile_completed = True
            self.teacher_profile.save()

        # Create availability settings
        self.settings = TeacherAvailabilitySettings.objects.create(
            teacher=self.teacher,
            buffer_minutes=0,
            min_booking_notice_hours=24,
            max_booking_days_ahead=90,
            use_availability_calendar=True,
            auto_approve_bookings=True,
            timezone='UTC'
        )

        # Create weekly availability (Monday 9-17, Wednesday 10-18)
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True
        )
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day_of_week=2,  # Wednesday
            start_time=time(10, 0),
            end_time=time(18, 0),
            is_active=True
        )

    def test_time_range_merging(self):
        """Test that overlapping time ranges are merged correctly"""
        ranges = [
            {'start': time(9, 0), 'end': time(12, 0)},
            {'start': time(11, 0), 'end': time(14, 0)},
            {'start': time(16, 0), 'end': time(18, 0)}
        ]
        merged = _merge_time_ranges(ranges)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]['start'], time(9, 0))
        self.assertEqual(merged[0]['end'], time(14, 0))
        self.assertEqual(merged[1]['start'], time(16, 0))
        self.assertEqual(merged[1]['end'], time(18, 0))

    def test_time_range_subtraction(self):
        """Test subtracting time blocks from available ranges"""
        available = [{'start': time(9, 0), 'end': time(17, 0)}]

        # Block 11:00-13:00
        result = _subtract_time_range(available, time(11, 0), time(13, 0))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['start'], time(9, 0))
        self.assertEqual(result[0]['end'], time(11, 0))
        self.assertEqual(result[1]['start'], time(13, 0))
        self.assertEqual(result[1]['end'], time(17, 0))

    def test_slot_generation(self):
        """Test generating time slots at intervals"""
        test_date = date(2025, 6, 15)  # A Sunday
        slots = _generate_slots_in_range(
            test_date,
            time(9, 0),
            time(12, 0),
            duration=60,
            increment=30
        )

        # Should generate slots at 9:00, 9:30, 10:00, 10:30, 11:00
        # (11:30 would end at 12:30, outside range)
        self.assertEqual(len(slots), 5)
        self.assertEqual(slots[0].hour, 9)
        self.assertEqual(slots[0].minute, 0)
        self.assertEqual(slots[1].hour, 9)
        self.assertEqual(slots[1].minute, 30)

    def test_get_available_ranges_for_date(self):
        """Test getting available ranges for a specific date"""
        # Monday
        monday = date(2025, 6, 16)
        ranges = _get_available_ranges_for_date(self.teacher, monday)

        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0]['start'], time(9, 0))
        self.assertEqual(ranges[0]['end'], time(17, 0))

        # Tuesday (no availability)
        tuesday = date(2025, 6, 17)
        ranges = _get_available_ranges_for_date(self.teacher, tuesday)
        self.assertEqual(len(ranges), 0)

        # Wednesday
        wednesday = date(2025, 6, 18)
        ranges = _get_available_ranges_for_date(self.teacher, wednesday)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0]['start'], time(10, 0))
        self.assertEqual(ranges[0]['end'], time(18, 0))

    def test_blocked_exception(self):
        """Test that blocked exceptions remove availability"""
        monday = date(2025, 6, 16)

        # Block 11:00-13:00 on this specific Monday
        AvailabilityException.objects.create(
            teacher=self.teacher,
            exception_type='blocked',
            date=monday,
            start_time=time(11, 0),
            end_time=time(13, 0),
            reason='Lunch meeting'
        )

        ranges = _get_available_ranges_for_date(self.teacher, monday)

        # Should have 2 ranges: 9-11 and 13-17
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0]['start'], time(9, 0))
        self.assertEqual(ranges[0]['end'], time(11, 0))
        self.assertEqual(ranges[1]['start'], time(13, 0))
        self.assertEqual(ranges[1]['end'], time(17, 0))

    def test_available_exception(self):
        """Test that available exceptions add availability"""
        # Tuesday normally has no availability
        tuesday = date(2025, 6, 17)

        # Add special hours 14:00-16:00
        AvailabilityException.objects.create(
            teacher=self.teacher,
            exception_type='available',
            date=tuesday,
            start_time=time(14, 0),
            end_time=time(16, 0),
            reason='Special availability'
        )

        ranges = _get_available_ranges_for_date(self.teacher, tuesday)

        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0]['start'], time(14, 0))
        self.assertEqual(ranges[0]['end'], time(16, 0))

    def test_calculate_available_slots(self):
        """Test full slot calculation for a date range"""
        start_date = date(2025, 6, 16)  # Monday
        end_date = date(2025, 6, 18)    # Wednesday

        slots = calculate_available_slots(
            teacher=self.teacher,
            start_date=start_date,
            end_date=end_date,
            duration=60,
            time_increment=60
        )

        # Should have slots on Monday (9-17, 8 hours) and Wednesday (10-18, 8 hours)
        # With 60-minute slots at 60-minute increments
        self.assertGreater(len(slots), 0)

        # Check slot structure
        first_slot = slots[0]
        self.assertIn('datetime', first_slot)
        self.assertIn('duration', first_slot)
        self.assertIn('available', first_slot)
        self.assertIn('end_datetime', first_slot)

    def test_check_slot_availability_success(self):
        """Test checking if a specific slot is available"""
        from django.utils import timezone

        # Get a Monday 3 days from now at 10:00 AM (respects 24h notice, within availability)
        now = timezone.now()
        days_ahead = 3
        while (now + timedelta(days=days_ahead)).weekday() != 0:  # 0 = Monday
            days_ahead += 1

        slot_datetime = now + timedelta(days=days_ahead)
        slot_datetime = slot_datetime.replace(hour=10, minute=0, second=0, microsecond=0)

        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertTrue(is_available, f"Expected slot to be available, but got reason: {reason}")
        self.assertEqual(reason, '')

    def test_check_slot_availability_outside_hours(self):
        """Test that slots outside availability hours are rejected"""
        from django.utils import timezone

        # Get a Monday 3 days from now at 8:00 AM (before availability starts at 9:00)
        now = timezone.now()
        days_ahead = 3
        while (now + timedelta(days=days_ahead)).weekday() != 0:  # 0 = Monday
            days_ahead += 1

        slot_datetime = now + timedelta(days=days_ahead)
        slot_datetime = slot_datetime.replace(hour=8, minute=0, second=0, microsecond=0)

        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertFalse(is_available)
        # Reason could be about availability or booking notice
        self.assertTrue(len(reason) > 0)

    def test_check_slot_availability_with_existing_lesson(self):
        """Test that slots with existing lessons are rejected"""
        from apps.private_teaching.models import Subject

        # Create student
        student = User.objects.create_user(
            username='teststudent',
            email='student@test.com',
            password='testpass123'
        )

        # Create subject
        subject = Subject.objects.create(
            teacher=self.teacher,
            subject='Piano',
            base_price_60min=50.00
        )

        # Create existing lesson on Monday at 10:00
        existing_lesson = Lesson.objects.create(
            student=student,
            teacher=self.teacher,
            subject=subject,
            lesson_date=date(2025, 6, 16),
            lesson_time=time(10, 0),
            duration_in_minutes=60,
            location='Online',
            approved_status='Accepted',
            payment_status='Not Paid',
            status='Draft'
        )

        # Try to book same time
        slot_datetime = datetime(2025, 6, 16, 10, 0)

        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertFalse(is_available)
        self.assertIn('conflict', reason.lower())

    def test_buffer_time(self):
        """Test that buffer time is respected between lessons"""
        from apps.private_teaching.models import Subject

        # Update settings to require 15-minute buffer
        self.settings.buffer_minutes = 15
        self.settings.save()

        # Create student and subject
        student = User.objects.create_user(
            username='teststudent2',
            email='student2@test.com',
            password='testpass123'
        )
        subject = Subject.objects.create(
            teacher=self.teacher,
            subject='Guitar',
            base_price_60min=45.00
        )

        # Create lesson 10:00-11:00
        Lesson.objects.create(
            student=student,
            teacher=self.teacher,
            subject=subject,
            lesson_date=date(2025, 6, 16),
            lesson_time=time(10, 0),
            duration_in_minutes=60,
            location='Online',
            approved_status='Accepted',
            payment_status='Not Paid',
            status='Draft'
        )

        # Try to book 11:00-12:00 (should fail due to 15-min buffer)
        slot_datetime = datetime(2025, 6, 16, 11, 0)
        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertFalse(is_available)
        self.assertIn('buffer', reason.lower())

        # Try to book 11:15-12:15 (should succeed)
        slot_datetime = datetime(2025, 6, 16, 11, 15)
        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertTrue(is_available)

    def test_minimum_booking_notice(self):
        """Test that minimum booking notice is enforced"""
        from django.utils import timezone

        # Set minimum notice to 24 hours
        self.settings.min_booking_notice_hours = 24
        self.settings.save()

        # Try to book a slot 12 hours from now (should fail)
        slot_datetime = timezone.now() + timedelta(hours=12)

        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertFalse(is_available)
        self.assertIn('advance', reason.lower())

    def test_max_booking_window(self):
        """Test that maximum booking window is enforced"""
        from django.utils import timezone

        # Set max booking window to 90 days
        self.settings.max_booking_days_ahead = 90
        self.settings.save()

        # Try to book 100 days from now (should fail)
        slot_datetime = timezone.now() + timedelta(days=100)

        is_available, reason = check_slot_availability(
            teacher=self.teacher,
            slot_datetime=slot_datetime,
            duration=60
        )

        self.assertFalse(is_available)
        self.assertIn('too far', reason.lower())

    def test_full_day_block(self):
        """Test blocking an entire day"""
        monday = date(2025, 6, 16)

        # Block entire day (no start/end times)
        AvailabilityException.objects.create(
            teacher=self.teacher,
            exception_type='blocked',
            date=monday,
            start_time=None,
            end_time=None,
            reason='Holiday'
        )

        ranges = _get_available_ranges_for_date(self.teacher, monday)

        # Should have no availability
        self.assertEqual(len(ranges), 0)

    def test_inactive_availability_ignored(self):
        """Test that inactive availability slots are ignored"""
        # Make Monday availability inactive
        TeacherAvailability.objects.filter(
            teacher=self.teacher,
            day_of_week=0
        ).update(is_active=False)

        monday = date(2025, 6, 16)
        ranges = _get_available_ranges_for_date(self.teacher, monday)

        # Should have no availability on Monday
        self.assertEqual(len(ranges), 0)

    def test_multiple_slots_same_day(self):
        """Test teacher with split availability on same day"""
        # Add another Monday slot (afternoon only)
        TeacherAvailability.objects.filter(
            teacher=self.teacher,
            day_of_week=0
        ).delete()

        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(12, 0)
        )
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day_of_week=0,
            start_time=time(14, 0),
            end_time=time(17, 0)
        )

        monday = date(2025, 6, 16)
        ranges = _get_available_ranges_for_date(self.teacher, monday)

        # Should have 2 ranges
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0]['start'], time(9, 0))
        self.assertEqual(ranges[0]['end'], time(12, 0))
        self.assertEqual(ranges[1]['start'], time(14, 0))
        self.assertEqual(ranges[1]['end'], time(17, 0))


class AvailabilityModelTestCase(TestCase):
    """Test cases for availability models"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='modeltest',
            email='modeltest@test.com',
            password='testpass123'
        )

    def test_teacher_availability_creation(self):
        """Test creating teacher availability"""
        availability = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day_of_week=1,  # Tuesday
            start_time=time(10, 0),
            end_time=time(16, 0)
        )

        self.assertTrue(availability.is_active)
        self.assertEqual(availability.get_day_of_week_display(), 'Tuesday')

    def test_availability_exception_creation(self):
        """Test creating availability exception"""
        exception = AvailabilityException.objects.create(
            teacher=self.teacher,
            exception_type='blocked',
            date=date(2025, 6, 20),
            start_time=time(9, 0),
            end_time=time(12, 0),
            reason='Conference'
        )

        self.assertTrue(exception.is_active)
        self.assertEqual(exception.exception_type, 'blocked')

    def test_teacher_availability_settings_defaults(self):
        """Test default settings creation"""
        settings = TeacherAvailabilitySettings.objects.create(
            teacher=self.teacher
        )

        self.assertEqual(settings.buffer_minutes, 0)
        self.assertEqual(settings.min_booking_notice_hours, 24)
        self.assertEqual(settings.max_booking_days_ahead, 90)
        self.assertFalse(settings.use_availability_calendar)
        self.assertTrue(settings.auto_approve_bookings)
        self.assertEqual(settings.timezone, 'UTC')
