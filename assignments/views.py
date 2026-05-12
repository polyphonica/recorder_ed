from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
import json
import os

from .models import Assignment, AssignmentSubmission, SubmissionAttachment, FeedbackRound
from lessons.models import LessonAssignment
from .forms import AssignmentForm, AssignToStudentForm, GradeSubmissionForm, SubmissionForm
from apps.private_teaching.notifications import StudentNotificationService

_ALLOWED_ATTACHMENT_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB
_MAX_ATTACHMENTS = 5


def _is_valid_attachment(file):
    _, ext = os.path.splitext(file.name.lower())
    return ext in _ALLOWED_ATTACHMENT_EXTENSIONS and file.size <= _MAX_ATTACHMENT_SIZE


def _save_attachments(request, submission, uploader, field_name='attachments', round_number=None):
    if round_number is None:
        round_number = submission.current_round_number
    files = request.FILES.getlist(field_name)
    existing_count = submission.attachments.filter(uploaded_by=uploader, round_number=round_number).count()
    slots = max(0, _MAX_ATTACHMENTS - existing_count)
    skipped = 0
    for f in files[:slots]:
        if _is_valid_attachment(f):
            SubmissionAttachment.objects.create(
                submission=submission,
                file=f,
                uploaded_by=uploader,
                label=f.name,
                round_number=round_number,
            )
        else:
            skipped += 1
    if skipped:
        messages.warning(request, f'{skipped} file(s) were skipped — only JPG, PNG, PDF under 10MB are accepted.')


# ============= TEACHER VIEWS =============

