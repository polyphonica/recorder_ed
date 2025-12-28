"""
Serializers for Teacher Availability Calendar API
"""

from rest_framework import serializers
from apps.private_teaching.models import (
    TeacherAvailability,
    AvailabilityException,
    TeacherAvailabilitySettings
)


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for TeacherAvailability model"""

    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = TeacherAvailability
        fields = [
            'id',
            'teacher',
            'day_of_week',
            'day_name',
            'start_time',
            'end_time',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']


class AvailabilityExceptionSerializer(serializers.ModelSerializer):
    """Serializer for AvailabilityException model"""

    exception_type_display = serializers.CharField(source='get_exception_type_display', read_only=True)

    class Meta:
        model = AvailabilityException
        fields = [
            'id',
            'teacher',
            'exception_type',
            'exception_type_display',
            'date',
            'start_time',
            'end_time',
            'reason',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Run model validation to check for conflicts"""
        # Create a temporary instance to validate
        instance = AvailabilityException(**attrs)

        # If updating, set the pk so clean() can exclude self
        if self.instance:
            instance.pk = self.instance.pk

        # Set the teacher from the request context
        if 'teacher' not in attrs and self.context.get('request'):
            instance.teacher = self.context['request'].user

        # Run the model's clean method
        instance.clean()

        return attrs


class TeacherAvailabilitySettingsSerializer(serializers.ModelSerializer):
    """Serializer for TeacherAvailabilitySettings model"""

    class Meta:
        model = TeacherAvailabilitySettings
        fields = [
            'id',
            'teacher',
            'buffer_minutes',
            'min_booking_notice_hours',
            'max_booking_days_ahead',
            'use_availability_calendar',
            'auto_approve_bookings',
            'timezone',
            'max_recurring_lessons',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']


class BulkAvailabilityUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk updating weekly availability
    Expected format:
    {
        "monday": [{"start": "09:00", "end": "17:00"}],
        "tuesday": [{"start": "10:00", "end": "15:00"}],
        ...
    }
    """
    monday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    tuesday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    wednesday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    thursday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    friday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    saturday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    sunday = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )


class RecurringPreviewRequestSerializer(serializers.Serializer):
    """
    Serializer for recurring slot preview requests
    """
    teacher_id = serializers.IntegerField(required=True)
    base_datetime = serializers.DateTimeField(required=True)
    duration = serializers.IntegerField(required=True, min_value=15, max_value=180)
    num_weeks = serializers.IntegerField(required=True, min_value=2, max_value=52)
    subject_id = serializers.IntegerField(required=True)


class RecurringSlotSerializer(serializers.Serializer):
    """
    Serializer for individual recurring slot in preview
    """
    datetime = serializers.DateTimeField()
    duration = serializers.IntegerField()
    available = serializers.BooleanField()
    conflict_reason = serializers.CharField(allow_null=True, required=False)
    subject_id = serializers.IntegerField()
