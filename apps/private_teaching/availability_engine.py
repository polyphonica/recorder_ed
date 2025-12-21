"""
Availability Calculation Engine

This module contains the core logic for calculating teacher availability.
It combines:
1. Weekly recurring availability templates
2. One-time exceptions (blocks and special hours)
3. Existing booked lessons
4. Buffer time requirements
5. Advance booking rules
"""

from datetime import datetime, timedelta, date, time
from typing import List, Dict, Tuple
from django.utils import timezone
from .models import TeacherAvailability, AvailabilityException
from lessons.models import Lesson


def calculate_available_slots(
    teacher,
    start_date: date,
    end_date: date,
    duration: int = 60,
    time_increment: int = 30
) -> List[Dict]:
    """
    Calculate all available time slots for a teacher within a date range.

    Args:
        teacher: User object (teacher)
        start_date: Start date for availability search
        end_date: End date for availability search
        duration: Lesson duration in minutes (e.g., 60)
        time_increment: Slot increment in minutes (e.g., 30 means slots at 9:00, 9:30, 10:00...)

    Returns:
        List of available slots:
        [
            {
                'datetime': datetime(2025, 6, 15, 9, 0),
                'duration': 60,
                'available': True,
                'end_datetime': datetime(2025, 6, 15, 10, 0)
            },
            ...
        ]

    Algorithm:
        For each date in range:
            1. Get base availability from weekly template
            2. Apply exceptions (blocks/special hours)
            3. Exclude booked lessons
            4. Apply buffer time
            5. Apply min/max booking notice rules
            6. Generate slots at time_increment intervals
    """
    # Check if teacher has availability settings
    if not hasattr(teacher, 'availability_settings'):
        return []  # Teacher hasn't set up availability yet

    settings = teacher.availability_settings

    # Check if teacher is using availability calendar
    if not settings.use_availability_calendar:
        return []  # Fall back to old request system

    available_slots = []

    # Iterate through each date in the range
    current_date = start_date
    while current_date <= end_date:
        # Get available time ranges for this date
        time_ranges = _get_available_ranges_for_date(teacher, current_date)

        # Generate slots within each time range
        for time_range in time_ranges:
            slots = _generate_slots_in_range(
                date_obj=current_date,
                start_time=time_range['start'],
                end_time=time_range['end'],
                duration=duration,
                increment=time_increment
            )

            # Filter slots based on booking rules and existing lessons
            for slot in slots:
                if _is_slot_available(teacher, slot, duration, settings):
                    available_slots.append({
                        'datetime': slot.isoformat(),
                        'duration': duration,
                        'available': True,
                        'end_datetime': (slot + timedelta(minutes=duration)).isoformat()
                    })

        current_date += timedelta(days=1)

    return available_slots


def _get_available_ranges_for_date(teacher, target_date: date) -> List[Dict]:
    """
    Get list of available time ranges for a specific date.
    Combines weekly template + exceptions.

    Returns:
        [
            {'start': time(9, 0), 'end': time(12, 0)},
            {'start': time(14, 0), 'end': time(17, 0)},
        ]
    """
    day_of_week = target_date.weekday()  # 0 = Monday, 6 = Sunday

    # Step 1: Get base availability from weekly template
    base_availability = TeacherAvailability.objects.filter(
        teacher=teacher,
        day_of_week=day_of_week,
        is_active=True
    ).order_by('start_time')

    base_ranges = [
        {'start': slot.start_time, 'end': slot.end_time}
        for slot in base_availability
    ]

    # Step 2: Check for exceptions on this date
    exceptions = AvailabilityException.objects.filter(
        teacher=teacher,
        date=target_date,
        is_active=True
    )

    # If there's an all-day block exception, return empty
    all_day_block = exceptions.filter(
        exception_type='block',
        start_time__isnull=True,
        end_time__isnull=True
    ).exists()

    if all_day_block:
        return []

    # Apply time-specific exceptions
    final_ranges = base_ranges.copy()

    for exception in exceptions:
        if exception.start_time and exception.end_time:
            if exception.exception_type == 'block':
                # Remove blocked time from ranges
                final_ranges = _subtract_time_range(
                    final_ranges,
                    exception.start_time,
                    exception.end_time
                )
            elif exception.exception_type == 'available':
                # Add special availability
                final_ranges.append({
                    'start': exception.start_time,
                    'end': exception.end_time
                })

    # Merge overlapping ranges
    final_ranges = _merge_time_ranges(final_ranges)

    return final_ranges


