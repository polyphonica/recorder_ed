"""
Course models for the recordered project.

This module contains all models related to:
- Course structure (Course, Topic, Lesson)
- Course content (LessonAttachment)
- Student progress (CourseEnrollment, LessonProgress)
- Quizzes (Quiz, QuizQuestion, QuizAnswer, QuizAttempt)
- Messaging (CourseMessage)
- Certificates (CourseCertificate)
"""

import uuid
import random
import string
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


# ============================================================================
# COURSE STRUCTURE MODELS
# ============================================================================

class Course(models.Model):
    """
    Main course model representing a complete course offering.
    Follows the pattern from workshops.models.Workshop.
    """

    GRADE_CHOICES = [
        ('N/A', 'N/A'),
        ('grade_1', 'Grade 1'),
        ('grade_2', 'Grade 2'),
        ('grade_3', 'Grade 3'),
        ('grade_4', 'Grade 4'),
        ('grade_5', 'Grade 5'),
        ('grade_6', 'Grade 6'),
        ('grade_7', 'Grade 7'),
        ('grade_8', 'Grade 8'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    # Primary key - UUID pattern from recordered
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core fields
    slug = models.SlugField(unique=True, max_length=255)
    title = models.CharField(max_length=200)
    grade = models.CharField(max_length=20, choices=GRADE_CHOICES, default='N/A')
    description = CKEditor5Field('description', config_name='default')

    # Pricing
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    # Media
    image = models.ImageField(upload_to='courses/images/', null=True, blank=True)
    preview_video_url = models.URLField(blank=True, help_text='YouTube or Vimeo URL for course preview')

    # Relationships
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='taught_courses',
        help_text='Course instructor/teacher'
    )

    # Status and visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False, help_text='Show on featured courses list')

    # Denormalized counts for performance (updated via signals or methods)
    total_topics = models.PositiveIntegerField(default=0)
    total_lessons = models.PositiveIntegerField(default=0)
    total_enrollments = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['grade', 'status']),
            models.Index(fields=['instructor', 'status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_grade_display()})"

    def save(self, *args, **kwargs):
        """Auto-generate slug from title if not provided"""
        if not self.slug:
            self.slug = slugify(self.title)

        # Set published_at timestamp when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the URL for this course's detail page"""
        return reverse('courses:detail', kwargs={'slug': self.slug})

    def is_owned_by(self, user):
        """Check if the course is owned/taught by the given user"""
        return self.instructor == user

    def get_first_lesson(self):
        """Get the first published lesson in the course"""
        first_topic = self.topics.filter(lessons__status='published').first()
        if first_topic:
            return first_topic.lessons.filter(status='published').first()
        return None

    @property
    def is_published(self):
        """Check if course is published"""
        return self.status == 'published'

    @property
    def has_quiz(self):
        """Check if any lesson in the course has a quiz"""
        return Quiz.objects.filter(lesson__topic__course=self).exists()


class Topic(models.Model):
    """
    Topics group lessons within a course.
    Example: "The Beat and Meter", "Pitch", "Rhythm", "Notation"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, related_name='topics', on_delete=models.CASCADE)

    topic_number = models.PositiveIntegerField(help_text='Order within the course (1, 2, 3...)')
    topic_title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text='Optional topic description')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['topic_number']
        unique_together = [['course', 'topic_number']]
        indexes = [
            models.Index(fields=['course', 'topic_number']),
        ]

    def __str__(self):
        return f"{self.course.title} - Topic {self.topic_number}: {self.topic_title}"

    def get_lessons_count(self):
        """Total number of lessons in this topic"""
        return self.lessons.count()

    def get_published_lessons_count(self):
        """Number of published lessons in this topic"""
        return self.lessons.filter(status='published').count()

    def is_completed(self, enrollment):
        """
        Check if all lessons in topic are completed for this enrollment.
        A lesson is considered complete when:
        1. The lesson is marked complete
        2. Any associated quiz is passed
        """
        published_lessons = self.lessons.filter(status='published')

        if not published_lessons.exists():
            return False

        for lesson in published_lessons:
            # Check lesson completion
            lesson_complete = LessonProgress.objects.filter(
                enrollment=enrollment,
                lesson=lesson,
                is_completed=True
            ).exists()

            # Check quiz completion if quiz exists
            if hasattr(lesson, 'quiz') and lesson.quiz.status == 'published':
                quiz_complete = QuizAttempt.objects.filter(
                    enrollment=enrollment,
                    quiz=lesson.quiz,
                    passed=True
                ).exists()
            else:
                quiz_complete = True  # No quiz required

            if not (lesson_complete and quiz_complete):
                return False

        return True


class Lesson(models.Model):
    """
    Individual lessons within a topic.
    Contains rich content, optional video, and optional quiz.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, related_name='lessons', on_delete=models.CASCADE)

    slug = models.SlugField(unique=True, max_length=255)
    lesson_number = models.PositiveIntegerField(help_text='Order within the topic')
    lesson_title = models.CharField(max_length=255)
    content = CKEditor5Field('content', config_name='default', help_text='Main lesson content')

    # Media
    video_url = models.URLField(
        blank=True,
        null=True,
        help_text='YouTube or Vimeo embed URL'
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text='Estimated time to complete (in minutes)'
    )

    # Access control
    is_preview = models.BooleanField(
        default=False,
        help_text='Allow non-enrolled users to preview this lesson'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['lesson_number']
        unique_together = [['topic', 'lesson_number']]
        indexes = [
            models.Index(fields=['topic', 'lesson_number']),
            models.Index(fields=['status']),
            models.Index(fields=['is_preview']),
        ]

    def __str__(self):
        return f"{self.topic.course.title} > {self.topic.topic_title} > Lesson {self.lesson_number}: {self.lesson_title}"

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided"""
        if not self.slug:
            base_slug = slugify(f"{self.topic.course.title}-{self.topic.topic_title}-{self.lesson_title}")
            # Ensure uniqueness
            original_slug = base_slug
            counter = 1
            while Lesson.objects.filter(slug=base_slug).exists():
                base_slug = f"{original_slug}-{counter}"
                counter += 1
            self.slug = base_slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the URL for this lesson's detail page"""
        return reverse('courses:lesson_detail', kwargs={
            'course_slug': self.topic.course.slug,
            'topic_number': self.topic.topic_number,
            'lesson_slug': self.slug
        })

    def get_next_lesson(self):
        """Get the next lesson in the course"""
        # Try next lesson in same topic
        next_in_topic = Lesson.objects.filter(
            topic=self.topic,
            lesson_number__gt=self.lesson_number,
            status='published'
        ).first()

        if next_in_topic:
            return next_in_topic

        # Try first lesson of next topic
        next_topic = Topic.objects.filter(
            course=self.topic.course,
            topic_number__gt=self.topic.topic_number
        ).first()

        if next_topic:
            return next_topic.lessons.filter(status='published').first()

        return None

    def get_previous_lesson(self):
        """Get the previous lesson in the course"""
        # Try previous lesson in same topic
        prev_in_topic = Lesson.objects.filter(
            topic=self.topic,
            lesson_number__lt=self.lesson_number,
            status='published'
        ).order_by('-lesson_number').first()

        if prev_in_topic:
            return prev_in_topic

        # Try last lesson of previous topic
        prev_topic = Topic.objects.filter(
            course=self.topic.course,
            topic_number__lt=self.topic.topic_number
        ).order_by('-topic_number').first()

        if prev_topic:
            return prev_topic.lessons.filter(status='published').order_by('-lesson_number').first()

        return None


class LessonAttachment(models.Model):
    """
    File attachments for lessons (PDFs, documents, audio files, etc.)
    """

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('doc', 'Document'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attachments')

    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='courses/documents/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.lesson.lesson_title} - {self.title}"

    @property
    def file_size(self):
        """Get human-readable file size"""
        if self.file:
            size = self.file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
        return "0 B"


# ============================================================================
# ENROLLMENT & PROGRESS TRACKING MODELS
# ============================================================================

class CourseEnrollment(models.Model):
    """
    Tracks student enrollment in courses.
    Created after successful payment or manual enrollment.

    Supports both adult students and children (under 18).
    - For adults: student field is populated, child_profile is None
    - For children: student field = guardian, child_profile = child
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_enrollments',
        help_text="For adults: the student. For children: the guardian/parent."
    )

    # Child profile (for students under 18)
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.CASCADE,
        related_name='course_enrollments',
        null=True,
        blank=True,
        help_text="If enrolling a child, link to their child profile"
    )

    # Enrollment status
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Payment reference - links to recordered's payment system
    # TODO: Add back when implementing course payments
    # order = models.ForeignKey(
    #     'payments.Order',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='course_enrollments'
    # )

    class Meta:
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['student', 'is_active']),
            models.Index(fields=['course', 'is_active']),
            models.Index(fields=['child_profile', 'is_active']),
        ]

    def __str__(self):
        if self.child_profile:
            return f"{self.child_profile.full_name} (Guardian: {self.student.get_full_name() or self.student.username}) - {self.course.title}"
        else:
            student_name = self.student.get_full_name() or self.student.username
            return f"{student_name} - {self.course.title}"

    @property
    def student_name(self):
        """Return the name of the actual student (child or adult)"""
        if self.child_profile:
            return self.child_profile.full_name
        return self.student.get_full_name() or self.student.username

    @property
    def guardian(self):
        """Return guardian user if this is a child enrollment, None otherwise"""
        return self.student if self.child_profile else None

    @property
    def is_child_enrollment(self):
        """Check if this is an enrollment for a child (under 18)"""
        return self.child_profile is not None

    @property
    def progress_percentage(self):
        """Calculate overall course completion percentage"""
        total_lessons = Lesson.objects.filter(
            topic__course=self.course,
            status='published'
        ).count()

        if total_lessons == 0:
            return 0

        completed_lessons = LessonProgress.objects.filter(
            enrollment=self,
            is_completed=True,
            lesson__status='published'
        ).count()

        return int((completed_lessons / total_lessons) * 100)

    @property
    def is_completed(self):
        """Check if course is 100% complete"""
        return self.completed_at is not None or self.progress_percentage == 100

    def check_and_mark_complete(self):
        """
        Check if all lessons and quizzes are complete.
        If yes, mark course as complete and create certificate.
        Returns True if marked complete, False otherwise.
        """
        if self.completed_at:
            return True  # Already complete

        # Check all topics
        for topic in self.course.topics.all():
            if not topic.is_completed(self):
                return False

        # All topics complete - mark course complete
        self.completed_at = timezone.now()
        self.save()

        # Create certificate
        CourseCertificate.objects.get_or_create(enrollment=self)

        return True


class LessonProgress(models.Model):
    """
    Tracks individual lesson progress for each enrollment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')

    # Progress tracking
    is_completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['enrollment', 'lesson']]
        ordering = ['lesson__topic__topic_number', 'lesson__lesson_number']
        verbose_name_plural = 'Lesson progress records'
        indexes = [
            models.Index(fields=['enrollment', 'is_completed']),
        ]

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        student_name = self.enrollment.student.get_full_name() or self.enrollment.student.username
        return f"{status} {student_name} - {self.lesson.lesson_title}"

    def mark_complete(self):
        """Mark this lesson as complete"""
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            if not self.started_at:
                self.started_at = timezone.now()
            self.save()

            # Check if course is now complete
            self.enrollment.check_and_mark_complete()


# ============================================================================
# QUIZ MODELS
# ============================================================================

class Quiz(models.Model):
    """
    Quiz associated with a lesson (one-to-one relationship).
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz')

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_percentage = models.PositiveIntegerField(
        default=70,
        help_text='Minimum percentage required to pass (0-100)'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return f"Quiz: {self.lesson.lesson_title}"

    def get_questions(self):
        """Get all questions ordered by order field"""
        return self.questions.all().order_by('order')

    @property
    def total_points(self):
        """Calculate total possible points"""
        return sum(q.points for q in self.questions.all())


class QuizQuestion(models.Model):
    """
    Individual question within a quiz.
    Uses CKEditor for rich content (images, formatting, etc.)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')

    text = CKEditor5Field('question', config_name='default')
    order = models.PositiveIntegerField(default=0, help_text='Display order')
    points = models.PositiveIntegerField(default=1, help_text='Points for correct answer')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        # Strip HTML tags for display
        from django.utils.html import strip_tags
        text = strip_tags(self.text)
        return text[:75] + '...' if len(text) > 75 else text

    def get_answers(self):
        """Get all answers ordered by order field"""
        return self.answers.all().order_by('order')

    def get_correct_answer(self):
        """Get the correct answer for this question"""
        return self.answers.filter(is_correct=True).first()


class QuizAnswer(models.Model):
    """
    Multiple choice answer for a quiz question.
    Only one answer should be marked as correct per question.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answers')

    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        correct_marker = " ✓" if self.is_correct else ""
        return f"{self.text}{correct_marker}"


class QuizAttempt(models.Model):
    """
    Records each attempt a student makes at a quiz.
    Students can retake quizzes unlimited times.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Score as a percentage (0-100)'
    )
    passed = models.BooleanField(default=False)

    # Store student's answers as JSON: {question_id: answer_id}
    answers_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['enrollment', 'quiz']),
            models.Index(fields=['quiz', 'passed']),
        ]

    def __str__(self):
        student_name = self.enrollment.student.get_full_name() or self.enrollment.student.username
        status = "✓" if self.passed else "✗"
        return f"{status} {student_name} - {self.quiz.title} ({self.score}%)"

    def calculate_score(self):
        """
        Calculate score based on answers_data.
        Returns percentage score.
        """
        if not self.answers_data:
            return 0

        total_points = 0
        earned_points = 0

        for question in self.quiz.questions.all():
            total_points += question.points

            # Get student's answer
            student_answer_id = self.answers_data.get(str(question.id))
            if student_answer_id:
                try:
                    answer = QuizAnswer.objects.get(id=student_answer_id)
                    if answer.is_correct:
                        earned_points += question.points
                except QuizAnswer.DoesNotExist:
                    pass

        if total_points == 0:
            return 0

        percentage = (earned_points / total_points) * 100
        return round(percentage, 2)

    def grade(self):
        """
        Grade the quiz attempt and update score and passed status.
        """
        self.score = self.calculate_score()
        self.passed = self.score >= self.quiz.pass_percentage
        self.submitted_at = timezone.now()
        self.save()

        return {
            'score': self.score,
            'passed': self.passed,
            'pass_percentage': self.quiz.pass_percentage
        }


