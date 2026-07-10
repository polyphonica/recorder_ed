"""
Diagnostic command for the teacher "View Progress" 500 error.

Reproduces TeacherStudentProgressView.get_context_data (and optionally the
template render) for a given student, printing the full traceback so we can
see exactly which line fails on production.

Usage:
    python manage.py diag_student_progress <student_id>
    python manage.py diag_student_progress <student_id> --teacher <teacher_id>
"""
import traceback

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.template.loader import render_to_string

from lessons.models import Lesson
from apps.private_teaching.views import TeacherStudentProgressView


class Command(BaseCommand):
    help = "Reproduce the teacher View Progress page for a student and print any traceback"

    def add_arguments(self, parser):
        parser.add_argument('student_id', type=int)
        parser.add_argument('--teacher', type=int, default=None,
                            help='Teacher user id (auto-detected from lessons if omitted)')

    def handle(self, *args, **options):
        student_id = options['student_id']
        teacher_id = options['teacher']

        if teacher_id is None:
            teacher_id = Lesson.objects.filter(
                student_id=student_id,
                approved_status=Lesson.ApprovalStatus.ACCEPTED,
                is_deleted=False,
            ).values_list('teacher_id', flat=True).first()

        self.stdout.write(f"student_id={student_id}  teacher_id={teacher_id}")
        if not teacher_id:
            self.stderr.write("No accepted-lesson teacher found for this student. "
                              "Pass --teacher <id> explicitly.")
            return

        try:
            teacher = User.objects.get(id=teacher_id)
        except User.DoesNotExist:
            self.stderr.write(f"Teacher {teacher_id} does not exist.")
            return

        req = RequestFactory().get('/')
        req.user = teacher

        view = TeacherStudentProgressView()
        view.request = req
        view.kwargs = {'student_id': student_id}

        # Step 1: build context
        try:
            context = view.get_context_data(student_id=student_id)
        except Exception:
            self.stdout.write("\n===== EXCEPTION IN get_context_data =====")
            traceback.print_exc()
            return

        self.stdout.write("get_context_data OK — trying template render...")

        # Step 2: render the template with that context
        try:
            render_to_string(view.template_name, context, request=req)
        except Exception:
            self.stdout.write("\n===== EXCEPTION IN TEMPLATE RENDER =====")
            traceback.print_exc()
            return

        self.stdout.write(self.style.SUCCESS(
            "\nNo error reproduced — page built and rendered cleanly for this student."))
