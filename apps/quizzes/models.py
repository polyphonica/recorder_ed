"""
Unified Quiz models — covers both private-lesson quizzes and course quizzes.

DB tables:
  Quiz          → private_teaching_privatelessonquiz
  QuizQuestion  → private_teaching_privatelessonquizquestion
  QuizAnswer    → private_teaching_privatelessonquizanswer
  QuizAssignment→ private_teaching_privatelessonquizassignment
  QuizAttempt   → private_teaching_privatelessonquizattempt

Two nullable columns were added to support course quizzes:
  Quiz.course_lesson        — OneToOne FK to courses.Lesson (null for private lesson quizzes)
  Quiz.status               — DRAFT/PUBLISHED (null for private lesson quizzes)
  QuizAssignment.course_enrollment — FK to courses.CourseEnrollment (null for private lesson assignments)
"""
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field

User = get_user_model()


class Quiz(models.Model):
    """
    Reusable quiz. Created by teachers for private lesson use, or auto-created
    for course lessons (course_lesson is set in that case).
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core Fields
    title = models.CharField(
        max_length=200,
        help_text="Quiz title (e.g., 'Grade 1 Theory Mock Exam')"
    )
    description = models.TextField(
        blank=True,
        help_text="Overview of what this quiz covers"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Instructions for students taking the quiz"
    )

    # Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_quizzes'
    )

    # Quiz Settings
    pass_percentage = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage to pass (0-100)"
    )
    time_limit_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time limit in minutes (null = no limit)"
    )
    randomize_questions = models.BooleanField(
        default=False,
        help_text="Randomize question order for each attempt"
    )
    show_correct_answers = models.BooleanField(
        default=True,
        help_text="Show correct answers after submission"
    )
    allow_retakes = models.BooleanField(
        default=True,
        help_text="Allow students to retake quiz"
    )
    max_attempts = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum attempts allowed (null = unlimited)"
    )
    pagination_mode = models.CharField(
        max_length=20,
        choices=[
            ('continuous', 'Continuous (Single Page)'),
            ('paginated', 'Paginated (One at a Time)'),
        ],
        default='continuous',
        help_text="Display mode for quiz questions"
    )

    # Categorization (align with LessonTemplate system)
    subject = models.ForeignKey(
        'private_teaching.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    syllabus = models.CharField(
        max_length=50,
        choices=[
            ('abrsm', 'ABRSM'),
            ('trinity', 'Trinity College'),
            ('rcm', 'RCM'),
            ('mtb', 'Music Teachers Board'),
            ('custom', 'Custom'),
        ],
        blank=True
    )
    grade_level = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., '1', 'Beginner', 'Intermediate'"
    )
    tags = models.ManyToManyField(
        'lesson_templates.Tag',
        blank=True,
        related_name='quizzes'
    )

    # Sharing
    is_public = models.BooleanField(
        default=False,
        help_text="Make quiz available to other teachers"
    )

    # Metadata
    use_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -----------------------------------------------------------------------
    # Course context (null for private lesson quizzes)
    # -----------------------------------------------------------------------
    course_lesson = models.OneToOneField(
        'courses.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quiz',
        help_text="Course lesson this quiz is attached to (null for private lesson quizzes)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        null=True,
        blank=True,
        help_text="DRAFT/PUBLISHED status (used by course quizzes only)"
    )

    class Meta:
        db_table = 'private_teaching_privatelessonquiz'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'is_public'], name='private_tea_created_59baa1_idx'),
            models.Index(fields=['syllabus', 'grade_level'], name='private_tea_syllabu_55c321_idx'),
        ]

    def __str__(self):
        return self.title

    @property
    def total_points(self):
        return self.questions.aggregate(
            total=models.Sum('points')
        )['total'] or 0

    @property
    def question_count(self):
        return self.questions.count()

    def get_questions(self, randomize=False):
        questions = self.questions.all()
        if randomize and self.randomize_questions:
            return questions.order_by('?')
        return questions.order_by('order')


class QuizQuestion(models.Model):
    """Individual question within a quiz."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    text = CKEditor5Field(
        config_name='extends',
        help_text="Question text (supports images, music notation, etc.)"
    )
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(
        default=1,
        help_text="Points awarded for correct answer"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Explanation shown after answer (optional)"
    )

    class Meta:
        db_table = 'private_teaching_privatelessonquizquestion'
        verbose_name = 'Quiz Question'
        ordering = ['order']

    def __str__(self):
        from django.utils.html import strip_tags
        text_preview = strip_tags(self.text)[:50]
        return f"Q{self.order}: {text_preview}..."

    def get_answers(self):
        return self.answers.all().order_by('order')

    def get_correct_answer(self):
        return self.answers.filter(is_correct=True).first()

    def get_correct_answers(self):
        return self.answers.filter(is_correct=True)

    def has_multiple_correct_answers(self):
        return self.answers.filter(is_correct=True).count() > 1


