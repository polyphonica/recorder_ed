from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
import json

from .models import Assignment, AssignmentSubmission
from apps.private_teaching.models import PrivateLessonAssignment
from .forms import AssignmentForm, AssignToStudentForm, GradeSubmissionForm, SubmissionForm


# ============= TEACHER VIEWS =============

@login_required
def assignment_create(request):
    """Teacher creates a new assignment"""
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user
            assignment.save()
            messages.success(request, f'Assignment "{assignment.title}" created successfully!')
            return redirect('assignments:teacher_library')
    else:
        form = AssignmentForm()

    return render(request, 'assignments/teacher_create.html', {
        'form': form,
    })


@login_required
def assignment_edit(request, pk):
    """Teacher edits an existing assignment"""
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Assignment "{assignment.title}" updated successfully!')
            return redirect('assignments:teacher_library')
    else:
        form = AssignmentForm(instance=assignment)

    return render(request, 'assignments/teacher_edit.html', {
        'form': form,
        'assignment': assignment,
    })


@login_required
def teacher_assignment_library(request):
    """Teacher's library of created assignments"""
    assignments = Assignment.objects.filter(
        created_by=request.user,
        is_active=True
    ).order_by('-created_at')

    # Count how many times each assignment has been assigned
    for assignment in assignments:
        assignment.times_assigned = PrivateLessonAssignment.objects.filter(
            assignment=assignment
        ).count()

    return render(request, 'assignments/teacher_library.html', {
        'assignments': assignments,
    })


@login_required
def assign_to_student(request, pk):
    """Teacher assigns an assignment to a student"""
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = AssignToStudentForm(request.POST, teacher=request.user)
        if form.is_valid():
            assignment_link = form.save(commit=False)
            assignment_link.assignment = assignment
            assignment_link.teacher = request.user

            # Check if assignment is already assigned to this student
            existing_assignment = PrivateLessonAssignment.objects.filter(
                assignment=assignment,
                student=assignment_link.student
            ).first()

            if existing_assignment:
                messages.error(
                    request,
                    f'Assignment "{assignment.title}" is already assigned to {assignment_link.student.get_full_name() or assignment_link.student.username}.'
                )
                return redirect('assignments:teacher_library')

            assignment_link.save()

            # Create an empty submission for the student
            AssignmentSubmission.objects.get_or_create(
                student=assignment_link.student,
                assignment=assignment
            )

            messages.success(
                request,
                f'Assignment "{assignment.title}" assigned to {assignment_link.student.get_full_name() or assignment_link.student.username}!'
            )
            return redirect('assignments:teacher_library')
    else:
        form = AssignToStudentForm(teacher=request.user)

    return render(request, 'assignments/assign_to_student.html', {
        'form': form,
        'assignment': assignment,
    })


@login_required
def teacher_submissions(request):
    """Teacher views all submissions from their students"""
    # Get all assignment links where this user is the teacher
    assignment_links = PrivateLessonAssignment.objects.filter(
        teacher=request.user
    ).select_related('assignment', 'student', 'lesson', 'lesson__lesson_request', 'lesson__lesson_request__child_profile').order_by('-assigned_at')

    # Get submissions for these assignments
    submissions_data = []
    for link in assignment_links:
        submission = link.submission
        if submission and submission.status in ['submitted', 'graded']:
            submissions_data.append({
                'link': link,
                'submission': submission,
            })

    return render(request, 'assignments/teacher_submissions.html', {
        'submissions_data': submissions_data,
    })


@login_required
def grade_submission(request, pk):
    """Teacher grades a student's submission"""
    submission = get_object_or_404(
        AssignmentSubmission,
        pk=pk,
        assignment__created_by=request.user
    )

    # Get the assignment link to access lesson and child profile info
    assignment_link = PrivateLessonAssignment.objects.filter(
        assignment=submission.assignment,
        student=submission.student
    ).select_related('lesson', 'lesson__lesson_request', 'lesson__lesson_request__child_profile').first()

    # Parse written questions if they exist
    written_questions = []
    if submission.assignment.has_written_component and submission.assignment.written_questions:
        try:
            written_questions = json.loads(submission.assignment.written_questions)
        except (json.JSONDecodeError, TypeError):
            written_questions = []

    # Determine student display name
    student_display_name = submission.student.get_full_name() or submission.student.username
    if assignment_link and assignment_link.lesson and assignment_link.lesson.lesson_request and assignment_link.lesson.lesson_request.child_profile:
        student_display_name = assignment_link.lesson.lesson_request.child_profile.full_name

    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            graded_submission = form.save(commit=False)
            graded_submission.grade_submission(
                grade=graded_submission.grade,
                feedback=graded_submission.feedback,
                graded_by=request.user
            )
            messages.success(request, f'Graded submission for {student_display_name}!')
            return redirect('assignments:teacher_submissions')
    else:
        form = GradeSubmissionForm(instance=submission)

    return render(request, 'assignments/grade_submission.html', {
        'form': form,
        'submission': submission,
        'written_questions': written_questions,
        'assignment_link': assignment_link,
    })


# ============= STUDENT VIEWS =============