@login_required
def assignment_create(request):
    """Teacher creates a new assignment"""
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user
            assignment.save()
            form.save_m2m()
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
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
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
    """Teacher's library of created assignments with search and filters"""
    from django.db.models import Q

    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    difficulty = request.GET.get('difficulty', '').strip()
    grading_scale = request.GET.get('grading_scale', '').strip()
    tag_id = request.GET.get('tag', '').strip()
    assignment_type = request.GET.get('type', '').strip()  # notation, written, or both
    view_mode = request.GET.get('mode', 'my_assignments')  # 'my_assignments' or 'browse_all'

    # Base queryset
    assignments = Assignment.objects.filter(
        is_active=True
    ).prefetch_related('tags')

    # Filter by view mode
    if view_mode == 'my_assignments':
        # Show only assignments created by the logged-in teacher
        assignments = assignments.filter(created_by=request.user)
    elif view_mode == 'browse_all':
        # Show all public assignments
        assignments = assignments.filter(is_public=True)

    # Apply search filter
    if search_query:
        assignments = assignments.filter(
            Q(title__icontains=search_query) |
            Q(instructions__icontains=search_query)
        )

    # Apply difficulty filter
    if difficulty:
        assignments = assignments.filter(difficulty=difficulty)

    # Apply grading scale filter
    if grading_scale:
        assignments = assignments.filter(grading_scale=grading_scale)

    # Apply tag filter
    if tag_id:
        assignments = assignments.filter(tags__id=tag_id)

    # Apply assignment type filter
    if assignment_type == 'notation':
        assignments = assignments.filter(has_notation_component=True, has_written_component=False)
    elif assignment_type == 'written':
        assignments = assignments.filter(has_notation_component=False, has_written_component=True)
    elif assignment_type == 'both':
        assignments = assignments.filter(has_notation_component=True, has_written_component=True)

    # Order by creation date (newest first)
    assignments = assignments.order_by('-created_at')

    # Limit results for performance
    assignments = assignments[:200]

    # Count how many times each assignment has been assigned
    from lessons.models import LessonAssignment
    for assignment in assignments:
        assignment.times_assigned = LessonAssignment.objects.filter(
            assignment=assignment
        ).count()

    # Get filter options for dropdowns
    from .models import Tag
    tags = Tag.objects.all().order_by('name')

    # Check if filters are active
    filters_active = any([search_query, difficulty, grading_scale, tag_id, assignment_type])

    return render(request, 'assignments/teacher_library.html', {
        'assignments': assignments,
        'tags': tags,
        'difficulty_choices': Assignment.DIFFICULTY_CHOICES,
        'grading_scale_choices': Assignment.GRADING_SCALE_CHOICES,
        'search_query': search_query,
        'selected_difficulty': difficulty,
        'selected_grading_scale': grading_scale,
        'selected_tag': tag_id,
        'selected_type': assignment_type,
        'view_mode': view_mode,
        'filters_active': filters_active,
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

            # Check if assignment is already assigned to this student (standalone)
            existing_assignment = LessonAssignment.objects.filter(
                assignment=assignment,
                student=assignment_link.student,
                lesson__isnull=True
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

            StudentNotificationService.send_assignment_given_notification(assignment_link)

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
def assignment_delete(request, pk):
    """Teacher deletes (soft delete) an assignment"""
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user, is_active=True)

    if request.method == 'POST':
        # Soft delete - set is_active to False
        assignment.is_active = False
        assignment.save()
        messages.success(request, f'Assignment "{assignment.title}" has been deleted.')
        return redirect('assignments:teacher_library')

    # If GET request, show confirmation page
    # Count how many times this assignment has been assigned
    times_assigned = LessonAssignment.objects.filter(assignment=assignment).count()

    return render(request, 'assignments/teacher_delete_confirm.html', {
        'assignment': assignment,
        'times_assigned': times_assigned,
    })


@login_required
def teacher_preview(request, pk):
    """Teacher previews assignment as students see it"""
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)

    return render(request, 'assignments/teacher_preview.html', {
        'assignment': assignment,
    })


@login_required
def teacher_submissions(request):
    """Teacher views all submissions from their students"""
    from django.db.models import Q
    from lessons.models import Lesson

    # Single combined query: lesson-linked (via lesson.subject.teacher) + standalone (teacher field)
    assignment_links = LessonAssignment.objects.filter(
        Q(lesson__subject__teacher=request.user, lesson__status=Lesson.Status.ASSIGNED) |
        Q(teacher=request.user, lesson__isnull=True)
    ).select_related(
        'assignment',
        'lesson',
        'lesson__student',
        'lesson__lesson_request',
        'lesson__lesson_request__child_profile',
        'student',
        'child_profile'
    ).order_by('-assigned_at')

    # Get submissions for these assignments
    submissions_data = []

    for link in assignment_links:
        student = link.effective_student
        if not student:
            continue

        if link.child_profile:
            student_name = link.child_profile.full_name
        elif link.lesson and link.lesson.lesson_request and link.lesson.lesson_request.child_profile:
            student_name = link.lesson.lesson_request.child_profile.full_name
        else:
            student_name = student.get_full_name() or student.username

        submission = AssignmentSubmission.objects.filter(
            student=student,
            assignment=link.assignment
        ).first()
        if submission and submission.status in ['submitted', 'feedback_given', 'graded']:
            submissions_data.append({
                'link': link,
                'submission': submission,
                'student_name': student_name,
            })

    # Sort all submissions by submission date (most recent first)
    submissions_data.sort(key=lambda x: x['submission'].submitted_at or x['submission'].updated_at, reverse=True)

    return render(request, 'assignments/teacher_submissions.html', {
        'submissions_data': submissions_data,
    })


@login_required
def grade_submission(request, pk):
    """Teacher grades or gives feedback on a student's submission"""
    submission = get_object_or_404(
        AssignmentSubmission,
        pk=pk,
        assignment__created_by=request.user
    )

    from lessons.models import LessonAssignment
    assignment_link = LessonAssignment.objects.filter(
        assignment=submission.assignment,
        lesson__student=submission.student
    ).select_related('lesson', 'lesson__lesson_request', 'lesson__lesson_request__child_profile').first()

    student_display_name = submission.student.get_full_name() or submission.student.username
    if assignment_link and assignment_link.lesson and assignment_link.lesson.lesson_request and assignment_link.lesson.lesson_request.child_profile:
        student_display_name = assignment_link.lesson.lesson_request.child_profile.full_name

    if request.method == 'POST':
        action = request.POST.get('action', 'grade')

        if action == 'give_feedback':
            feedback_text = request.POST.get('interim_feedback', '').strip()
            feedback_round = submission.give_feedback(feedback_text, given_by=request.user)
            _save_attachments(request, submission, request.user,
                              field_name='teacher_attachments',
                              round_number=feedback_round.round_number)
            try:
                from apps.private_teaching.notifications import StudentNotificationService
                StudentNotificationService.send_assignment_feedback_notification(submission, assignment_link)
            except Exception:
                pass
            messages.success(request, f'Feedback sent to {student_display_name}.')
            return redirect('assignments:teacher_submissions')

        else:  # action == 'grade'
            if submission.status == 'graded':
                messages.error(request, 'This submission has already been graded.')
                return redirect('assignments:teacher_submissions')
            form = GradeSubmissionForm(request.POST, instance=submission)
            if form.is_valid():
                graded_submission = form.save(commit=False)
                graded_submission.grade_submission(
                    grade=graded_submission.grade,
                    feedback=graded_submission.feedback,
                    graded_by=request.user
                )
                current_round = submission.current_round_number
                _save_attachments(request, submission, request.user,
                                  field_name='teacher_attachments',
                                  round_number=current_round)
                messages.success(request, f'Graded submission for {student_display_name}!')
                return redirect('assignments:teacher_submissions')
    else:
        form = GradeSubmissionForm(instance=submission)

    # Build rounds history for display
    current_round_number = submission.current_round_number
    past_rounds = []
    for feedback_round in submission.rounds.all():
        past_rounds.append({
            'round': feedback_round,
            'student_attachments': submission.attachments.filter(
                uploaded_by=submission.student,
                round_number=feedback_round.round_number
            ),
            'teacher_attachments': submission.attachments.filter(
                uploaded_by=request.user,
                round_number=feedback_round.round_number
            ),
        })

    current_student_attachments = submission.attachments.filter(
        uploaded_by=submission.student,
        round_number=current_round_number
    )
    current_teacher_attachments = submission.attachments.filter(
        uploaded_by=request.user,
        round_number=current_round_number
    )

    return render(request, 'assignments/grade_submission.html', {
        'form': form,
        'submission': submission,
        'assignment_link': assignment_link,
        'student_display_name': student_display_name,
        'past_rounds': past_rounds,
        'current_round_number': current_round_number,
        'current_student_attachments': current_student_attachments,
        'current_teacher_attachments': current_teacher_attachments,
        'max_attachments': _MAX_ATTACHMENTS,
    })


# ============= STUDENT VIEWS =============

@login_required
def student_assignment_library(request):
    """Student's library of assigned assignments from their lessons"""
    from django.db.models import Q
    from lessons.models import Lesson

    # Single combined query: lesson-linked (published lessons for this student) + standalone
    assignment_links = LessonAssignment.objects.filter(
        Q(lesson__student=request.user, lesson__status=Lesson.Status.ASSIGNED) |
        Q(student=request.user, lesson__isnull=True)
    ).select_related(
        'assignment',
        'lesson',
        'lesson__lesson_request',
        'lesson__lesson_request__child_profile',
        'lesson__subject',
        'lesson__subject__teacher',
        'student',
        'teacher'
    ).order_by('-assigned_at')

    # Organize by status
    pending_assignments = []
    submitted_assignments = []
    feedback_assignments = []
    graded_assignments = []

    for link in assignment_links:
        submission = link.submission

        if not submission or submission.status == 'draft':
            pending_assignments.append(link)
        elif submission.status == 'submitted':
            submitted_assignments.append(link)
        elif submission.status == 'feedback_given':
            feedback_assignments.append(link)
        elif submission.status == 'graded':
            graded_assignments.append(link)

    return render(request, 'assignments/student_library.html', {
        'pending_assignments': pending_assignments,
        'submitted_assignments': submitted_assignments,
        'feedback_assignments': feedback_assignments,
        'graded_assignments': graded_assignments,
        'pending_count': len(pending_assignments),
    })


@login_required
def complete_assignment(request, assignment_link_id):
    """Student completes an assignment"""
    from django.core.exceptions import PermissionDenied

    assignment_link = get_object_or_404(
        LessonAssignment.objects.select_related(
            'assignment', 'lesson', 'lesson__lesson_request',
            'lesson__lesson_request__child_profile', 'lesson__subject',
            'lesson__subject__teacher', 'student'
        ),
        pk=assignment_link_id
    )
    # Verify ownership
    if assignment_link.effective_student != request.user:
        raise PermissionDenied

    # Get or create submission
    submission, created = AssignmentSubmission.objects.get_or_create(
        student=request.user,
        assignment=assignment_link.assignment
    )

    # Graded submissions are read-only — redirect to view
    if submission.status == 'graded':
        return redirect('assignments:view_graded', pk=submission.pk)

    if request.method == 'POST':
        if submission.is_submission_locked:
            messages.error(request, 'You have used all your allowed submissions. Your teacher will now grade your work.')
            return redirect('assignments:student_library')

        form = SubmissionForm(request.POST, instance=submission)

        if form.is_valid():
            is_draft = request.POST.get('save_draft') == 'true'
            submission = form.save(commit=False)

            if is_draft:
                submission.save_draft()
                _save_attachments(request, submission, request.user)
                messages.success(request, 'Draft saved successfully!')
            else:
                _save_attachments(request, submission, request.user)
                submission.submit()
                messages.success(request, 'Assignment submitted successfully!')
                return redirect('assignments:student_library')
    else:
        form = SubmissionForm(instance=submission)

    current_round_number = submission.current_round_number
    student_attachments = submission.attachments.filter(
        uploaded_by=request.user,
        round_number=current_round_number
    ) if submission.pk else []

    # Previous feedback rounds for display when re-submitting
    past_rounds = []
    for feedback_round in submission.rounds.all():
        past_rounds.append({
            'round': feedback_round,
            'student_attachments': submission.attachments.filter(
                uploaded_by=request.user,
                round_number=feedback_round.round_number
            ),
            'teacher_attachments': submission.attachments.filter(
                round_number=feedback_round.round_number
            ).exclude(uploaded_by=request.user),
        })

    return render(request, 'assignments/complete_assignment.html', {
        'assignment_link': assignment_link,
        'assignment': assignment_link.assignment,
        'submission': submission,
        'form': form,
        'student_attachments': student_attachments,
        'past_rounds': past_rounds,
        'max_attachments': _MAX_ATTACHMENTS,
        'is_submission_locked': submission.is_submission_locked,
    })


@login_required
def submit_assignment(request, assignment_link_id):
    """Student submits their completed assignment"""
    from django.core.exceptions import PermissionDenied
    assignment_link = get_object_or_404(LessonAssignment, pk=assignment_link_id)
    if assignment_link.effective_student != request.user:
        raise PermissionDenied

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

    # Get the LessonAssignment for messaging link
    from django.db.models import Q
    assignment_link = LessonAssignment.objects.filter(
        Q(lesson__student=request.user) | Q(student=request.user),
        assignment=submission.assignment
    ).first()

    # Build rounds history
    past_rounds = []
    for feedback_round in submission.rounds.all():
        past_rounds.append({
            'round': feedback_round,
            'student_attachments': submission.attachments.filter(
                uploaded_by=submission.student,
                round_number=feedback_round.round_number
            ),
            'teacher_attachments': submission.attachments.filter(
                round_number=feedback_round.round_number
            ).exclude(uploaded_by=submission.student),
        })

    # Final round: attachments uploaded after the last feedback round (or all if no rounds)
    final_round_number = submission.current_round_number
    final_student_attachments = submission.attachments.filter(
        uploaded_by=submission.student,
        round_number=final_round_number
    )
    final_teacher_attachments = submission.attachments.filter(
        round_number=final_round_number
    ).exclude(uploaded_by=submission.student)

    return render(request, 'assignments/view_graded.html', {
        'submission': submission,
        'assignment_link': assignment_link,
        'past_rounds': past_rounds,
        'final_round_number': final_round_number,
        'final_student_attachments': final_student_attachments,
        'final_teacher_attachments': final_teacher_attachments,
    })


@login_required
def delete_attachment(request, pk):
    from django.core.exceptions import PermissionDenied

    if request.method != 'POST':
        return redirect('assignments:student_library')

    attachment = get_object_or_404(SubmissionAttachment, pk=pk)
    submission = attachment.submission

    if attachment.uploaded_by != request.user:
        raise PermissionDenied

    # Students can only remove attachments when the submission is open for editing
    if attachment.uploaded_by == submission.student and submission.status not in ('draft', 'feedback_given'):
        messages.error(request, 'Attachments cannot be removed after submission.')
        return redirect('assignments:student_library')

    attachment.file.delete(save=False)
    attachment.delete()
    messages.success(request, 'Attachment removed.')

    referer = request.META.get('HTTP_REFERER', '')
    if referer:
        return redirect(referer)
    return redirect('assignments:student_library')


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
