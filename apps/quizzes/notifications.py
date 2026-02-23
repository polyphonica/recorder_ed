"""
Quiz notification helpers (wrappers around the private_teaching notification services).
"""
import logging

from apps.private_teaching.notifications import (
    TeacherNotificationService,
    StudentNotificationService,
)

logger = logging.getLogger(__name__)


def send_quiz_submission_notification(attempt):
    """Send notification to teacher when a student submits a quiz."""
    return TeacherNotificationService.send_quiz_submission_notification(attempt)


def send_quiz_assignment_notification(assignment):
    """Send notification to student when teacher assigns a quiz."""
    return StudentNotificationService.send_quiz_assignment_notification(assignment)
