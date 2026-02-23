from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class TeacherAvailability(models.Model):
    """
    Represents a teacher's recurring weekly availability pattern.
    Example: "Every Monday from 9:00 AM to 12:00 PM I'm available"
    """
    DAY_OF_WEEK_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='availability_slots',
        help_text="Teacher who owns this availability slot"
    )
    day_of_week = models.IntegerField(
        choices=DAY_OF_WEEK_CHOICES,
        help_text="Day of week (0=Monday, 6=Sunday)"
    )
    start_time = models.TimeField(
        help_text="Start time of availability (e.g., 09:00)"
    )
    end_time = models.TimeField(
        help_text="End time of availability (e.g., 17:00)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to temporarily disable this slot"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_teaching_teacher_availability'
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Teacher Availability Slot'
        verbose_name_plural = 'Teacher Availability Slots'
        indexes = [
            models.Index(fields=['teacher', 'day_of_week'], name='private_tea_teacher_48e31d_idx'),
        ]

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        return f"{teacher_name} - {self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    def clean(self):
        """Validate that end_time is after start_time"""
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")


class AvailabilityException(models.Model):
    """
    Represents exceptions to the recurring availability pattern.
    Used for: vacations, one-time blocks, special available hours
    Example: "On Dec 25, I'm unavailable all day (Christmas)"
    Example: "On Jan 15, I'm available 6 PM - 9 PM (normally closed)"
    """
    EXCEPTION_TYPE_CHOICES = [
        ('block', 'Block Time (Unavailable)'),
        ('available', 'Add Availability (Override)'),
    ]

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='availability_exceptions',
        help_text="Teacher who owns this exception"
    )
    exception_type = models.CharField(
        max_length=20,
        choices=EXCEPTION_TYPE_CHOICES,
        default='block',
        help_text="Type of exception: block unavailable time or add special availability"
    )
    date = models.DateField(
        help_text="Specific date for this exception"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time (leave blank to block entire day)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="End time (leave blank to block entire day)"
    )
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional reason (e.g., 'Christmas Holiday', 'Conference')"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to cancel this exception"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_teaching_availability_exception'
        ordering = ['date', 'start_time']
        verbose_name = 'Availability Exception'
        verbose_name_plural = 'Availability Exceptions'
        indexes = [
            models.Index(fields=['teacher', 'date'], name='private_tea_teacher_2394e5_idx'),
        ]

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        if self.start_time and self.end_time:
            return f"{teacher_name} - {self.date} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')} ({self.get_exception_type_display()})"
        return f"{teacher_name} - {self.date} All Day ({self.get_exception_type_display()})"

    def clean(self):
        """Validate exception data"""
        # If one time is specified, both must be specified
        if (self.start_time is None) != (self.end_time is None):
            raise ValidationError(
                "Both start_time and end_time must be specified, or both left blank for all-day exception"
            )

        # If times are specified, end must be after start
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")

        # Check for conflicting exceptions when blocking time
        if self.exception_type == 'block':
            # Build queryset for existing exceptions
            existing_exceptions = AvailabilityException.objects.filter(
                teacher=self.teacher,
                date=self.date,
                exception_type='block',
                is_active=True
            )

            # Exclude self if updating
            if self.pk:
                existing_exceptions = existing_exceptions.exclude(pk=self.pk)

            # Check for overlapping block exceptions
            if self.start_time and self.end_time:
                # Check for specific time blocks that overlap
                overlapping = existing_exceptions.filter(
                    start_time__isnull=False,
                    end_time__isnull=False,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                )
                if overlapping.exists():
                    raise ValidationError(
                        f"This time conflicts with an existing block on {self.date}. "
                        f"You already have blocked time that overlaps with this period."
                    )

            # Check for all-day blocks
            all_day_blocks = existing_exceptions.filter(
                start_time__isnull=True,
                end_time__isnull=True
            )
            if all_day_blocks.exists():
                raise ValidationError(
                    f"This day is already blocked all day on {self.date}. "
                    f"Remove the existing all-day block before adding a specific time block."
                )

            # If creating an all-day block, check for any existing blocks
            if not self.start_time and not self.end_time:
                if existing_exceptions.exists():
                    raise ValidationError(
                        f"Cannot create an all-day block on {self.date} because there are already "
                        f"specific time blocks on this day. Remove them first or use a specific time range."
                    )

            # Check if this time is already unavailable in the regular schedule
            if self.start_time and self.end_time:
                # Get the day of week for this date
                day_of_week = self.date.weekday()

                # Check if there's any regular availability for this day/time
                available_slots = TeacherAvailability.objects.filter(
                    teacher=self.teacher,
                    day_of_week=day_of_week,
                    is_active=True,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                )

                if not available_slots.exists():
                    raise ValidationError(
                        f"This time is already unavailable in your regular weekly schedule. "
                        f"No need to add a block exception - you don't have recurring availability during this time. "
                        f"If you want to add special hours, use 'Special Hours' instead."
                    )


class TeacherAvailabilitySettings(models.Model):
    """
    Global settings for teacher's availability and booking behavior
    """
    teacher = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='availability_settings',
        help_text="Teacher who owns these settings"
    )

    # Buffer time between lessons
    buffer_minutes = models.IntegerField(
        default=0,
        help_text="Minutes of break time required between lessons (0-60)"
    )

    # Advance booking settings
    min_booking_notice_hours = models.IntegerField(
        default=24,
        help_text="Minimum hours in advance students must book (e.g., 24 = must book at least 1 day ahead)"
    )
    max_booking_days_ahead = models.IntegerField(
        default=90,
        help_text="Maximum days in advance students can book (e.g., 90 = can book up to 3 months ahead)"
    )

    # Availability system enable/disable
    use_availability_calendar = models.BooleanField(
        default=False,
        help_text="Enable availability calendar (if False, uses old request system)"
    )

    # Auto-approval
    auto_approve_bookings = models.BooleanField(
        default=True,
        help_text="Automatically approve bookings if slot is available (recommended)"
    )

    # Timezone
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Teacher's timezone (e.g., 'America/New_York', 'Europe/London')"
    )

    # Recurring lessons settings
    max_recurring_lessons = models.IntegerField(
        default=8,
        help_text="Maximum number of lessons students can book in a recurring sequence (e.g., 8 = up to 8 weekly lessons)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_teaching_availability_settings'
        verbose_name = 'Teacher Availability Settings'
        verbose_name_plural = 'Teacher Availability Settings'

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username
        return f"Availability Settings - {teacher_name}"
