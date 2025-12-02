from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, DetailView
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm, UserProfileForm, ChildProfileForm, AccountTransferForm
from .models import UserProfile, ChildProfile
from .email_verification import send_verification_email
from django.db import transaction


class CustomLoginView(LoginView):
    """
    Custom login view that redirects users based on their role:
    - Staff members → Support Dashboard
    - Instructors → Workshops Dashboard (default)
    - Students → Workshops list (default)
    """
    def dispatch(self, request, *args, **kwargs):
        # If user is already authenticated, redirect them away from login page
        if request.user.is_authenticated:
            return redirect(self.get_redirect_url_for_authenticated_user())
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url_for_authenticated_user(self):
        """Determine where to redirect already-authenticated users"""
        if self.request.user.is_staff:
            return reverse('support:staff_dashboard')
        elif hasattr(self.request.user, 'profile') and self.request.user.profile.is_teacher:
            return reverse('workshops:instructor_dashboard')
        else:
            return reverse('workshops:list')

    def get_success_url(self):
        # Check if user is staff
        if self.request.user.is_staff:
            return reverse('support:staff_dashboard')

        # Use the default LOGIN_REDIRECT_URL for other users
        return super().get_success_url()


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/signup.html'

    def get_success_url(self):
        # Store the 'next' parameter in session for use after profile setup
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            self.request.session['signup_next'] = next_url
        return reverse_lazy('accounts:profile_setup')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object

        # Send verification email
        try:
            send_verification_email(self.request, user)
        except Exception as e:
            # Log error but don't block registration
            print(f"Failed to send verification email: {e}")

        # Check if this is a guardian signup
        if form.cleaned_data.get('is_guardian'):
            # Mark user profile as guardian
            user.profile.is_guardian = True
            user.profile.save()

            # Create child profile
            child_profile = ChildProfile.objects.create(
                guardian=user,
                first_name=form.cleaned_data['child_first_name'],
                last_name=form.cleaned_data['child_last_name'],
                date_of_birth=form.cleaned_data['child_date_of_birth']
            )

            # Log the user in after successful registration with explicit backend
            login(self.request, user, backend='apps.core.backends.EmailBackend')
            messages.success(
                self.request,
                f'Guardian account created successfully for {child_profile.full_name}! '
                'Please check your email to verify your account and complete your profile.'
            )
        else:
            # Regular student signup
            # Log the user in after successful registration with explicit backend
            login(self.request, user, backend='apps.core.backends.EmailBackend')
            messages.success(
                self.request,
                'Account created successfully! Please check your email to verify your account and complete your profile.'
            )

        return response

@login_required
def profile_setup_view(request):
    """Initial profile setup after registration"""
    profile = request.user.profile

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.profile_completed = True
            profile.save()

            # Also update the User model with first_name and last_name
            user = request.user
            user.first_name = profile.first_name
            user.last_name = profile.last_name
            user.save()

            messages.success(request, 'Profile completed successfully!')

            # Check for stored 'next' URL from signup
            next_url = request.session.pop('signup_next', None)
            if next_url:
                return redirect(next_url)

            # Default fallback
            return redirect('workshops:student_dashboard')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'accounts/profile_setup.html', {
        'form': form,
        'is_setup': True
    })

