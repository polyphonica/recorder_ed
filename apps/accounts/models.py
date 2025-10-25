from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
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
    
    # Guardian Information (for under 18 students)
    under_eighteen = models.BooleanField(default=False)
    guardian_first_name = models.CharField(max_length=100, blank=True)
    guardian_last_name = models.CharField(max_length=100, blank=True)
    guardian_email = models.EmailField(blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    
    # Role flags 
    is_student = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_private_teacher = models.BooleanField(default=False, help_text="Designates if this user can access private teaching teacher features")
    
    # Teacher/Instructor Information (unified across all domains)
    bio = models.TextField(blank=True, help_text="Teacher biography displayed on profile")
    website = models.URLField(blank=True, help_text="Teacher's personal or professional website")
    teaching_experience = models.TextField(blank=True, help_text="Teaching experience and qualifications")
    specializations = models.TextField(blank=True, help_text="Musical specializations and expertise")
    default_zoom_link = models.URLField(blank=True, help_text="Default Zoom link for online lessons")
    
    # Profile completion tracking
    profile_completed = models.BooleanField(default=False)
    
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

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()