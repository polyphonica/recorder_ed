from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q
from .models import (
    WorkshopCategory, Workshop, WorkshopSession,
    WorkshopRegistration, WorkshopMaterial, WorkshopInterest, UserProfile,
    WorkshopCartItem
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email']
    fields = ['user', 'bio', 'website']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    def get_readonly_fields(self, request, obj=None):
        # Make fields read-only with helpful message
        if obj:  # Editing an existing object
            return ['user']
        return []


# Extend the default User admin to show workshop-specific profile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Workshop Profile (Legacy - Bio/Website only)'
    fields = ['bio', 'website']
    classes = ['collapse']  # Collapsed by default


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    # Teacher status is now managed via accounts.UserProfile.is_teacher
    # No need to show instructor_status here anymore

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(WorkshopCategory)
class WorkshopCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'color', 'workshop_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def workshop_count(self, obj):
        return obj.workshop_set.count()
    workshop_count.short_description = 'Workshops'


class WorkshopSessionInline(admin.TabularInline):
    model = WorkshopSession
    extra = 1
    fields = ['start_datetime', 'end_datetime', 'max_participants', 'current_registrations', 'is_active']
    readonly_fields = ['current_registrations']


class WorkshopMaterialInline(admin.TabularInline):
    model = WorkshopMaterial
    extra = 1
    fields = ['title', 'material_type', 'access_timing', 'session', 'file', 'order', 'is_featured']
    readonly_fields = []
    
    def get_queryset(self, request):
        # Show only workshop-level materials in the workshop admin
        qs = super().get_queryset(request)
        return qs.filter(session__isnull=True)


class InstructorChoiceField(forms.ModelChoiceField):
    """Custom choice field that displays full name for instructors"""
    
    def label_from_instance(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name} ({obj.username})"
        elif obj.first_name or obj.last_name:
            return f"{obj.first_name}{obj.last_name} ({obj.username})"
        else:
            return obj.username


class WorkshopAdminForm(forms.ModelForm):
    """Custom form for Workshop admin with better instructor selection"""
    
    instructor = InstructorChoiceField(
        queryset=User.objects.all().order_by('first_name', 'last_name', 'username'),
        required=True,
        empty_label="Select an instructor...",
        help_text="Choose an instructor for this workshop"
    )
    
    class Meta:
        model = Workshop
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to show users with teacher status (from accounts.UserProfile.is_teacher)
        # or existing workshop instructors
        instructors = User.objects.filter(
            Q(profile__is_teacher=True) |
            Q(workshops__isnull=False)
        ).distinct().order_by('first_name', 'last_name', 'username')

        self.fields['instructor'].queryset = instructors


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    form = WorkshopAdminForm
    list_display = [
        'title', 'instructor_name', 'category', 'delivery_method', 'status', 'difficulty_level',
        'price_display', 'session_count', 'registration_count', 'is_featured'
    ]
    list_filter = [
        'status', 'delivery_method', 'difficulty_level', 'category', 'is_featured', 
        'is_free', 'created_at', 'instructor'
    ]
    search_fields = [
        'title', 'description', 'instructor__username', 'instructor__email',
        'instructor__first_name', 'instructor__last_name'
    ]
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'instructor', 'category', 'status')
        }),
        ('Content', {
            'fields': ('description', 'short_description', 'learning_objectives', 
                      'prerequisites', 'materials_needed')
        }),
        ('Classification', {
            'fields': ('difficulty_level', ('duration_value', 'duration_unit'), 'tags')
        }),
        ('Media', {
            'fields': ('featured_image', 'promo_video_url')
        }),
        ('Delivery Method and Venue', {
            'fields': (
                'delivery_method',
                ('venue_name', 'venue_city'),
                'venue_address',
                ('venue_postcode', 'venue_map_link'),
                'venue_notes',
                'max_venue_capacity'
            ),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('is_free', 'price')
        }),
        ('Publishing', {
            'fields': ('is_featured', 'published_at')
        }),
    )
    
    inlines = [WorkshopSessionInline, WorkshopMaterialInline]
    
    def price_display(self, obj):
        if obj.is_free:
            return format_html('<span style="color: green;">Free</span>')
        return f"£{obj.price}"
    price_display.short_description = 'Price'
    
    def session_count(self, obj):
        upcoming = obj.sessions.filter(start_datetime__gte=timezone.now()).count()
        total = obj.sessions.count()
        return f"{upcoming}/{total}"
    session_count.short_description = 'Sessions (Upcoming/Total)'
    
    def registration_count(self, obj):
        return obj.total_registrations
    registration_count.short_description = 'Registrations'
    
    def instructor_name(self, obj):
        """Display instructor full name in admin list"""
        if obj.instructor.first_name and obj.instructor.last_name:
            return f"{obj.instructor.first_name} {obj.instructor.last_name}"
        elif obj.instructor.first_name or obj.instructor.last_name:
            return f"{obj.instructor.first_name}{obj.instructor.last_name}"
        else:
            return obj.instructor.username
    instructor_name.short_description = 'Instructor'
    instructor_name.admin_order_field = 'instructor__first_name'


