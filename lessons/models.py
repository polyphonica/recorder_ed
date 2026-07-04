from django.urls import reverse
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.conf import settings
from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords

import uuid

User = get_user_model()


class Lesson(models.Model):
    ONLINE = 'Online'
    ONSITE = 'Onsite'
    ATTENDED = 'Attended'
    NOSHOW = 'No-show'
    LEGALCANCEL = 'Legal-Cancel'
    ILLEGALCANCEL = 'Illegal-Cancel'

    class Status(models.TextChoices):
        DRAFT    = 'Draft',    'Draft'
        ASSIGNED = 'Assigned', 'Assigned'

    class ApprovalStatus(models.TextChoices):
        ACCEPTED = 'Accepted', 'Accepted'
        REJECTED = 'Rejected', 'Rejected'
        PENDING  = 'Pending',  'Pending'

    Location = [
        (ONLINE, 'Online'),
        (ONSITE, 'Onsite'),
    ]
    Attendance = [
        (ATTENDED, 'Attended'),
        (NOSHOW, 'No-show'),
        (LEGALCANCEL, 'Legal-Cancel'),
        (ILLEGALCANCEL, 'Illegal-Cancel'),
    ]
    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = 'not_required', 'Not Required'
        PENDING      = 'pending',      'Pending Payment'
        COMPLETED    = 'completed',    'Payment Completed'
        FAILED       = 'failed',       'Payment Failed'

    DURATION = [
        ('30', '30'),
        ('60', '60'),
        ('90', '90'),
    ]
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)

    # Relationships
    lesson_request = models.ForeignKey(
        'private_teaching.LessonRequest',
        on_delete=models.CASCADE,
        related_name='lessons',
        help_text="The lesson request this lesson belongs to"
    )
    subject = models.ForeignKey('private_teaching.Subject', on_delete=models.CASCADE)
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_lessons',
        help_text="Student taking this lesson"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_lessons',
        help_text="Teacher giving this lesson (auto-populated from subject)"
    )
    
    # Lesson details
    duration_in_minutes = models.CharField(choices=DURATION, max_length=7, default="60")
    lesson_date = models.DateField()
    lesson_time = models.TimeField()
    fee = models.FloatField(null=True, blank=True, help_text="Calculated lesson price")
    
    # Lesson settings
    location = models.CharField(max_length=20, choices=Location, default='Online')
    attendance = models.CharField(max_length=20, choices=Attendance, default='Attended')
    zoom_link = models.URLField(
        blank=True,
        default='',
        help_text="Zoom meeting link for online lessons"
    )
    
    # Lesson content
    lesson_content = CKEditor5Field(config_name='default', null=True, blank=True)
    teacher_notes = models.TextField(null=True, blank=True)
    homework = models.TextField(null=True, blank=True)
    private_note = models.TextField(
        null=True, 
        blank=True,
        help_text="Private notes not visible to students"
    )
    
    # Status fields
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    approved_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    payment_status = models.CharField(
        choices=PaymentStatus.choices, max_length=20, default=PaymentStatus.PENDING)
    in_cart = models.BooleanField(default=False)
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag for rejected lessons"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    # Playalong pieces
    pieces = models.ManyToManyField(
        'audioplayer.Piece',
        through='PrivateLessonPiece',
        related_name='private_lessons',
        blank=True,
        help_text='Interactive playalong pieces for this lesson'
    )

    # Homework assignments
    assignments = models.ManyToManyField(
        'assignments.Assignment',
        through='LessonAssignment',
        related_name='lessons',
        blank=True,
        help_text='Homework assignments for this lesson'
    )

    # Exam preparation link
    exam_registration = models.ForeignKey(
        'exams.ExamRegistration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preparation_lessons',
        help_text='Link to exam if this lesson is for exam preparation'
    )

    class Meta:
        ordering = ["-lesson_date"]
        indexes = [
            # Teacher schedule queries - most common pattern
            models.Index(
                fields=['teacher', 'lesson_date', 'is_deleted'],
                name='lesson_teacher_schedule_idx'
            ),
            # Payment filtering queries
            models.Index(
                fields=['payment_status', 'approved_status'],
                name='lesson_payment_status_idx'
            ),
            # Calendar date/time queries
            models.Index(
                fields=['lesson_date', 'lesson_time'],
                name='lesson_datetime_idx'
            ),
            # Student lesson queries
            models.Index(
                fields=['student', 'is_deleted', 'lesson_date'],
                name='lesson_student_schedule_idx'
            ),
        ]

    def __str__(self):
        return f"{self.subject.subject} - {self.lesson_date}"

    @property
    def price(self):
        """Get the lesson price"""
        return self.fee or 0

    @property
    def calendar_color(self):
        """Return color code for calendar display based on lesson status"""
        if self.status == Lesson.Status.ASSIGNED:
            return '#1e40af'  # Dark blue for assigned
        elif self.payment_status == Lesson.PaymentStatus.COMPLETED:
            return '#3b82f6'  # Blue for paid
        elif self.approved_status == Lesson.ApprovalStatus.ACCEPTED:
            return '#10b981'  # Green for accepted but not paid
        elif self.approved_status == Lesson.ApprovalStatus.REJECTED:
            return '#ef4444'  # Red for rejected
        else:
            return '#f59e0b'  # Yellow/orange for pending

    @property
    def get_student_url(self):
        url = reverse('teacher:student_update', args=(self.student.pk,))
        return url

    @property
    def get_teacher_lesson_url(self):
        url = reverse('lessons:lesson_update', args=(self.id,))
        return url

    @property
    def get_student_my_lessons_url(self):
        url = reverse('lessons:lesson_list')
        return url

    @property
    def get_student_my_lessons_detail_url(self):
        url = reverse('lessons:lesson_detail', args=(self.id,))
        return url

    def calculate_fee(self):
        """Calculate fee based on subject base price and duration"""
        if self.subject and self.duration_in_minutes:
            base_price = float(self.subject.base_price_60min)
            duration = int(self.duration_in_minutes)
            self.fee = (base_price / 60) * duration
        return self.fee

    def save(self, *args, **kwargs):
        # Auto-populate teacher from subject
        if self.subject and not self.teacher_id:
            self.teacher = self.subject.teacher

        # Auto-populate zoom link from teacher's default for online lessons
        try:
            if (self.location == self.ONLINE and
                self.teacher and
                hasattr(self.teacher, 'profile')):

                teacher_default_link = self.teacher.profile.default_zoom_link

                # Only auto-populate if:
                # 1. Teacher has a default zoom link set, AND
                # 2. This lesson's zoom link is empty
                if teacher_default_link and not self.zoom_link:
                    self.zoom_link = teacher_default_link

        except Exception as e:
            # Log error but don't prevent save
            print(f"Error auto-populating zoom link: {e}")

        # Auto-calculate fee if not set
        if not self.fee:
            self.calculate_fee()

        super().save(*args, **kwargs)


