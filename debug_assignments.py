#!/usr/bin/env python
"""
Debug script to check assignment visibility
Run with: python manage.py shell < debug_assignments.py
"""

from lessons.models import Lesson, LessonAssignment
from assignments.models import Assignment, AssignmentSubmission
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n=== DEBUGGING ASSIGNMENT VISIBILITY ===\n")

# Check all lessons with status='Assigned' that have assignments
lessons_with_assignments = Lesson.objects.filter(
    status='Assigned',
    lesson_assignments__isnull=False
).distinct()

print(f"Found {lessons_with_assignments.count()} Assigned lessons with homework assignments:\n")

for lesson in lessons_with_assignments:
    print(f"Lesson ID: {lesson.id}")
    print(f"  Date: {lesson.lesson_date}")
    print(f"  Subject: {lesson.subject}")
    print(f"  Student: {lesson.student.username} (ID: {lesson.student.id})")
    print(f"  Status: {lesson.status}")

    # Get assignments for this lesson
    lesson_assignments = LessonAssignment.objects.filter(lesson=lesson)
    print(f"  Assignments ({lesson_assignments.count()}):")

    for la in lesson_assignments:
        print(f"    - {la.assignment.title} (LessonAssignment ID: {la.id})")

        # Check if submission exists
        try:
            submission = AssignmentSubmission.objects.get(
                student=lesson.student,
                assignment=la.assignment
            )
            print(f"      Submission exists: {submission.status}")
        except AssignmentSubmission.DoesNotExist:
            print(f"      No submission found")

    print()

print("\n=== END DEBUG ===\n")