class SessionMaterialInline(admin.TabularInline):
    model = WorkshopMaterial
    extra = 1
    fields = ['title', 'material_type', 'access_timing', 'file', 'external_url', 'order']
    verbose_name = "Session Material"
    verbose_name_plural = "Session Materials"
    
    def get_queryset(self, request):
        # Only show materials specific to this session
        qs = super().get_queryset(request)
        return qs.filter(session__isnull=False)


@admin.register(WorkshopSession)
class WorkshopSessionAdmin(admin.ModelAdmin):
    list_display = [
        'workshop', 'start_datetime', 'capacity_display', 
        'registration_count', 'status_display', 'is_active'
    ]
    list_filter = [
        'workshop__category', 'start_datetime', 'is_active', 
        'is_cancelled', 'workshop__instructor'
    ]
    search_fields = ['workshop__title', 'session_notes']
    
    fieldsets = (
        ('Workshop', {
            'fields': ('workshop',)
        }),
        ('Schedule', {
            'fields': ('start_datetime', 'end_datetime', 'timezone_name')
        }),
        ('Capacity', {
            'fields': ('max_participants', 'current_registrations', 'waitlist_enabled')
        }),
        ('Meeting Details', {
            'fields': ('meeting_url', 'meeting_id', 'meeting_password', 'session_notes')
        }),
        ('Status', {
            'fields': ('is_active', 'is_cancelled', 'cancellation_reason')
        }),
        ('Recording', {
            'fields': ('recording_url', 'recording_available_until')
        }),
    )
    
    readonly_fields = ['current_registrations']
    inlines = [SessionMaterialInline]
    
    def capacity_display(self, obj):
        percentage = (obj.current_registrations / obj.max_participants) * 100 if obj.max_participants > 0 else 0
        color = 'red' if percentage >= 100 else 'orange' if percentage >= 80 else 'green'
        return format_html(
            '<span style="color: {}">{}/{}</span>',
            color, obj.current_registrations, obj.max_participants
        )
    capacity_display.short_description = 'Capacity'
    
    def registration_count(self, obj):
        registered = obj.registrations.filter(status='registered').count()
        waitlisted = obj.registrations.filter(status='waitlisted').count()
        if waitlisted > 0:
            return f"{registered} (+{waitlisted} waitlisted)"
        return str(registered)
    registration_count.short_description = 'Registrations'
    
    def status_display(self, obj):
        if obj.is_cancelled:
            return format_html('<span style="color: red;">Cancelled</span>')
        elif obj.is_past:
            return format_html('<span style="color: gray;">Past</span>')
        elif obj.is_ongoing:
            return format_html('<span style="color: blue;">Live</span>')
        elif obj.is_upcoming:
            return format_html('<span style="color: green;">Upcoming</span>')
        return 'Unknown'
    status_display.short_description = 'Status'