class QuizAnswer(models.Model):
    """Answer option for a quiz question."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    text = CKEditor5Field(
        config_name='default',
        help_text="Answer text (supports images, formatting, music notation)"
    )
    is_correct = models.BooleanField(
        default=False,
        help_text="Mark as the correct answer"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'private_teaching_privatelessonquizanswer'
        verbose_name = 'Quiz Answer'
        ordering = ['order']

    def __str__(self):
        correct_marker = "✓" if self.is_correct else "✗"
        return f"{correct_marker} {self.text[:50]}"


class QuizAssignment(models.Model):
    """
    Assignment of a quiz to a specific student. Used for both:
    - Private lesson quizzes (teacher→student, course_enrollment=null)
    - Course quizzes (course_enrollment is set, teacher/student may be null)
    """
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_quizzes',
        null=True,
        blank=True,
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_quizzes',
        null=True,
        blank=True,
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_quizzes',
        help_text="If student is a guardian, specify which child"
    )
    lesson = models.ForeignKey(
        'lessons.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quiz_assignments',
        help_text="Link to specific private lesson (optional)"
    )

    # Assignment Details
    assigned_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional deadline"
    )
    notes = models.TextField(
        blank=True,
        help_text="Teacher notes for student about this quiz"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='assigned'
    )

    # Course context (null for private lesson assignments)
    course_enrollment = models.ForeignKey(
        'courses.CourseEnrollment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='quiz_assignments',
        help_text="Course enrollment (course context only)"
    )

    class Meta:
        db_table = 'private_teaching_privatelessonquizassignment'
        verbose_name = 'Quiz Assignment'
        ordering = ['-assigned_date']
        indexes = [
            models.Index(fields=['student', 'status'], name='private_tea_student_0a9066_idx'),
            models.Index(fields=['teacher', 'assigned_date'], name='private_tea_teacher_fcd363_idx'),
        ]
        unique_together = [['quiz', 'student', 'child_profile']]

    def __str__(self):
        if self.child_profile:
            student_name = self.child_profile.full_name
        elif self.student:
            student_name = self.student.get_full_name()
        else:
            student_name = 'Course Student'
        return f"{self.quiz.title} → {student_name}"

    @property
    def is_overdue(self):
        if not self.due_date:
            return False
        return timezone.now() > self.due_date and self.status != 'completed'

    @property
    def attempt_count(self):
        return self.attempts.count()

    @property
    def best_attempt(self):
        return self.attempts.filter(
            submitted_at__isnull=False
        ).order_by('-score').first()

    @property
    def latest_attempt(self):
        return self.attempts.order_by('-started_at').first()

    @property
    def passed(self):
        best = self.best_attempt
        return best.passed if best else False


class QuizAttempt(models.Model):
    """Individual attempt at a quiz by a student."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    assignment = models.ForeignKey(
        QuizAssignment,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Answers (stored as JSON: {question_id: answer_id})
    answers_data = models.JSONField(
        default=dict,
        help_text="Student answers as {question_id: answer_id}"
    )

    # Results
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage score (0-100)"
    )
    passed = models.BooleanField(default=False)

    # Time tracking
    time_taken_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="How long student took (minutes)"
    )

    # Auto-save tracking
    last_autosave_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last auto-save operation"
    )

    class Meta:
        db_table = 'private_teaching_privatelessonquizattempt'
        verbose_name = 'Quiz Attempt'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['assignment', 'submitted_at'], name='private_tea_assignm_41378e_idx'),
        ]

    def __str__(self):
        status = "Graded" if self.submitted_at else "In Progress"
        return f"Attempt {self.started_at.strftime('%Y-%m-%d')} - {status}"

    @property
    def quiz(self):
        return self.assignment.quiz

    @property
    def student(self):
        return self.assignment.student

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    def autosave_answers(self, answers_data):
        self.answers_data = answers_data
        self.last_autosave_at = timezone.now()
        self.save(update_fields=['answers_data', 'last_autosave_at'])
        return True

    def calculate_score(self):
        """
        Calculate percentage score based on answers_data.
        Supports both single-answer and multi-answer questions.
        Returns: (earned_points, total_points, percentage)
        """
        quiz = self.quiz
        questions = quiz.get_questions()

        earned_points = 0
        total_points = 0

        for question in questions:
            total_points += question.points

            student_answer = self.answers_data.get(str(question.id))
            if not student_answer:
                continue

            if question.has_multiple_correct_answers():
                correct_answer_ids = set(str(a.id) for a in question.get_correct_answers())
                if isinstance(student_answer, list):
                    student_answer_ids = set(str(a) for a in student_answer)
                else:
                    student_answer_ids = {str(student_answer)}
                if student_answer_ids == correct_answer_ids:
                    earned_points += question.points
            else:
                correct_answer = question.get_correct_answer()
                if isinstance(student_answer, list):
                    student_answer_id = str(student_answer[0]) if student_answer else None
                else:
                    student_answer_id = str(student_answer)
                if correct_answer and str(correct_answer.id) == student_answer_id:
                    earned_points += question.points

        percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        return earned_points, total_points, Decimal(str(round(percentage, 2)))

    def grade(self):
        """Grade the attempt and save results."""
        earned_points, total_points, percentage = self.calculate_score()

        self.score = percentage
        self.passed = percentage >= self.assignment.quiz.pass_percentage
        self.submitted_at = timezone.now()

        if self.started_at:
            time_delta = timezone.now() - self.started_at
            self.time_taken_minutes = int(time_delta.total_seconds() / 60)

        self.save()

        self.assignment.status = 'completed'
        self.assignment.save()

        return {
            'earned_points': earned_points,
            'total_points': total_points,
            'percentage': float(percentage),
            'passed': self.passed,
            'pass_percentage': self.assignment.quiz.pass_percentage,
        }

    def get_detailed_results(self):
        """Get detailed results for each question."""
        quiz = self.quiz
        questions = quiz.get_questions()
        results = []

        for question in questions:
            student_answer_id = self.answers_data.get(str(question.id))
            correct_answer = question.get_correct_answer()

            student_answer = None
            if student_answer_id:
                student_answer = question.answers.filter(id=student_answer_id).first()

            is_correct = (
                student_answer is not None and
                correct_answer is not None and
                student_answer.id == correct_answer.id
            )

            results.append({
                'question': question,
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'answers': question.answers.order_by('order'),
            })

        return results