class PrivateLessonPiece(models.Model):
    """Through model for associating playalong pieces with private lessons"""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='lesson_pieces',
        help_text="The lesson this piece is assigned to"
    )
    piece = models.ForeignKey(
        'audioplayer.Piece',
        on_delete=models.CASCADE,
        related_name='private_lesson_assignments',
        help_text="The playalong piece"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the lesson"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Whether students can see this piece"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Lesson-specific instructions for this piece"
    )
    is_optional = models.BooleanField(
        default=False,
        help_text="Whether this piece is optional practice"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Lesson Piece'
        verbose_name_plural = 'Lesson Pieces'
        unique_together = ['lesson', 'piece']

    def __str__(self):
        return f"{self.lesson} - {self.piece.title}"


class PrivateLessonCollection(models.Model):
    """
    Through model for associating piece collections with private lessons.
    Assigning a collection gives the student access to all pieces within it.
    """
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='lesson_collections',
        help_text="The lesson this collection is assigned to"
    )
    collection = models.ForeignKey(
        'audioplayer.PieceCollection',
        on_delete=models.CASCADE,
        related_name='private_lesson_assignments',
        help_text="The piece collection"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the lesson"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Whether students can see this collection"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Lesson-specific instructions for this collection"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Lesson Collection'
        verbose_name_plural = 'Lesson Collections'
        unique_together = ['lesson', 'collection']

    def __str__(self):
        return f"{self.lesson} - {self.collection.title}"


class LessonAssignment(models.Model):
    """
    Links homework assignments to lessons or directly to students (standalone).
    Replaces PrivateLessonAssignment as the single canonical assignment-link model.
    Lesson-linked: lesson is set, student/teacher derived from lesson.
    Standalone: lesson is null, student/teacher/child_profile set explicitly.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='lesson_assignments',
        null=True,
        blank=True,
        help_text="The lesson this assignment is homework for (null for standalone)"
    )
    assignment = models.ForeignKey(
        'assignments.Assignment',
        on_delete=models.CASCADE,
        related_name='lesson_assignments',
        help_text="The homework assignment"
    )
    # For standalone assignments (lesson=null): explicit student/teacher/child_profile
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='standalone_assignments_received',
        help_text="Student (standalone only; lesson-linked derive from lesson.student)"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='standalone_assignments_given',
        help_text="Teacher (standalone only; lesson-linked derive from lesson.subject.teacher)"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_assignments_received',
        help_text="Optional: specific child this assignment is for"
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this assignment is due (defaults to next lesson)"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within homework list"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Lesson-specific instructions for this assignment"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'assigned_at']
        verbose_name = 'Lesson Assignment'
        verbose_name_plural = 'Lesson Assignments'
        constraints = [
            models.UniqueConstraint(
                fields=['lesson', 'assignment'],
                condition=models.Q(lesson__isnull=False),
                name='unique_lesson_assignment_per_lesson'
            )
        ]

    def __str__(self):
        student = self.effective_student
        student_name = (student.get_full_name() or student.username) if student else 'Unknown'
        lesson_info = f" (Lesson: {self.lesson.lesson_date})" if self.lesson else " (Standalone)"
        return f"{self.assignment.title} → {student_name}{lesson_info}"

    @property
    def effective_student(self):
        """Student for this assignment — explicit for standalone, derived for lesson-linked"""
        return self.student if self.student_id else (self.lesson.student if self.lesson_id else None)

    @property
    def effective_teacher(self):
        """Teacher for this assignment — explicit for standalone, derived for lesson-linked"""
        return self.teacher if self.teacher_id else (self.lesson.subject.teacher if self.lesson_id else None)

    @property
    def submission(self):
        """Get the submission for this assignment (if exists)"""
        from assignments.models import AssignmentSubmission
        student = self.effective_student
        if not student:
            return None
        try:
            return AssignmentSubmission.objects.get(student=student, assignment=self.assignment)
        except AssignmentSubmission.DoesNotExist:
            return None

    @property
    def is_submitted(self):
        """Check if student has submitted"""
        sub = self.submission
        return sub is not None and sub.status in ['submitted', 'graded']

    @property
    def is_graded(self):
        """Check if submission is graded"""
        sub = self.submission
        return sub is not None and sub.status == 'graded'

    @property
    def is_overdue(self):
        """Check if the assignment is overdue"""
        if not self.due_date:
            return False
        from django.utils import timezone
        return timezone.now() > self.due_date and not self.is_submitted


class Document(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=100)
    document = models.FileField(upload_to='lesson_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.lesson}"


class LessonAttachedUrl(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StandaloneDocument(models.Model):
    """
    A document shared directly by a teacher without being tied to a lesson.
    Useful for resources like manuscript paper that all students should access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='standalone_documents'
    )
    title = models.CharField(max_length=200)
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional note, e.g. 'Treble clef — 8 staves per page'"
    )
    document = models.FileField(upload_to='standalone_documents/')
    share_with_all_students = models.BooleanField(
        default=True,
        help_text="Make available to all current students"
    )
    shared_with_students = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_standalone_documents',
        help_text="Specific students to share with (only used when not sharing with all)"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='standalone_documents',
        help_text="The specific child this resource is for (its primary target), when shared with a child student"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} (by {self.teacher.get_full_name() or self.teacher.username})"