@admin.register(WorkshopRegistration)
class WorkshopRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'student_name', 'workshop_title', 'session_date', 
        'status', 'registration_date', 'attended'
    ]
    list_filter = [
        'status', 'attended', 'session__workshop__category',
        'registration_date', 'session__start_datetime'
    ]
    search_fields = [
        'student__username', 'student__email', 'email',
        'session__workshop__title'
    ]
    
    fieldsets = (
        ('Registration', {
            'fields': ('session', 'student', 'status')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Experience', {
            'fields': ('experience_level', 'expectations', 'special_requirements')
        }),
        ('Post-Session', {
            'fields': ('attended', 'rating', 'feedback')
        }),
    )
    
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username
    student_name.short_description = 'Student'
    
    def workshop_title(self, obj):
        return obj.session.workshop.title
    workshop_title.short_description = 'Workshop'
    
    def session_date(self, obj):
        return obj.session.start_datetime.strftime('%Y-%m-%d %H:%M')
    session_date.short_description = 'Session Date'


@admin.register(WorkshopMaterial)
class WorkshopMaterialAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'workshop', 'session_info', 'material_type', 'access_timing', 
        'file_size_info', 'requires_registration', 'is_featured', 'order'
    ]
    list_filter = [
        'material_type', 'access_timing', 'requires_registration', 
        'is_featured', 'workshop__category'
    ]
    search_fields = ['title', 'description', 'workshop__title']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workshop', 'session', 'title', 'description')
        }),
        ('Content', {
            'fields': ('material_type', 'file', 'external_url')
        }),
        ('Access Control', {
            'fields': ('access_timing', 'requires_registration', 'is_downloadable')
        }),
        ('Organization', {
            'fields': ('order', 'is_featured')
        }),
    )
    
    def session_info(self, obj):
        if obj.session:
            return f"{obj.session.start_datetime.strftime('%Y-%m-%d %H:%M')}"
        return "Workshop-level"
    session_info.short_description = 'Session'
    
    def file_size_info(self, obj):
        return obj.file_size_display if obj.file else 'No file'
    file_size_info.short_description = 'File Size'


@admin.register(WorkshopInterest)
class WorkshopInterestAdmin(admin.ModelAdmin):
    list_display = [
        'workshop', 'user', 'email', 'preferred_timing_display', 
        'is_active', 'has_been_notified', 'created_at'
    ]
    list_filter = [
        'workshop', 'preferred_timing', 'experience_level', 
        'is_active', 'has_been_notified', 'notify_immediately',
        'created_at'
    ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'email', 'workshop__title']
    readonly_fields = ['created_at', 'updated_at', 'notification_sent_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workshop', 'user', 'email')
        }),
        ('Preferences', {
            'fields': ('preferred_timing', 'experience_level', 'special_requests')
        }),
        ('Notifications', {
            'fields': ('notify_immediately', 'notify_summary', 'is_active')
        }),
        ('Status', {
            'fields': ('has_been_notified', 'notification_sent_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def preferred_timing_display(self, obj):
        return obj.formatted_timing
    preferred_timing_display.short_description = 'Preferred Timing'


@admin.register(WorkshopCartItem)
class WorkshopCartItemAdmin(admin.ModelAdmin):
    list_display = ['cart_user', 'workshop_title', 'session_date', 'price', 'added_at']
    list_filter = ['added_at', 'session__workshop__category']
    search_fields = [
        'cart__user__username', 'cart__user__email',
        'session__workshop__title'
    ]
    readonly_fields = ['added_at']

    fieldsets = (
        ('Cart Item', {
            'fields': ('cart', 'session', 'price')
        }),
        ('Optional Details', {
            'fields': ('notes', 'child_profile'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )

    def cart_user(self, obj):
        return obj.cart.user.get_full_name() or obj.cart.user.username
    cart_user.short_description = 'User'

    def workshop_title(self, obj):
        return obj.session.workshop.title
    workshop_title.short_description = 'Workshop'

    def session_date(self, obj):
        return obj.session.start_datetime.strftime('%Y-%m-%d %H:%M')
    session_date.short_description = 'Session Date'


# Customize admin site
admin.site.site_header = "Recordered Workshop Admin"
admin.site.site_title = "Workshop Admin"
admin.site.index_title = "Workshop Management"
