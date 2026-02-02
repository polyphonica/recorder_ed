from rest_framework import serializers
from apps.aural_training.models import StudentIntervalProgress, AuralTrainingSession


class IntervalProgressSerializer(serializers.ModelSerializer):
    accuracy = serializers.ReadOnlyField()
    is_mastered = serializers.ReadOnlyField()
    interval_display = serializers.CharField(source='get_interval_display', read_only=True)

    class Meta:
        model = StudentIntervalProgress
        fields = [
            'id', 'interval', 'interval_display',
            'attempts', 'correct', 'unlocked',
            'accuracy', 'is_mastered', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class SessionSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.ReadOnlyField()
    accuracy = serializers.ReadOnlyField()
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)

    class Meta:
        model = AuralTrainingSession
        fields = [
            'id', 'mode', 'mode_display',
            'started_at', 'ended_at', 'duration_minutes',
            'questions_attempted', 'questions_correct',
            'highest_streak', 'current_level', 'accuracy'
        ]
        read_only_fields = ['id', 'started_at']


class RecordAnswerSerializer(serializers.Serializer):
    """Serializer for recording an individual answer"""
    session_id = serializers.UUIDField()
    interval = serializers.ChoiceField(choices=StudentIntervalProgress.INTERVAL_CHOICES)
    correct = serializers.BooleanField()
    current_streak = serializers.IntegerField(min_value=0, required=False, default=0)
    current_level = serializers.IntegerField(min_value=0, max_value=7, required=False, default=0)


class UnlockIntervalsSerializer(serializers.Serializer):
    """Serializer for unlocking intervals when leveling up"""
    intervals = serializers.ListField(
        child=serializers.ChoiceField(choices=StudentIntervalProgress.INTERVAL_CHOICES)
    )
