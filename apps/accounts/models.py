from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Personal Information
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Address Information
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Profile Image
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # Role flags
    is_student = models.BooleanField(default=True, help_text="Students can enroll in courses, workshops, and request private lessons")
    is_teacher = models.BooleanField(default=False, help_text="Teachers can create courses, workshops, and offer private lessons")
    is_private_teacher = models.BooleanField(default=False, help_text="Designates if this user can access private teaching teacher features")
    is_guardian = models.BooleanField(default=False, help_text="Guardian/parent managing child profiles (under 18)")
    
    # Teacher/Instructor Information (unified across all domains)
    bio = models.TextField(blank=True, help_text="Teacher biography displayed on profile")
    website = models.URLField(blank=True, help_text="Teacher's personal or professional website")
    teaching_experience = models.TextField(blank=True, help_text="Teaching experience and qualifications")
    specializations = models.TextField(blank=True, help_text="Musical specializations and expertise")
    default_zoom_link = models.URLField(blank=True, help_text="Default Zoom link for online lessons")

    # Private teaching capacity management
    max_private_students = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of private teaching students this teacher can accept"
    )
    accepting_new_private_students = models.BooleanField(
        default=True,
        help_text="Whether this teacher is currently accepting new private teaching students"
    )

    # Profile completion tracking
    profile_completed = models.BooleanField(default=False)

    # Notification preferences
    email_on_new_message = models.BooleanField(
        default=True,
        help_text="Send email notification when you receive a new message"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.user.username
    
    @property
    def display_name(self):
        return self.full_name or self.user.email
    
    def get_profile_image_url(self):
        if self.profile_image:
            return self.profile_image.url
        # Return default avatar URL
        return '/static/images/default-avatar.svg'


class ChildProfile(models.Model):
    """
    Profile for students under 18.
    Linked to guardian (parent) account.
    Guardian manages all enrollments, payments, and communications.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guardian = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='children',
        help_text="Parent/guardian who manages this child's account"
    )

    # Child Information
    first_name = models.CharField(max_length=100, help_text="Child's first name")
    last_name = models.CharField(max_length=100, help_text="Child's last name (needed for exam registration)")
    date_of_birth = models.DateField(help_text="Child's date of birth for age calculation")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Child Profile'
        verbose_name_plural = 'Child Profiles'

    def __str__(self):
        return f"{self.full_name} (Guardian: {self.guardian.get_full_name() or self.guardian.username})"

    @property
    def full_name(self):
        """Return child's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        """Calculate current age from date of birth"""
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def is_adult(self):
        """Check if child has turned 18 (eligible for account transfer)"""
        return self.age >= 18

    def can_transfer_account(self):
        """
        Check if this child profile can be transferred to an independent account.
        Only allowed when child turns 18.
        """
        return self.is_adult


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()