"""
URL Configuration for Teacher Availability Calendar API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TeacherAvailabilityViewSet,
    AvailabilityExceptionViewSet,
    TeacherAvailabilitySettingsViewSet,
    AvailableSlotsAPIView,
    SubmitBookingAPIView,
    PreviewRecurringSlotsAPIView
)

# Create router for viewsets
router = DefaultRouter()
router.register('teacher-availability', TeacherAvailabilityViewSet, basename='teacher-availability')
router.register('availability-exceptions', AvailabilityExceptionViewSet, basename='availability-exceptions')
router.register('availability-settings', TeacherAvailabilitySettingsViewSet, basename='availability-settings')

app_name = 'private_teaching_api'

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),

    # Custom API endpoints
    path('student/available-slots/', AvailableSlotsAPIView.as_view(), name='available-slots'),
    path('student/submit-booking/', SubmitBookingAPIView.as_view(), name='submit-booking'),
    path('student/preview-recurring/', PreviewRecurringSlotsAPIView.as_view(), name='preview-recurring-slots'),
]
