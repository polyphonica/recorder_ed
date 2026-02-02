from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone

from apps.aural_training.models import StudentIntervalProgress, AuralTrainingSession
from .serializers import (
    IntervalProgressSerializer, SessionSerializer,
    RecordAnswerSerializer, UnlockIntervalsSerializer
)


# Level progression intervals (matching POC)
LEVEL_INTERVALS = [
    ['P5', 'P8'],  # Level 1
    ['P5', 'P8', 'P4'],  # Level 2
    ['P5', 'P8', 'P4', 'M3'],  # Level 3
    ['P5', 'P8', 'P4', 'M3', 'm3'],  # Level 4
    ['P5', 'P8', 'P4', 'M3', 'm3', 'M6'],  # Level 5
    ['P5', 'P8', 'P4', 'M3', 'm3', 'M6', 'M2'],  # Level 6
    ['P5', 'P8', 'P4', 'M3', 'm3', 'M6', 'M2', 'm6', 'm2'],  # Level 7
    ['P5', 'P8', 'P4', 'M3', 'm3', 'M6', 'M2', 'm6', 'm2', 'M7', 'm7'],  # Level 8
]


class LoadProgressAPIView(APIView):
    """
    GET: Load all progress data for current student on page load.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        child_profile_id = request.query_params.get('child_profile')

        # Get or create progress records for all intervals
        progress_records = []
        default_unlocked = ['P5', 'P8']  # Level 1 intervals

        for interval_code, interval_name in StudentIntervalProgress.INTERVAL_CHOICES:
            progress, created = StudentIntervalProgress.objects.get_or_create(
                student=request.user,
                child_profile_id=child_profile_id if child_profile_id else None,
                interval=interval_code,
                defaults={'unlocked': interval_code in default_unlocked}
            )
            progress_records.append(progress)

        # Calculate current level based on unlocked intervals
        current_level = self._calculate_level(progress_records)

        # Calculate totals
        total_attempts = sum(p.attempts for p in progress_records)
        total_correct = sum(p.correct for p in progress_records)
        intervals_mastered = sum(1 for p in progress_records if p.is_mastered)

        return Response({
            'interval_progress': IntervalProgressSerializer(progress_records, many=True).data,
            'current_level': current_level,
            'total_attempts': total_attempts,
            'total_correct': total_correct,
            'intervals_mastered': intervals_mastered,
        })

    def _calculate_level(self, progress_records):
        """Calculate current level based on unlocked intervals"""
        unlocked = {p.interval for p in progress_records if p.unlocked}

        for level, intervals in enumerate(LEVEL_INTERVALS):
            if not all(i in unlocked for i in intervals):
                return level
        return len(LEVEL_INTERVALS)


class StartSessionAPIView(APIView):
    """
    POST: Start a new training session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mode = request.data.get('mode', 'training')
        child_profile_id = request.data.get('child_profile')

        session = AuralTrainingSession.objects.create(
            student=request.user,
            child_profile_id=child_profile_id if child_profile_id else None,
            mode=mode
        )

        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class RecordAnswerAPIView(APIView):
    """
    POST: Record a single answer and update progress.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RecordAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get session
        try:
            session = AuralTrainingSession.objects.get(
                id=data['session_id'],
                student=request.user
            )
        except AuralTrainingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        # Update session stats
        session.questions_attempted += 1
        if data['correct']:
            session.questions_correct += 1
        session.highest_streak = max(session.highest_streak, data.get('current_streak', 0))
        session.current_level = data.get('current_level', session.current_level)
        session.save()

        # Update interval progress
        progress, _ = StudentIntervalProgress.objects.get_or_create(
            student=request.user,
            child_profile=session.child_profile,
            interval=data['interval']
        )
        progress.attempts += 1
        if data['correct']:
            progress.correct += 1
        progress.save()

        return Response({
            'session': SessionSerializer(session).data,
            'interval_progress': IntervalProgressSerializer(progress).data
        })


class UnlockIntervalsAPIView(APIView):
    """
    POST: Unlock intervals when student levels up.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UnlockIntervalsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        child_profile_id = request.data.get('child_profile')

        unlocked_progress = []
        for interval in data['intervals']:
            progress, _ = StudentIntervalProgress.objects.get_or_create(
                student=request.user,
                child_profile_id=child_profile_id if child_profile_id else None,
                interval=interval
            )
            progress.unlocked = True
            progress.save()
            unlocked_progress.append(progress)

        return Response({
            'unlocked': IntervalProgressSerializer(unlocked_progress, many=True).data
        })


class EndSessionAPIView(APIView):
    """
    POST: End an active session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get('session_id')

        try:
            session = AuralTrainingSession.objects.get(
                id=session_id,
                student=request.user,
                ended_at__isnull=True
            )
        except AuralTrainingSession.DoesNotExist:
            return Response({'error': 'Active session not found'}, status=status.HTTP_404_NOT_FOUND)

        session.ended_at = timezone.now()
        session.save()

        return Response(SessionSerializer(session).data)