def _subtract_time_range(ranges: List[Dict], block_start: time, block_end: time) -> List[Dict]:
    """
    Subtract a time range from a list of time ranges.
    Example:
        ranges = [{'start': 9:00, 'end': 17:00}]
        block = 12:00 - 13:00
        result = [{'start': 9:00, 'end': 12:00}, {'start': 13:00, 'end': 17:00}]
    """
    result = []

    for range_dict in ranges:
        range_start = range_dict['start']
        range_end = range_dict['end']

        # Case 1: Block doesn't overlap with this range
        if block_end <= range_start or block_start >= range_end:
            result.append(range_dict)
            continue

        # Case 2: Block completely covers this range
        if block_start <= range_start and block_end >= range_end:
            continue  # Skip this range entirely

        # Case 3: Block is in the middle of range
        if block_start > range_start and block_end < range_end:
            result.append({'start': range_start, 'end': block_start})
            result.append({'start': block_end, 'end': range_end})
            continue

        # Case 4: Block overlaps start of range
        if block_start <= range_start and block_end < range_end:
            result.append({'start': block_end, 'end': range_end})
            continue

        # Case 5: Block overlaps end of range
        if block_start > range_start and block_end >= range_end:
            result.append({'start': range_start, 'end': block_start})
            continue

    return result


def _merge_time_ranges(ranges: List[Dict]) -> List[Dict]:
    """
    Merge overlapping time ranges.
    Example:
        [{'start': 9:00, 'end': 12:00}, {'start': 11:00, 'end': 14:00}]
        -> [{'start': 9:00, 'end': 14:00}]
    """
    if not ranges:
        return []

    # Sort by start time
    sorted_ranges = sorted(ranges, key=lambda x: x['start'])

    merged = [sorted_ranges[0]]

    for current in sorted_ranges[1:]:
        last = merged[-1]

        # If current overlaps or touches last, merge them
        if current['start'] <= last['end']:
            last['end'] = max(last['end'], current['end'])
        else:
            merged.append(current)

    return merged


def _generate_slots_in_range(
    date_obj: date,
    start_time: time,
    end_time: time,
    duration: int,
    increment: int
) -> List[datetime]:
    """
    Generate time slots within a time range.

    Example:
        start_time = 9:00
        end_time = 12:00
        duration = 60 minutes
        increment = 30 minutes

        Result: [9:00, 9:30, 10:00, 10:30, 11:00]
        (11:30 not included because 11:30 + 60 min = 12:30 > end_time)
    """
    slots = []

    current_dt = datetime.combine(date_obj, start_time)
    end_dt = datetime.combine(date_obj, end_time)

    while current_dt + timedelta(minutes=duration) <= end_dt:
        slots.append(current_dt)
        current_dt += timedelta(minutes=increment)

    return slots