# ============================================================================
# MESSAGING MODELS
# ============================================================================

class CourseMessage(models.Model):
    """
    Messaging system for students to contact instructors about courses/lessons.
    """

    CATEGORY_CHOICES = [
        ('content_question', '📚 Content Question'),
        ('technical_issue', '🐛 Technical Issue'),
        ('content_error', '✏️ Content Error/Typo'),
        ('suggestion', '💡 Suggestion'),
        ('other', '❓ Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_course_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_course_messages'
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='messages')
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        help_text='Optional: specific lesson this message is about'
    )

    subject = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        help_text='Type of message'
    )

    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Threading support for conversations
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['recipient', 'read_at']),
            models.Index(fields=['course', 'sent_at']),
        ]

    def __str__(self):
        sender_name = self.sender.get_full_name() or self.sender.username
        recipient_name = self.recipient.get_full_name() or self.recipient.username
        return f"From {sender_name} to {recipient_name}: {self.subject}"

    @property
    def is_read(self):
        """Check if message has been read"""
        return self.read_at is not None

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.read_at = timezone.now()
            self.save()


# ============================================================================
# CERTIFICATE MODELS
# ============================================================================

class CourseCertificate(models.Model):
    """
    Certificate of completion for a course.
    Generated automatically when student completes all requirements.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.OneToOneField(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name='certificate'
    )

    certificate_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(
        upload_to='certificates/',
        null=True,
        blank=True,
        help_text='Pre-generated PDF certificate (optional)'
    )

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        student_name = self.enrollment.student.get_full_name() or self.enrollment.student.username
        return f"Certificate {self.certificate_number} - {student_name}"

    def save(self, *args, **kwargs):
        """Auto-generate certificate number if not provided"""
        if not self.certificate_number:
            # Format: GRADE-XXXXXX (e.g., GRADE1-123456)
            grade = self.enrollment.course.grade.replace(' ', '').replace('/', '')
            random_suffix = ''.join(random.choices(string.digits, k=6))
            self.certificate_number = f"{grade}-{random_suffix}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return URL to view/download certificate"""
        return reverse('courses:certificate_view', kwargs={'certificate_id': self.id})