@login_required
def profile_edit_view(request):
    """Edit existing profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            
            # Also update the User model with first_name and last_name
            user = request.user
            user.first_name = profile.first_name
            user.last_name = profile.last_name
            user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile_edit')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'accounts/profile_setup.html', {
        'form': form,
        'is_setup': False
    })


class TeacherPublicProfileView(DetailView):
    """
    Public teacher profile page - no login required.
    Shows teacher bio, experience, courses, workshops, etc.
    """
    model = User
    template_name = 'accounts/teacher_profile.html'
    context_object_name = 'teacher'
    pk_url_kwarg = 'teacher_id'

    def get_queryset(self):
        # Only show teachers who have completed profiles and are marked as teachers
        return User.objects.filter(
            profile__is_teacher=True,
            profile__profile_completed=True
        ).select_related('profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.object

        # Get teacher's courses (published only)
        try:
            from apps.courses.models import Course
            courses = Course.objects.filter(
                instructor=teacher,
                status='published'
            )[:6]  # Limit to 6 courses
            context['courses'] = courses
        except:
            context['courses'] = []

        # Get teacher's workshops (published only)
        try:
            from apps.workshops.models import Workshop
            workshops = Workshop.objects.filter(
                instructor=teacher,
                status='published'
            )[:6]  # Limit to 6 workshops
            context['workshops'] = workshops
        except:
            context['workshops'] = []

        # Check if teacher offers private lessons
        context['offers_private_lessons'] = teacher.profile.is_private_teacher

        return context


@login_required
def guardian_dashboard_view(request):
    """Dashboard for guardians to manage their children"""
    if not request.user.profile.is_guardian:
        messages.error(request, 'This page is only accessible to guardian accounts.')
        return redirect('workshops:student_dashboard')

    children = request.user.children.all().order_by('first_name')

    context = {
        'children': children,
    }
    return render(request, 'accounts/guardian_dashboard.html', context)


@login_required
def add_child_view(request):
    """Add a new child to guardian account"""
    if not request.user.profile.is_guardian:
        messages.error(request, 'This page is only accessible to guardian accounts.')
        return redirect('workshops:student_dashboard')

    if request.method == 'POST':
        form = ChildProfileForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.guardian = request.user
            child.save()
            messages.success(request, f'Child profile created for {child.full_name}!')
            return redirect('accounts:guardian_dashboard')
    else:
        form = ChildProfileForm()

    return render(request, 'accounts/child_form.html', {
        'form': form,
        'title': 'Add Child Profile',
        'is_edit': False
    })


@login_required
def edit_child_view(request, child_id):
    """Edit an existing child profile"""
    child = get_object_or_404(ChildProfile, id=child_id, guardian=request.user)

    if request.method == 'POST':
        form = ChildProfileForm(request.POST, instance=child)
        if form.is_valid():
            child = form.save()
            messages.success(request, f'Child profile updated for {child.full_name}!')
            return redirect('accounts:guardian_dashboard')
    else:
        form = ChildProfileForm(instance=child)

    return render(request, 'accounts/child_form.html', {
        'form': form,
        'child': child,
        'title': f'Edit {child.full_name}',
        'is_edit': True
    })


@login_required
def delete_child_view(request, child_id):
    """Delete a child profile"""
    child = get_object_or_404(ChildProfile, id=child_id, guardian=request.user)

    if request.method == 'POST':
        child_name = child.full_name
        child.delete()
        messages.success(request, f'Child profile for {child_name} has been deleted.')
        return redirect('accounts:guardian_dashboard')

    return render(request, 'accounts/child_confirm_delete.html', {
        'child': child
    })


def transfer_account_view(request, child_id):
    """
    Transfer a child account to an adult account when they turn 18.
    Only accessible via a special link provided to guardians for 18+ children.
    """
    # Get the child profile
    child = get_object_or_404(ChildProfile, id=child_id)

    # Verify the child is 18 or older
    if not child.is_adult:
        messages.error(request, 'Account transfer is only available for students who are 18 years or older.')
        return redirect('core:home')

    if request.method == 'POST':
        form = AccountTransferForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create new adult user account
                new_user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1'],
                    first_name=child.first_name,
                    last_name=child.last_name
                )

                # Update profile
                new_user.profile.phone = form.cleaned_data.get('phone', '')
                new_user.profile.is_student = True
                new_user.profile.profile_completed = True
                new_user.profile.save()

                # Transfer all enrollments
                from apps.courses.models import CourseEnrollment
                CourseEnrollment.objects.filter(child_profile=child).update(
                    student=new_user,
                    child_profile=None
                )

                # Transfer all workshop registrations
                from apps.workshops.models import WorkshopRegistration
                WorkshopRegistration.objects.filter(child_profile=child).update(
                    student=new_user,
                    child_profile=None
                )

                # Transfer all lesson requests
                from apps.private_teaching.models import LessonRequest
                LessonRequest.objects.filter(child_profile=child).update(
                    student=new_user,
                    child_profile=None
                )

                # Delete the child profile
                guardian_user = child.guardian
                child.delete()

                # Log the new user in
                login(request, new_user, backend='apps.core.backends.EmailBackend')

                messages.success(
                    request,
                    f'Account successfully transferred! Welcome, {new_user.first_name}. '
                    'Your account is now independent and all your learning history has been preserved.'
                )
                return redirect('workshops:student_dashboard')
    else:
        form = AccountTransferForm()

    return render(request, 'accounts/transfer_account.html', {
        'form': form,
        'child': child
    })


def verify_email_view(request, uidb64, token):
    """
    Verify user's email address using the token sent via email.
    """
    from .email_verification import verify_token
    from django.utils import timezone

    user = verify_token(uidb64, token)

    if user is not None:
        # Mark email as verified
        user.profile.email_verified = True
        user.profile.email_verified_at = timezone.now()
        user.profile.save()

        messages.success(
            request,
            'Email verified successfully! You now have full access to all platform features.'
        )

        # If user is logged in, redirect to their dashboard
        if request.user.is_authenticated:
            return redirect('workshops:student_dashboard')
        else:
            # Otherwise redirect to login
            return redirect('accounts:login')
    else:
        messages.error(
            request,
            'Email verification link is invalid or has expired. Please request a new verification email.'
        )
        return redirect('accounts:resend_verification')


@login_required
def resend_verification_view(request):
    """
    Resend verification email to the logged-in user.
    """
    user = request.user

    # Check if already verified
    if user.profile.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('workshops:student_dashboard')

    if request.method == 'POST':
        try:
            send_verification_email(request, user)
            messages.success(
                request,
                'Verification email sent! Please check your inbox and spam folder.'
            )
        except Exception as e:
            messages.error(
                request,
                'Failed to send verification email. Please try again later or contact support.'
            )

        return redirect('workshops:student_dashboard')

    return render(request, 'accounts/resend_verification.html')