def _is_slot_available(
    teacher,
    slot_datetime: datetime,
    duration: int,
    settings
) -> bool:
    """
    Check if a specific slot is available.
    Checks:
        1. Advance booking rules (min/max notice)
        2. Existing lessons (conflicts)
        3. Buffer time requirements
    """
    now = timezone.now()

    # Make slot_datetime timezone-aware if it's naive
    if timezone.is_naive(slot_datetime):
        slot_datetime = timezone.make_aware(slot_datetime)

    # Check minimum booking notice
    min_notice = timedelta(hours=settings.min_booking_notice_hours)
    if slot_datetime < now + min_notice:
        return False

    # Check maximum booking window
    max_advance = timedelta(days=settings.max_booking_days_ahead)
    if slot_datetime > now + max_advance:
        return False

    # Check for existing lesson conflicts
    slot_end = slot_datetime + timedelta(minutes=duration)

    # Get all non-deleted lessons for this teacher on this date
    existing_lessons = Lesson.objects.filter(
        teacher=teacher,
        lesson_date=slot_datetime.date(),
        is_deleted=False
    ).exclude(
        approved_status='Rejected'
    )

    for lesson in existing_lessons:
        lesson_start = datetime.combine(
            lesson.lesson_date,
            lesson.lesson_time
        )
        # Make timezone-aware
        if timezone.is_naive(lesson_start):
            lesson_start = timezone.make_aware(lesson_start)

        lesson_end = lesson_start + timedelta(minutes=lesson.duration_in_minutes)

        # Add buffer time
        lesson_end_with_buffer = lesson_end + timedelta(minutes=settings.buffer_minutes)

        # Check for overlap
        if slot_datetime < lesson_end_with_buffer and slot_end > lesson_start:
            return False  # Conflict found

    return True


def check_slot_availability(
    teacher,
    slot_datetime: datetime,
    duration: int
) -> Tuple[bool, str]:
    """
    Check if a specific slot is available and return reason if not.

    Returns:
        (is_available: bool, reason: str)

    Examples:
        (True, "")
        (False, "Teacher is not available at this time")
        (False, "This time slot conflicts with an existing lesson")
        (False, "Bookings must be made at least 24 hours in advance")
    """
    # Check if teacher has availability settings
    if not hasattr(teacher, 'availability_settings'):
        return (True, "")  # Teacher hasn't set up availability, allow any time

    settings = teacher.availability_settings

    if not settings.use_availability_calendar:
        return (True, "")  # Availability checking disabled

    # Make timezone-aware if naive
    if timezone.is_naive(slot_datetime):
        slot_datetime = timezone.make_aware(slot_datetime)

    # Check advance booking rules
    now = timezone.now()
    min_notice = timedelta(hours=settings.min_booking_notice_hours)
    if slot_datetime < now + min_notice:
        return (False, f"Bookings must be made at least {settings.min_booking_notice_hours} hours in advance")

    max_advance = timedelta(days=settings.max_booking_days_ahead)
    if slot_datetime > now + max_advance:
        return (False, f"Bookings can only be made up to {settings.max_booking_days_ahead} days in advance")

    # Check if time falls within teacher's available hours
    available_ranges = _get_available_ranges_for_date(teacher, slot_datetime.date())
    slot_time = slot_datetime.time()
    slot_end_time = (slot_datetime + timedelta(minutes=duration)).time()

    is_in_available_range = False
    for range_dict in available_ranges:
        if slot_time >= range_dict['start'] and slot_end_time <= range_dict['end']:
            is_in_available_range = True
            break

    if not is_in_available_range:
        return (False, "Teacher is not available at this time")

    # Check for conflicts with existing lessons
    slot_end = slot_datetime + timedelta(minutes=duration)
    existing_lessons = Lesson.objects.filter(
        teacher=teacher,
        lesson_date=slot_datetime.date(),
        is_deleted=False
    ).exclude(approved_status='Rejected')

    for lesson in existing_lessons:
        lesson_start = datetime.combine(lesson.lesson_date, lesson.lesson_time)
        if timezone.is_naive(lesson_start):
            lesson_start = timezone.make_aware(lesson_start)

        lesson_end = lesson_start + timedelta(minutes=lesson.duration_in_minutes)
        lesson_end_with_buffer = lesson_end + timedelta(minutes=settings.buffer_minutes)

        if slot_datetime < lesson_end_with_buffer and slot_end > lesson_start:
            return (False, "This time slot conflicts with an existing lesson")

    return (True, "")
