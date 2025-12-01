from django.urls import reverse
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.conf import settings
from django.contrib.auth import get_user_model

# Import models from other apps
from apps.private_teaching.models import Subject, LessonRequest

import uuid

User = get_user_model()


class Lesson(models.Model):
    ONLINE = 'Online'
    ONSITE = 'Onsite'
    ATTENDED = 'Attended'
    NOSHOW = 'No-show'
    LEGALCANCEL = 'Legal-Cancel'
    ILLEGALCANCEL = 'Illegal-Cancel'
    
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
    status = [
        ('Draft', 'Draft'),
        ('Assigned', 'Assigned'),
    ]
    approved_status = [
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Pending', 'Pending'),
    ]
    DURATION = [
        ('30', '30'),
        ('60', '60'),
        ('90', '90'),
    ]
    PAYMENT_STATUS = (
        ('Not Paid', 'Not Paid'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Payment In Process', 'Payment In Process')
    )
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)

    # Relationships
    lesson_request = models.ForeignKey(
        LessonRequest,
        on_delete=models.CASCADE,
        related_name='lessons',
        help_text="The lesson request this lesson belongs to"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
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
    status = models.CharField(max_length=20, choices=status, default='Draft')
    approved_status = models.CharField(max_length=20, choices=approved_status, default='Pending')
    payment_status = models.CharField(
        choices=PAYMENT_STATUS, max_length=20, default='Not Paid')
    in_cart = models.BooleanField(default=False)
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag for rejected lessons"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Playalong pieces
    pieces = models.ManyToManyField(
        'audioplayer.Piece',
        through='PrivateLessonPiece',
        related_name='private_lessons',
        blank=True,
        help_text='Interactive playalong pieces for this lesson'
    )

    # Exam preparation link
    exam_registration = models.ForeignKey(
        'private_teaching.ExamRegistration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preparation_lessons',
        help_text='Link to exam if this lesson is for exam preparation'
    )

    class Meta:
        ordering = ["-lesson_date"]

    def __str__(self):
        return f"{self.subject.subject} - {self.lesson_date}"

    @property
    def price(self):
        """Get the lesson price"""
        return self.fee or 0

    @property
    def calendar_color(self):
        """Return color code for calendar display based on lesson status"""
        if self.status == 'Assigned':
            return '#1e40af'  # Dark blue for assigned
        elif self.payment_status == 'Paid':
            return '#3b82f6'  # Blue for paid
        elif self.approved_status == 'Accepted':
            return '#10b981'  # Green for accepted but not paid
        elif self.approved_status == 'Rejected':
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
        return f"{self.piece.title} for {self.lesson}"


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


# Keep the LessonOrder model for backward compatibility with existing payment system
class LessonOrder(models.Model):
    PAYMENT_STATUS = (
        ('NONE', 'NONE'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Payment In Process', 'Payment In Process')
    )
    # Will need to reference student profile from private_teaching app
    # student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lessons = models.ManyToManyField(Lesson)
    payment_status = models.CharField(
        choices=PAYMENT_STATUS, max_length=20, default='NONE')
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
