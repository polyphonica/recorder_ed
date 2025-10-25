from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('accounts:profile_setup')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Log the user in after successful registration with explicit backend
        login(self.request, self.object, backend='apps.core.backends.EmailBackend')
        messages.success(self.request, 'Account created successfully! Please complete your profile.')
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