class StandaloneUrl(models.Model):
    """
    A URL shared directly by a teacher without being tied to a lesson.
    Useful for sharing video links, reference pages, or any web resource.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='standalone_urls'
    )
    name = models.CharField(max_length=200)
    url = models.URLField()
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional note, e.g. 'Warm-up exercises — start at 2:30'"
    )
    share_with_all_students = models.BooleanField(
        default=True,
        help_text="Make available to all current students"
    )
    shared_with_students = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_standalone_urls',
        help_text="Specific students to share with (only used when not sharing with all)"
    )
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='standalone_urls',
        help_text="The specific child this resource is for (its primary target), when shared with a child student"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (by {self.teacher.get_full_name() or self.teacher.username})"


# Keep the LessonOrder model for backward compatibility with existing payment system
class LessonOrder(models.Model):
    # Will need to reference student profile from private_teaching app
    # student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lessons = models.ManyToManyField(Lesson)
    payment_status = models.CharField(
        choices=Lesson.PaymentStatus.choices, max_length=20, default=Lesson.PaymentStatus.NOT_REQUIRED)
    transaction_id = models.CharField(max_length=100, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} | {self.payment_status}"

    @property
    def get_total(self):
        total = 0
        total_lessons = self.lessons.all()
        for lesson in total_lessons:
            total += lesson.fee or 0
        return total

    class Meta:
        ordering = ["-created"]
