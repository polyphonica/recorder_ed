"""
API Views for Teacher Availability Calendar
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import datetime, timedelta

from apps.private_teaching.models import (
    TeacherAvailability,
    AvailabilityException,
    TeacherAvailabilitySettings,
    Subject,
    LessonRequest,
    LessonRequestMessage
)
from lessons.models import Lesson
from .serializers import (
    TeacherAvailabilitySerializer,
    AvailabilityExceptionSerializer,
    TeacherAvailabilitySettingsSerializer,
    BulkAvailabilityUpdateSerializer,
    RecurringPreviewRequestSerializer,
    RecurringSlotSerializer
)
from apps.private_teaching.availability_engine import (
    calculate_available_slots,
    check_slot_availability,
    generate_recurring_slots
)

User = get_user_model()


class TeacherAvailabilityViewSet(viewsets.ModelViewSet):
    """
    API endpoints for teacher availability management
    """
    serializer_class = TeacherAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only return current teacher's availability"""
        return TeacherAvailability.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        """Set teacher to current user"""
        serializer.save(teacher=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update weekly availability
        Expected payload:
        {
            "monday": [{"start": "09:00", "end": "17:00"}],
            "tuesday": [],  // No availability
            "wednesday": [{"start": "09:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}]
            ...
        }
        """
        serializer = BulkAvailabilityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Delete existing availability
        TeacherAvailability.objects.filter(teacher=request.user).delete()

        # Create new availability slots
        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2,
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }

        created_slots = []
        for day_name, slots in serializer.validated_data.items():
            day_num = day_mapping.get(day_name)
            if day_num is None or not slots:
                continue

            for slot in slots:
                try:
                    availability = TeacherAvailability.objects.create(
                        teacher=request.user,
                        day_of_week=day_num,
                        start_time=slot['start'],
                        end_time=slot['end']
                    )
                    created_slots.append(availability)
                except Exception as e:
                    return Response(
                        {'error': f'Error creating slot: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        return Response({
            'status': 'success',
            'created_count': len(created_slots),
            'message': f'Created {len(created_slots)} availability slots'
        })


class AvailabilityExceptionViewSet(viewsets.ModelViewSet):
    """
    API endpoints for availability exceptions (blocks, special hours)
    """
    serializer_class = AvailabilityExceptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only return current teacher's exceptions"""
        return AvailabilityException.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        """Set teacher to current user"""
        serializer.save(teacher=self.request.user)


class TeacherAvailabilitySettingsViewSet(viewsets.ModelViewSet):
    """
    API endpoints for teacher availability settings
    """
    serializer_class = TeacherAvailabilitySettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only return current teacher's settings"""
        return TeacherAvailabilitySettings.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        """Set teacher to current user"""
        serializer.save(teacher=self.request.user)

    @action(detail=False, methods=['get', 'post', 'put', 'patch'])
    def my_settings(self, request):
        """
        Get or update current teacher's settings
        """
        settings, created = TeacherAvailabilitySettings.objects.get_or_create(
            teacher=request.user
        )

        if request.method == 'GET':
            serializer = self.get_serializer(settings)
            return Response(serializer.data)

        # Update settings
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvailableSlotsAPIView(APIView):
    """
    API endpoint for students to view available slots
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get available time slots for a teacher
        Query params:
            - teacher_id: ID of teacher
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)
            - duration: Lesson duration in minutes (30, 45, 60, 90)

        Returns:
        {
            "slots": [
                {
                    "datetime": "2025-06-15T09:00:00",
                    "duration": 60,
                    "available": true,
                    "end_datetime": "2025-06-15T10:00:00"
                },
                ...
            ]
        }
        """
        teacher_id = request.query_params.get('teacher_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        duration = int(request.query_params.get('duration', 60))

        # Validate parameters
        if not all([teacher_id, start_date_str, end_date_str]):
            return Response(
                {'error': 'Missing required parameters: teacher_id, start_date, end_date'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            teacher = User.objects.get(id=teacher_id)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except User.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Call availability calculation engine
        try:
            available_slots = calculate_available_slots(
                teacher=teacher,
                start_date=start_date,
                end_date=end_date,
                duration=duration
            )
            return Response({'slots': available_slots})
        except Exception as e:
            import traceback
            print(f"[ERROR] Failed to calculate available slots: {str(e)}")
            print(traceback.format_exc())
            return Response({
                'error': f'Failed to calculate availability: {str(e)}',
                'slots': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitBookingAPIView(APIView):
    """
    Submit a lesson booking request from student
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Submit booking
        Expected payload:
        {
            "teacher_id": 123,
            "location": "Online",
            "message": "Looking forward to lessons",
            "child_profile_id": 789,  // Optional - for guardian bookings
            "lessons": [
                {"datetime": "2025-06-15T09:00:00", "duration": 60, "subject_id": 456},
                {"datetime": "2025-06-16T10:00:00", "duration": 60, "subject_id": 457}
            ]
        }
        """
        try:
            teacher = User.objects.get(id=request.data['teacher_id'])

            # Create LessonRequest
            lesson_request = LessonRequest.objects.create(
                student=request.user
            )

            # Handle child profile if provided (for guardian bookings)
            child_profile_id = request.data.get('child_profile_id')
            if child_profile_id:
                from apps.accounts.models import ChildProfile
                try:
                    child_profile = ChildProfile.objects.get(
                        id=child_profile_id,
                        guardian=request.user
                    )
                    lesson_request.child_profile = child_profile
                    lesson_request.save()
                except ChildProfile.DoesNotExist:
                    lesson_request.delete()
                    return Response({
                        'success': False,
                        'error': 'Invalid child profile selected'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # First pass: Validate all lessons and check availability
            validated_lessons = []
            for lesson_data in request.data['lessons']:
                # Get subject for this lesson
                subject_id = lesson_data.get('subject_id')
                if not subject_id:
                    lesson_request.delete()
                    return Response({
                        'success': False,
                        'error': 'subject_id is required for each lesson'
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    subject = Subject.objects.get(id=subject_id)
                except Subject.DoesNotExist:
                    lesson_request.delete()
                    return Response({
                        'success': False,
                        'error': f'Subject with id {subject_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                # Verify teacher offers this subject
                if subject.teacher != teacher:
                    lesson_request.delete()
                    return Response({
                        'success': False,
                        'error': f'This teacher does not offer {subject.subject}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Parse datetime
                slot_datetime_str = lesson_data['datetime']
                # Handle ISO format with Z or timezone
                if slot_datetime_str.endswith('Z'):
                    slot_datetime_str = slot_datetime_str[:-1] + '+00:00'

                slot_datetime = datetime.fromisoformat(slot_datetime_str)

                # Validate slot is still available
                is_available, reason = check_slot_availability(
                    teacher=teacher,
                    slot_datetime=slot_datetime,
                    duration=lesson_data['duration']
                )

                if not is_available:
                    # Rollback - delete lesson request
                    lesson_request.delete()
                    return Response({
                        'success': False,
                        'error': f'Time slot {slot_datetime} is no longer available: {reason}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Store validated data for creation
                validated_lessons.append({
                    'subject': subject,
                    'datetime': slot_datetime,
                    'duration': lesson_data['duration']
                })

            # Determine approval status
            auto_approve = (
                hasattr(teacher, 'availability_settings') and
                teacher.availability_settings.auto_approve_bookings
            )
            approved_status = 'Accepted' if auto_approve else 'Pending'

            # Second pass: Create all lessons (only after all validations pass)
            created_lessons = []
            for validated_lesson in validated_lessons:
                lesson = Lesson.objects.create(
                    lesson_request=lesson_request,
                    student=request.user,
                    teacher=teacher,
                    subject=validated_lesson['subject'],
                    lesson_date=validated_lesson['datetime'].date(),
                    lesson_time=validated_lesson['datetime'].time(),
                    duration_in_minutes=validated_lesson['duration'],
                    location=request.data.get('location', 'Online'),
                    approved_status=approved_status,
                    payment_status='Not Paid',
                    status='Draft'
                )
                created_lessons.append(lesson)

            # Add initial message if provided
            if request.data.get('message'):
                LessonRequestMessage.objects.create(
                    lesson_request=lesson_request,
                    author=request.user,
                    message=request.data['message']
                )

            # TODO: Send notification email to teacher

            return Response({
                'success': True,
                'message': f'Successfully booked {len(created_lessons)} lessons',
                'lesson_request_id': lesson_request.id,
                'redirect_url': reverse('private_teaching:my_requests')
            })

        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Teacher not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except KeyError as e:
            return Response({
                'success': False,
                'error': f'Missing required field: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Rollback if lesson_request was created
            if 'lesson_request' in locals():
                lesson_request.delete()

            return Response({
                'success': False,
                'error': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PreviewRecurringSlotsAPIView(APIView):
    """
    API endpoint to preview recurring lesson slots before booking
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Preview recurring slots

        Expected payload:
        {
            "teacher_id": 123,
            "base_datetime": "2025-01-06T18:00:00",
            "duration": 60,
            "num_weeks": 4,
            "subject_id": 456
        }

        Returns:
        {
            "slots": [
                {
                    "datetime": "2025-01-06T18:00:00",
                    "duration": 60,
                    "available": true,
                    "conflict_reason": null,
                    "subject_id": 456
                },
                ...
            ],
            "available_count": 3,
            "conflict_count": 1,
            "teacher_max_allowed": 8
        }
        """
        # Validate request data
        serializer = RecurringPreviewRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get teacher
        try:
            teacher = User.objects.get(id=data['teacher_id'], profile__role='teacher')
        except User.DoesNotExist:
            return Response({
                'error': 'Teacher not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get subject and validate it belongs to teacher
        try:
            subject = Subject.objects.get(id=data['subject_id'], teacher=teacher)
        except Subject.DoesNotExist:
            return Response({
                'error': 'Subject not found or does not belong to this teacher'
            }, status=status.HTTP_404_NOT_FOUND)

        # Generate recurring slots
        try:
            recurring_slots = generate_recurring_slots(
                teacher=teacher,
                base_datetime=data['base_datetime'],
                duration=data['duration'],
                num_weeks=data['num_weeks'],
                subject_id=data['subject_id']
            )
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Error generating recurring slots: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Serialize slots
        slots_serializer = RecurringSlotSerializer(recurring_slots, many=True)

        # Calculate counts
        available_count = sum(1 for slot in recurring_slots if slot['available'])
        conflict_count = sum(1 for slot in recurring_slots if not slot['available'])

        # Get teacher's max allowed
        teacher_max_allowed = teacher.availability_settings.max_recurring_lessons if hasattr(teacher, 'availability_settings') else 8

        return Response({
            'slots': slots_serializer.data,
            'available_count': available_count,
            'conflict_count': conflict_count,
            'teacher_max_allowed': teacher_max_allowed
        }, status=status.HTTP_200_OK)