@login_required
def student_assignment_library(request):
    """Student's library of assigned assignments from their lessons"""
    from lessons.models import LessonAssignment, Lesson

    # Get all lessons for this student
    student_lessons = Lesson.objects.filter(
        student=request.user,
        status='Assigned'  # Only show assignments from assigned (published) lessons
    ).select_related('lesson_request', 'lesson_request__child_profile', 'subject', 'subject__teacher')

    # Get all assignment links from these lessons
    lesson_ids = student_lessons.values_list('id', flat=True)
    assignment_links = LessonAssignment.objects.filter(
        lesson_id__in=lesson_ids
    ).select_related(
        'assignment',
        'lesson',
        'lesson__lesson_request',
        'lesson__lesson_request__child_profile',
        'lesson__subject',
        'lesson__subject__teacher'
    ).order_by('-assigned_at')

    # Organize by status
    pending_assignments = []
    submitted_assignments = []
    graded_assignments = []

    for link in assignment_links:
        # Check if there's a submission for this assignment
        try:
            submission = AssignmentSubmission.objects.get(
                student=request.user,
                assignment=link.assignment
            )
        except AssignmentSubmission.DoesNotExist:
            submission = None

        # Add link with submission info
        link.submission = submission

        if not submission or submission.status == 'draft':
            # Not submitted yet - show in pending
            pending_assignments.append(link)
        elif submission.status == 'submitted':
            # Submitted but not graded yet
            submitted_assignments.append(link)
        elif submission.status == 'graded':
            # Graded assignments
            graded_assignments.append(link)

    return render(request, 'assignments/student_library.html', {
        'pending_assignments': pending_assignments,
        'submitted_assignments': submitted_assignments,
        'graded_assignments': graded_assignments,
        'pending_count': len(pending_assignments),
    })


@login_required
def complete_assignment(request, assignment_link_id):
    """Student completes an assignment"""
    from lessons.models import LessonAssignment

    assignment_link = get_object_or_404(
        LessonAssignment.objects.select_related(
            'assignment', 'lesson', 'lesson__lesson_request', 'lesson__lesson_request__child_profile', 'lesson__subject', 'lesson__subject__teacher'
        ),
        pk=assignment_link_id,
        lesson__student=request.user  # Ensure this assignment's lesson belongs to this student
    )

    # Get or create submission
    submission, created = AssignmentSubmission.objects.get_or_create(
        student=request.user,
        assignment=assignment_link.assignment
    )

    # Parse written questions if they exist
    written_questions = []
    if assignment_link.assignment.has_written_component and assignment_link.assignment.written_questions:
        try:
            written_questions = json.loads(assignment_link.assignment.written_questions)
        except (json.JSONDecodeError, TypeError):
            written_questions = []

    if request.method == 'POST':
        # Check if it's a save draft request
        is_draft = request.POST.get('save_draft') == 'true'

        # Save notation data
        notation_data = request.POST.get('notation_data')
        if notation_data:
            try:
                submission.notation_data = json.loads(notation_data)
            except json.JSONDecodeError:
                submission.notation_data = notation_data

        # Save written answers
        written_answers = []
        for i, question in enumerate(written_questions):
            answer = request.POST.get(f'written_answer_{i}', '')
            written_answers.append({
                'question_index': i,
                'answer': answer
            })
        submission.written_answers = written_answers

        if is_draft:
            submission.save_draft()
            messages.success(request, 'Draft saved successfully!')
        else:
            # Submit the assignment
            submission.submit()
            messages.success(request, 'Assignment submitted successfully!')
            return redirect('assignments:student_library')

    return render(request, 'assignments/complete_assignment.html', {
        'assignment_link': assignment_link,
        'assignment': assignment_link.assignment,
        'submission': submission,
        'written_questions': written_questions,
    })


@login_required
def submit_assignment(request, assignment_link_id):
    """Student submits their completed assignment"""
    assignment_link = get_object_or_404(
        PrivateLessonAssignment,
        pk=assignment_link_id,
        student=request.user
    )

    submission = get_object_or_404(
        AssignmentSubmission,
        student=request.user,
        assignment=assignment_link.assignment
    )

    if submission.status == 'draft':
        submission.submit()
        messages.success(request, 'Assignment submitted successfully!')
    else:
        messages.info(request, 'This assignment has already been submitted.')

    return redirect('assignments:student_library')


@login_required
def view_graded_assignment(request, pk):
    """Student views their graded assignment"""
    submission = get_object_or_404(
        AssignmentSubmission,
        pk=pk,
        student=request.user,
        status='graded'
    )

    # Parse written questions if they exist
    written_questions = []
    if submission.assignment.has_written_component and submission.assignment.written_questions:
        try:
            written_questions = json.loads(submission.assignment.written_questions)
        except (json.JSONDecodeError, TypeError):
            written_questions = []

    return render(request, 'assignments/view_graded.html', {
        'submission': submission,
        'written_questions': written_questions,
    })


# ============= HELPER FUNCTIONS =============

def _get_student_status(assignment_link, submission):
    """Determine the display status for a student's assignment"""
    if not submission:
        return 'Not Started'
    elif submission.status == 'draft':
        return 'In Progress'
    elif submission.status == 'submitted':
        if assignment_link.is_overdue:
            return 'Submitted (Late)'
        return 'Submitted'
    elif submission.status == 'graded':
        return f'Graded ({submission.grade}/100)'
    return 'Unknown'
