from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, RedirectView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.core.paginator import Paginator

from .models import (
    Workshop, WorkshopCategory, WorkshopSession, 
    WorkshopRegistration, WorkshopMaterial, WorkshopInterest
)
from .forms import WorkshopRegistrationForm, WorkshopForm, WorkshopSessionForm, WorkshopFilterForm, WorkshopInterestForm, WorkshopMaterialForm
from .mixins import InstructorRequiredMixin


class WorkshopListView(ListView):
    """Display list of workshops with filtering and search"""
    model = Workshop
    template_name = 'workshops/workshop_list.html'
    context_object_name = 'workshops'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Workshop.objects.filter(status='published').select_related(
            'instructor', 'category'
        ).prefetch_related('sessions')
        
        # Category filtering
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__icontains=search_query)
            )
        
        # Difficulty filter
        difficulty = self.request.GET.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
        
        # Delivery method filter
        delivery_method = self.request.GET.get('delivery_method')
        if delivery_method:
            queryset = queryset.filter(delivery_method=delivery_method)
        
        # Price filter
        price_filter = self.request.GET.get('price')
        if price_filter == 'free':
            queryset = queryset.filter(is_free=True)
        elif price_filter == 'paid':
            queryset = queryset.filter(is_free=False)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'featured')
        if sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating')
        else:  # featured
            queryset = queryset.order_by('-is_featured', '-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'categories': WorkshopCategory.objects.filter(is_active=True),
            'current_category': self.kwargs.get('category_slug'),
            'search_query': self.request.GET.get('search', ''),
            'current_difficulty': self.request.GET.get('difficulty', ''),
            'current_price': self.request.GET.get('price', ''),
            'current_sort': self.request.GET.get('sort', 'featured'),
            'difficulty_choices': Workshop.DIFFICULTY_CHOICES,
        })
        return context


class WorkshopDetailView(DetailView):
    """Detailed view of a workshop with sessions and registration info"""
    model = Workshop
    template_name = 'workshops/workshop_detail.html'
    context_object_name = 'workshop'
    
    def get_queryset(self):
        return Workshop.objects.filter(status='published').select_related(
            'instructor', 'category'
        ).prefetch_related('sessions', 'materials')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workshop = self.object
        
        # Get upcoming sessions
        upcoming_sessions = workshop.sessions.filter(
            start_datetime__gte=timezone.now(),
            is_active=True,
            is_cancelled=False
        ).order_by('start_datetime')
        
        # Add user registration info to sessions
        if self.request.user.is_authenticated:
            registrations = WorkshopRegistration.objects.filter(
                student=self.request.user,
                session__workshop=workshop
            ).select_related('session')
            
            # Create a mapping for easy lookup
            reg_map = {reg.session.id: reg for reg in registrations}
            
            # Add registration info to each session
            for session in upcoming_sessions:
                if session.id in reg_map:
                    session.user_registration = reg_map[session.id]
                else:
                    session.user_registration = None
        
        # Get materials accessible before session (exclude session-specific materials)
        pre_materials = workshop.materials.filter(
            access_timing__in=['pre', 'always'],
            session__isnull=True  # Only workshop-level materials, not session-specific
        ).order_by('order')
        
        # Get session-specific materials for registered user
        session_materials = []
        if self.request.user.is_authenticated:
            user_sessions = WorkshopSession.objects.filter(
                workshop=workshop,
                registrations__student=self.request.user,
                registrations__status__in=['registered', 'attended']
            ).prefetch_related('materials')
            
            for session in user_sessions:
                # Get materials accessible for this session based on timing
                now = timezone.now()
                session_start = session.start_datetime
                session_end = session.end_datetime
                
                accessible_materials = []
                for material in session.materials.all():
                    access_rules = {
                        'always': True,
                        'pre': now < session_start,
                        'during': session_start <= now <= session_end,
                        'post': now > session_end,
                    }
                    
                    if access_rules.get(material.access_timing, False):
                        accessible_materials.append(material)
                
                if accessible_materials:
                    session_materials.append({
                        'session': session,
                        'materials': accessible_materials
                    })
        
        # Get related workshops
        related_workshops = Workshop.objects.filter(
            category=workshop.category,
            status='published'
        ).exclude(id=workshop.id).select_related('instructor', 'category')[:3]
        
        # If current workshop has no available sessions, prioritize similar workshops with sessions
        similar_workshops_with_sessions = []
        if not workshop.has_available_sessions:
            similar_workshops_with_sessions = Workshop.objects.filter(
                Q(category=workshop.category) | 
                Q(difficulty_level=workshop.difficulty_level) |
                Q(tags__icontains=workshop.tags.split(',')[0] if workshop.tags else ''),
                status='published'
            ).exclude(
                id=workshop.id
            ).annotate(
                has_sessions=Count('sessions', filter=Q(
                    sessions__start_datetime__gte=timezone.now(),
                    sessions__is_active=True,
                    sessions__current_registrations__lt=F('sessions__max_participants')
                ))
            ).filter(
                has_sessions__gt=0
            ).select_related('instructor', 'category').distinct()[:4]
        
        context.update({
            'upcoming_sessions': upcoming_sessions,
            'pre_materials': pre_materials,
            'session_materials': session_materials,
            'related_workshops': related_workshops,
            'similar_workshops_with_sessions': similar_workshops_with_sessions,
        })

        # Cart is not used for workshops - registrations are direct
        context['cart_session_ids'] = []

        return context


class WorkshopRegistrationView(LoginRequiredMixin, CreateView):
    """Register for a workshop session"""
    model = WorkshopRegistration
    form_class = WorkshopRegistrationForm
    template_name = 'workshops/workshop_register.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure user is authenticated FIRST
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        self.workshop = get_object_or_404(
            Workshop, 
            slug=kwargs['workshop_slug'], 
            status='published'
        )
        self.session = get_object_or_404(
            WorkshopSession,
            id=kwargs['session_id'],
            workshop=self.workshop,
            is_active=True
        )
        
        # Check if user already registered (now safe since user is authenticated)
        existing_registration = WorkshopRegistration.objects.filter(
            student=request.user,
            session=self.session
        ).first()
        
        if existing_registration:
            if existing_registration.status == 'promoted':
                # Redirect promoted users to complete their payment
                messages.warning(request, 'Complete your payment to secure your workshop spot.')
                return redirect('workshops:registration_confirm', registration_id=existing_registration.id)
            else:
                messages.info(request, f'You are already {existing_registration.status} for this session.')
                return redirect('workshops:detail', slug=self.workshop.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['session'] = self.session
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Double-check user is authenticated
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()

        registration = form.save(commit=False)
        registration.student = self.request.user
        registration.session = self.session
        registration.email = registration.email or getattr(self.request.user, 'email', '')

        # Handle child profile if guardian
        if self.request.user.profile.is_guardian:
            child_id = form.cleaned_data.get('child_profile')
            if child_id:
                from apps.accounts.models import ChildProfile
                try:
                    child = ChildProfile.objects.get(id=child_id, guardian=self.request.user)
                    registration.child_profile = child
                except ChildProfile.DoesNotExist:
                    messages.error(self.request, 'Invalid child selected.')
                    return redirect('workshops:detail', slug=self.workshop.slug)

        # Check if workshop requires payment
        is_paid_workshop = not self.workshop.is_free and self.workshop.price > 0

        # Determine registration status based on capacity
        if self.session.is_full:
            if self.session.waitlist_enabled:
                registration.status = 'waitlisted'
                registration.payment_status = 'not_required'  # Payment only required when promoted
                student_name = registration.child_profile.full_name if registration.child_profile else 'You'
                messages.success(
                    self.request,
                    f'{student_name} {"has" if registration.child_profile else "have"} been added to the waitlist for this workshop.'
                )
                registration.save()
                self.workshop.total_registrations += 1
                self.workshop.save()
                return redirect('workshops:registration_confirm', registration_id=registration.id)
            else:
                messages.error(
                    self.request,
                    'Sorry, this workshop session is full and waitlist is not available.'
                )
                return redirect('workshops:detail', slug=self.workshop.slug)

        # Workshop has capacity available
        if is_paid_workshop:
            # PAID WORKSHOP: Create registration with pending payment status
            registration.status = 'pending_payment'
            registration.payment_status = 'pending'
            registration.payment_amount = self.workshop.price
            registration.save()

            # Create Stripe checkout session
            from apps.payments.stripe_service import create_checkout_session
            from django.urls import reverse

            success_url = self.request.build_absolute_uri(
                reverse('workshops:checkout_success', kwargs={'registration_id': registration.id})
            )
            cancel_url = self.request.build_absolute_uri(
                reverse('workshops:checkout_cancel', kwargs={'registration_id': registration.id})
            )

            try:
                # Format descriptive item name and description
                session_date = self.session.start_datetime.strftime('%d %B %Y at %H:%M')
                item_name = f"{self.workshop.title}"
                item_description = f"Workshop session on {session_date}"

                session = create_checkout_session(
                    amount=self.workshop.price,
                    student=self.request.user,
                    teacher=self.workshop.instructor,
                    domain='workshops',
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata={
                        'registration_id': str(registration.id),
                        'workshop_id': str(self.workshop.id),
                        'session_id': str(self.session.id),
                    },
                    item_name=item_name,
                    item_description=item_description
                )

                # Save session ID to registration
                registration.stripe_checkout_session_id = session.id
                registration.save()

                # Redirect to Stripe Checkout
                return redirect(session.url, code=303)

            except Exception as e:
                # If Stripe checkout creation fails, delete the registration
                registration.delete()
                messages.error(self.request, f"Payment setup failed: {str(e)}. Please try again.")
                return redirect('workshops:detail', slug=self.workshop.slug)

        else:
            # FREE WORKSHOP: Immediate registration
            registration.status = 'registered'
            registration.payment_status = 'not_required'
            registration.payment_amount = 0
            registration.save()

            # Update session registration count
            self.session.current_registrations += 1
            self.session.save()

            student_name = registration.child_profile.full_name if registration.child_profile else 'You'
            messages.success(
                self.request,
                f'{student_name} {"has" if registration.child_profile else "have"} been successfully registered for the workshop!'
            )

            # Update workshop total registrations
            self.workshop.total_registrations += 1
            self.workshop.save()

            # Send notification to instructor
            try:
                from .notifications import InstructorNotificationService
                InstructorNotificationService.send_new_registration_notification(registration)
            except Exception as e:
                # Don't fail the registration if email fails
                print(f"Failed to send instructor notification: {e}")

            return redirect('workshops:registration_confirm', registration_id=registration.id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'workshop': self.workshop,
            'session': self.session,
            'is_waitlist': self.session.is_full,
        })
        return context


class RegistrationConfirmView(LoginRequiredMixin, DetailView):
    """Confirmation page after registration"""
    model = WorkshopRegistration
    template_name = 'workshops/registration_confirm.html'
    context_object_name = 'registration'
    pk_url_kwarg = 'registration_id'
    
    def get_queryset(self):
        return WorkshopRegistration.objects.filter(
            student=self.request.user
        ).select_related('session__workshop')
    
    def post(self, request, *args, **kwargs):
        """Handle payment completion for promoted registrations"""
        registration = self.get_object()

        if registration.status == 'promoted':
            # Complete the registration (simulate payment completion)
            registration.status = 'registered'
            registration.save()

            # Mark the promotion as confirmed
            from django.apps import apps
            WaitlistPromotion = apps.get_model('workshops', 'WaitlistPromotion')
            promotion = WaitlistPromotion.objects.filter(
                registration=registration,
                confirmed_at__isnull=True
            ).first()

            if promotion:
                promotion.confirmed_at = timezone.now()
                promotion.save()

            # Update session registration count
            registration.session.current_registrations = registration.session.registrations.filter(
                status__in=['registered', 'promoted', 'attended']
            ).count()
            registration.session.save(update_fields=['current_registrations'])

            messages.success(request, 'Payment completed! You are now registered for the workshop.')

            # Send confirmation notification to student
            try:
                from .notifications import WaitlistNotificationService
                WaitlistNotificationService.send_registration_confirmed_notification(registration)
            except Exception as e:
                print(f"Failed to send student confirmation: {e}")

            # Send notification to instructor
            try:
                from .notifications import InstructorNotificationService
                InstructorNotificationService.send_new_registration_notification(registration)
            except Exception as e:
                print(f"Failed to send instructor notification: {e}")

        else:
            messages.warning(request, 'This registration cannot be completed.')

        return redirect('workshops:registration_confirm', registration_id=registration.id)


class WorkshopCheckoutSuccessView(LoginRequiredMixin, TemplateView):
    """Handle return from Stripe after successful checkout"""
    template_name = 'workshops/checkout_success.html'

    def get(self, request, *args, **kwargs):
        registration_id = kwargs.get('registration_id')

        try:
            registration = WorkshopRegistration.objects.select_related(
                'session__workshop'
            ).get(id=registration_id, student=request.user)

            # Webhook will update the status, but show intermediate page
            context = self.get_context_data(**kwargs)
            context['registration'] = registration
            context['workshop'] = registration.session.workshop
            context['session'] = registration.session

            return self.render_to_response(context)

        except WorkshopRegistration.DoesNotExist:
            messages.error(request, 'Registration not found.')
            return redirect('workshops:list')


class WorkshopCheckoutCancelView(LoginRequiredMixin, TemplateView):
    """Handle cancelled checkout"""
    template_name = 'workshops/checkout_cancel.html'

    def get(self, request, *args, **kwargs):
        registration_id = kwargs.get('registration_id')

        try:
            registration = WorkshopRegistration.objects.select_related(
                'session__workshop'
            ).get(id=registration_id, student=request.user)

            # Mark payment as failed
            registration.payment_status = 'failed'
            registration.save()

            context = self.get_context_data(**kwargs)
            context['registration'] = registration
            context['workshop'] = registration.session.workshop
            context['session'] = registration.session

            messages.warning(
                request,
                'Payment was cancelled. You can try again from your registrations page.'
            )

            return self.render_to_response(context)

        except WorkshopRegistration.DoesNotExist:
            messages.error(request, 'Registration not found.')
            return redirect('workshops:list')


class RegistrationCancelView(LoginRequiredMixin, DetailView):
    """Cancel a workshop registration"""
    model = WorkshopRegistration
    pk_url_kwarg = 'registration_id'
    
    def get_queryset(self):
        return WorkshopRegistration.objects.filter(
            student=self.request.user
        ).select_related('session__workshop')
    
    def post(self, request, *args, **kwargs):
        registration = self.get_object()

        if registration.status in ['registered', 'waitlisted']:
            if registration.status == 'registered':
                # Free up a spot
                session = registration.session
                session.current_registrations = max(0, session.current_registrations - 1)
                session.save()

                # Promote someone from waitlist
                waitlisted = WorkshopRegistration.objects.filter(
                    session=session,
                    status='waitlisted'
                ).order_by('registration_date').first()

                if waitlisted:
                    waitlisted.status = 'registered'
                    waitlisted.save()
                    session.current_registrations += 1
                    session.save()

                    # Send notification to promoted student
                    try:
                        from .notifications import WaitlistNotificationService
                        WaitlistNotificationService.send_registration_confirmed_notification(waitlisted)
                    except Exception as e:
                        print(f"Failed to send student promotion notification: {e}")

                    # Send notification to instructor about promotion
                    try:
                        from .notifications import InstructorNotificationService
                        InstructorNotificationService.send_new_registration_notification(waitlisted)
                    except Exception as e:
                        print(f"Failed to send instructor promotion notification: {e}")

            registration.status = 'cancelled'
            registration.save()

            # Send cancellation notification to instructor
            try:
                from .notifications import InstructorNotificationService
                InstructorNotificationService.send_registration_cancelled_notification(registration)
            except Exception as e:
                print(f"Failed to send instructor cancellation notification: {e}")

            messages.success(request, 'Your registration has been cancelled.')
        else:
            messages.error(request, 'Cannot cancel this registration.')

        return redirect('workshops:my_registrations')


class PromotionConfirmView(TemplateView):
    """Confirm waitlist promotion"""
    template_name = 'workshops/promotion_confirm.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the registration
        registration_id = kwargs.get('registration_id')
        try:
            registration = WorkshopRegistration.objects.select_related(
                'session__workshop'
            ).get(
                id=registration_id,
                promoted_at__isnull=False,
                promotion_expires_at__isnull=False
            )
            
            # Get the active promotion
            promotion = registration.promotions.filter(
                expired=False,
                confirmed_at__isnull=True
            ).first()
            
            context.update({
                'registration': registration,
                'session': registration.session,
                'workshop': registration.session.workshop,
                'promotion': promotion,
                'is_expired': registration.is_promotion_expired,
            })
            
        except WorkshopRegistration.DoesNotExist:
            context['error'] = 'Invalid or expired promotion link.'
        
        return context
    
    def post(self, request, *args, **kwargs):
        registration_id = kwargs.get('registration_id')
        
        try:
            registration = WorkshopRegistration.objects.select_related(
                'session__workshop'
            ).get(
                id=registration_id,
                promoted_at__isnull=False,
                promotion_expires_at__isnull=False
            )
            
            # Check if expired
            if registration.is_promotion_expired:
                messages.error(request, 'This promotion has expired.')
                return redirect('workshops:detail', slug=registration.session.workshop.slug)
            
            # Check if already confirmed
            promotion = registration.promotions.filter(
                expired=False,
                confirmed_at__isnull=True
            ).first()
            
            if not promotion:
                messages.info(request, 'This promotion has already been processed.')
                return redirect('workshops:detail', slug=registration.session.workshop.slug)
            
            # Confirm the promotion
            registration.confirm_promotion()
            
            # Send confirmation email
            from .notifications import WaitlistNotificationService
            WaitlistNotificationService.send_registration_confirmed_notification(registration)
            
            messages.success(
                request, 
                f'Your registration for "{registration.session.workshop.title}" has been confirmed!'
            )
            
            return redirect('workshops:registration_confirm', registration_id=registration.id)
            
        except WorkshopRegistration.DoesNotExist:
            messages.error(request, 'Invalid promotion link.')
            return redirect('workshops:list')


class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """Smart dashboard that redirects users based on their role"""
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        
        # Check if user has instructor status
        if user.is_instructor():
            return reverse('workshops:instructor_dashboard')
        else:
            return reverse('workshops:student_dashboard')


class StudentDashboardView(LoginRequiredMixin, TemplateView):
    """Student dashboard showing upcoming workshops and progress"""
    template_name = 'workshops/student_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Upcoming workshops
        upcoming_registrations = WorkshopRegistration.objects.filter(
            student=user,
            status='registered',
            session__start_datetime__gte=timezone.now()
        ).select_related('session__workshop').order_by('session__start_datetime')[:5]
        
        # Recent activity
        recent_registrations = WorkshopRegistration.objects.filter(
            student=user
        ).select_related('session__workshop').order_by('-registration_date')[:10]
        
        # Statistics
        total_registered = WorkshopRegistration.objects.filter(
            student=user, 
            status__in=['registered', 'attended']
        ).count()
        
        attended = WorkshopRegistration.objects.filter(
            student=user, 
            attended=True
        ).count()
        
        context.update({
            'upcoming_registrations': upcoming_registrations,
            'recent_registrations': recent_registrations,
            'stats': {
                'total_registered': total_registered,
                'attended': attended,
                'completion_rate': (attended / total_registered * 100) if total_registered > 0 else 0,
            }
        })
        return context


class MyRegistrationsView(LoginRequiredMixin, ListView):
    """List of user's workshop registrations"""
    model = WorkshopRegistration
    template_name = 'workshops/my_registrations.html'
    context_object_name = 'registrations'
    paginate_by = 20
    
    def get_queryset(self):
        return WorkshopRegistration.objects.filter(
            student=self.request.user
        ).select_related('session__workshop').order_by('-registration_date')


class InstructorDashboardView(InstructorRequiredMixin, TemplateView):
    """Instructor dashboard with workshop management overview"""
    template_name = 'workshops/instructor_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Workshop statistics with prefetched sessions
        workshops_queryset = Workshop.objects.filter(instructor=user).prefetch_related(
            'sessions'
        ).order_by('-created_at')
        
        # Convert to list and limit to avoid slice issues
        workshops = list(workshops_queryset[:6])
        
        # Add upcoming sessions for each workshop to avoid template filtering issues
        for workshop in workshops:
            workshop.upcoming_sessions_list = list(WorkshopSession.objects.filter(
                workshop=workshop,
                start_datetime__gte=timezone.now(),
                is_active=True
            ).order_by('start_datetime')[:3])
            
            # Add session count to avoid list.count() error
            workshop.total_sessions_count = WorkshopSession.objects.filter(workshop=workshop).count()
        
        upcoming_sessions = WorkshopSession.objects.filter(
            workshop__instructor=user,
            start_datetime__gte=timezone.now(),
            is_active=True
        ).select_related('workshop').order_by('start_datetime')[:5]
        
        recent_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=user
        ).select_related('session__workshop', 'student').order_by('-registration_date')[:10]
        
        context.update({
            'workshops': workshops,
            'upcoming_sessions': upcoming_sessions,
            'recent_registrations': recent_registrations,
            'stats': {
                'total_workshops': len(workshops),
                'published_workshops': len([w for w in workshops if w.status == 'published']),
                'total_sessions': WorkshopSession.objects.filter(workshop__instructor=user).count(),
                'total_registrations': WorkshopRegistration.objects.filter(session__workshop__instructor=user).count(),
            }
        })
        return context


class InstructorWorkshopsView(InstructorRequiredMixin, ListView):
    """List of instructor's workshops"""
    model = Workshop
    template_name = 'workshops/instructor_workshops.html'
    context_object_name = 'workshops'
    paginate_by = 12
    
    def get_queryset(self):
        return Workshop.objects.filter(
            instructor=self.request.user
        ).prefetch_related('sessions').order_by('-created_at')


class CreateWorkshopView(LoginRequiredMixin, CreateView):
    """Create new workshop"""
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/workshop_form.html'
    
    def form_valid(self, form):
        form.instance.instructor = self.request.user
        messages.success(
            self.request, 
            'Workshop created successfully! Now add sessions to schedule when it will run.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect to session management for the newly created workshop
        return reverse('workshops:manage_sessions', kwargs={'slug': self.object.slug})


class EditWorkshopView(LoginRequiredMixin, UpdateView):
    """Edit existing workshop"""
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/workshop_form.html'
    
    def get_queryset(self):
        return Workshop.objects.filter(instructor=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Workshop updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('workshops:instructor_workshops')


class ManageSessionsView(LoginRequiredMixin, TemplateView):
    """Manage workshop sessions"""
    template_name = 'workshops/manage_sessions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.workshop = get_object_or_404(
            Workshop, 
            slug=kwargs['slug'],
            instructor=self.request.user
        )
        
        sessions = self.workshop.sessions.all().order_by('start_datetime')
        
        # Add registration statistics for each session
        for session in sessions:
            session.registration_stats = {
                'total': session.registrations.count(),
                'registered': session.registrations.filter(status='registered').count(),
                'waitlisted': session.registrations.filter(status='waitlisted').count(),
                'attended': session.registrations.filter(status='attended').count(),
            }
        
        # Use provided form with errors, or create a new one
        session_form = kwargs.get('session_form', WorkshopSessionForm())
        
        context.update({
            'workshop': self.workshop,
            'sessions': sessions,
            'session_form': session_form,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        workshop = get_object_or_404(
            Workshop, 
            slug=kwargs['slug'],
            instructor=request.user
        )
        
        form = WorkshopSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.workshop = workshop
            session.save()
            messages.success(request, 'Session created successfully!')
            return redirect('workshops:manage_sessions', slug=workshop.slug)
        else:
            messages.error(request, 'Please correct the errors below.')
            # Re-render the page with form errors instead of redirecting
            return self.render_to_response(self.get_context_data(session_form=form, **kwargs))


class EditSessionView(LoginRequiredMixin, UpdateView):
    """Edit an existing workshop session"""
    model = WorkshopSession
    form_class = WorkshopSessionForm
    template_name = 'workshops/edit_session.html'
    pk_url_kwarg = 'session_id'
    
    def get_queryset(self):
        # Ensure instructor can only edit their own workshop sessions
        return WorkshopSession.objects.filter(
            workshop__instructor=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workshop'] = self.object.workshop
        return context
    
    def form_valid(self, form):
        # Check if max_participants was changed
        old_max_participants = self.object.max_participants if self.object.pk else None
        response = super().form_valid(form)
        
        # If max_participants increased, trigger waitlist processing
        if (old_max_participants is not None and 
            self.object.max_participants > old_max_participants):
            # Manually trigger the signal with update_fields
            from django.db.models.signals import post_save
            post_save.send(
                sender=WorkshopSession,
                instance=self.object,
                created=False,
                update_fields=['max_participants']
            )
        
        messages.success(self.request, 'Session updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse('workshops:manage_sessions', kwargs={'slug': self.object.workshop.slug})


class SessionRegistrationsView(LoginRequiredMixin, ListView):
    """View registrations for a specific session with participant management"""
    model = WorkshopRegistration
    template_name = 'workshops/session_registrations.html'
    context_object_name = 'registrations'
    paginate_by = 50
    
    def get_queryset(self):
        self.session = get_object_or_404(
            WorkshopSession,
            id=self.kwargs['session_id'],
            workshop__instructor=self.request.user
        )
        
        queryset = WorkshopRegistration.objects.filter(
            session=self.session
        ).select_related('student').order_by('registration_date')
        
        # Filter by status if requested
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
            
        # Search by student name or email
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search) |
                Q(student__last_name__icontains=search) |
                Q(student__username__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get registration statistics
        all_registrations = WorkshopRegistration.objects.filter(session=self.session)
        stats = {
            'total': all_registrations.count(),
            'registered': all_registrations.filter(status='registered').count(),
            'waitlisted': all_registrations.filter(status='waitlisted').count(),
            'attended': all_registrations.filter(status='attended').count(),
            'no_show': all_registrations.filter(status='no_show').count(),
            'cancelled': all_registrations.filter(status='cancelled').count(),
        }
        
        context.update({
            'session': self.session,
            'workshop': self.session.workshop,
            'stats': stats,
            'current_status_filter': self.request.GET.get('status', 'all'),
            'current_search': self.request.GET.get('search', ''),
            'status_choices': WorkshopRegistration.STATUS_CHOICES,
            'waitlist_info': self.session.get_waitlist_info(),
        })
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle participant status updates"""
        # Get the session object for POST requests
        self.session = get_object_or_404(
            WorkshopSession,
            id=self.kwargs['session_id'],
            workshop__instructor=self.request.user
        )
        
        action = request.POST.get('bulk_action') or request.POST.get('action')  # Support both parameter names
        registration_ids = request.POST.getlist('registration_ids')
        
        if not registration_ids:
            messages.warning(request, 'No participants selected.')
            return self.get(request, *args, **kwargs)
        
        registrations = WorkshopRegistration.objects.filter(
            id__in=registration_ids,
            session__workshop__instructor=request.user
        )
        
        if action == 'mark_attended':
            count = registrations.update(status='attended', attended=True)
            messages.success(request, f'Marked {count} participants as attended.')
        elif action == 'mark_no_show':
            count = registrations.update(status='no_show', attended=False)
            messages.success(request, f'Marked {count} participants as no-show.')
        elif action == 'move_to_registered':
            count = registrations.update(status='registered')
            messages.success(request, f'Moved {count} participants to registered status.')
        elif action == 'cancel_registration':
            count = registrations.update(status='cancelled')
            messages.success(request, f'Cancelled {count} registrations.')
        elif action == 'promote_from_waitlist':
            # Manual promotion from waitlist - only promote selected waitlisted registrations
            waitlisted_registrations = registrations.filter(status='waitlisted')
            
            if not waitlisted_registrations.exists():
                messages.warning(request, 'No waitlisted participants were selected.')
                return redirect('workshops:session_registrations', session_id=self.kwargs['session_id'])
            
            promoted_count = 0
            available_spots = self.session.max_participants - self.session.registrations.filter(
                status__in=['registered', 'promoted', 'attended']
            ).count()
            
            if available_spots <= 0:
                messages.warning(request, 'No spots available for promotion.')
                return redirect('workshops:session_registrations', session_id=self.kwargs['session_id'])
            
            # Promote selected waitlisted students up to available spots
            to_promote = waitlisted_registrations.order_by('waitlist_position', 'registration_date')[:available_spots]
            
            for registration in to_promote:
                from django.utils import timezone
                from datetime import timedelta
                
                # Update registration status
                promotion_deadline = timezone.now() + timedelta(hours=48)
                registration.status = 'promoted'
                registration.promoted_at = timezone.now()
                registration.promotion_expires_at = promotion_deadline
                registration.save()
                
                # Create promotion audit record
                from django.apps import apps
                WaitlistPromotion = apps.get_model('workshops', 'WaitlistPromotion')
                WaitlistPromotion.objects.create(
                    registration=registration,
                    promoted_by=request.user,
                    reason='manual_promotion',
                    expires_at=promotion_deadline
                )
                
                promoted_count += 1
                
                # Send notification
                from .notifications import WaitlistNotificationService
                promotion = registration.promotions.filter(
                    expired=False,
                    confirmed_at__isnull=True
                ).first()
                if promotion:
                    WaitlistNotificationService.send_promotion_notification(registration, promotion)
            
            # Update session registration count
            self.session.current_registrations = self.session.registrations.filter(
                status__in=['registered', 'promoted', 'attended', 'waitlisted']
            ).count()
            self.session.save(update_fields=['current_registrations'])
            
            if promoted_count > 0:
                messages.success(request, f'Promoted {promoted_count} participants from waitlist.')
            else:
                messages.warning(request, 'No participants could be promoted.')
                
        elif action == 'update_status':
            # Handle individual status updates (for AJAX requests)
            registration_id = request.POST.get('registration_id')
            status = request.POST.get('status')
            
            if registration_id and status:
                try:
                    registration = WorkshopRegistration.objects.get(
                        id=registration_id,
                        session__workshop__instructor=request.user
                    )
                    registration.status = status
                    if status == 'attended':
                        registration.attended = True
                    elif status == 'no_show':
                        registration.attended = False
                    registration.save()
                    
                    return JsonResponse({'success': True})
                except WorkshopRegistration.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Registration not found'})
            
            return JsonResponse({'success': False, 'error': 'Invalid parameters'})
        
        return redirect('workshops:session_registrations', session_id=self.kwargs['session_id'])


class WorkshopInterestView(CreateView):
    """Handle workshop interest requests for workshops without available sessions"""
    model = WorkshopInterest
    form_class = WorkshopInterestForm
    template_name = 'workshops/workshop_detail.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.workshop = get_object_or_404(Workshop, slug=kwargs['slug'], status='published')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['workshop'] = self.workshop
        kwargs['user'] = self.request.user if self.request.user.is_authenticated else None
        return kwargs
    
    def form_valid(self, form):
        # Check if user already has an interest request for this workshop
        if self.request.user.is_authenticated:
            existing_interest = WorkshopInterest.objects.filter(
                workshop=self.workshop,
                user=self.request.user,
                is_active=True
            ).first()
            
            if existing_interest:
                messages.info(
                    self.request, 
                    'You have already requested to be notified about this workshop. '
                    'We\'ll update your preferences.'
                )
                # Update existing interest with new data
                for field in ['email', 'preferred_timing', 'experience_level', 'special_requests', 'notify_immediately']:
                    setattr(existing_interest, field, form.cleaned_data[field])
                existing_interest.save()
                
                messages.success(
                    self.request,
                    'Your workshop request has been updated! We\'ll notify you when sessions become available.'
                )
                return redirect('workshops:detail', slug=self.workshop.slug)
        
        # Create new interest request
        form.save()
        messages.success(
            self.request,
            'Great! We\'ve recorded your interest in this workshop. '
            'You\'ll be notified as soon as sessions are scheduled.'
        )
        return redirect('workshops:detail', slug=self.workshop.slug)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'There was an error with your request. Please check the form and try again.'
        )
        return redirect('workshops:detail', slug=self.workshop.slug)
    
    def get_success_url(self):
        return reverse('workshops:detail', kwargs={'slug': self.workshop.slug})


class SessionMaterialsView(LoginRequiredMixin, TemplateView):
    """Manage materials for a specific session"""
    template_name = 'workshops/session_materials.html'
    
    def get_object(self):
        return get_object_or_404(
            WorkshopSession, 
            id=self.kwargs['session_id'],
            workshop__instructor=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.get_object()
        context['session'] = session
        context['workshop'] = session.workshop
        context['materials'] = session.materials.all().order_by('order', 'title')
        
        # Add material type choices for JavaScript
        context['material_types'] = WorkshopMaterial.TYPE_CHOICES
        context['access_timings'] = WorkshopMaterial.ACCESS_CHOICES
        
        return context


class MaterialDownloadView(LoginRequiredMixin, RedirectView):
    """Handle secure material downloads for registered participants"""
    
    def get_redirect_url(self, *args, **kwargs):
        material = get_object_or_404(WorkshopMaterial, id=kwargs['material_id'])
        
        # Check if user has access to this material
        if material.session:
            # Session-specific material - check registration
            registration = WorkshopRegistration.objects.filter(
                session=material.session,
                student=self.request.user,
                status__in=['registered', 'attended']
            ).first()
            
            if not material.can_be_accessed_by_registration(registration):
                messages.error(self.request, 'You do not have access to this material.')
                return reverse('workshops:detail', kwargs={'slug': material.workshop.slug})
        else:
            # Workshop-level material - check if user has any registration for this workshop
            has_registration = WorkshopRegistration.objects.filter(
                session__workshop=material.workshop,
                student=self.request.user,
                status__in=['registered', 'attended']
            ).exists()
            
            if material.requires_registration and not has_registration:
                messages.error(self.request, 'You must be registered for this workshop to access materials.')
                return reverse('workshops:detail', kwargs={'slug': material.workshop.slug})
        
        # Return file URL if accessible
        if material.file:
            return material.file.url
        elif material.external_url:
            return material.external_url
        else:
            messages.error(self.request, 'Material file not found.')
            return reverse('workshops:detail', kwargs={'slug': material.workshop.slug})


class CreateSessionMaterialView(LoginRequiredMixin, CreateView):
    """Create a new material for a session"""
    model = WorkshopMaterial
    form_class = WorkshopMaterialForm
    template_name = 'workshops/create_material.html'
    
    def get_session(self):
        return get_object_or_404(
            WorkshopSession,
            id=self.kwargs['session_id'],
            workshop__instructor=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.get_session()
        context['session'] = session
        context['workshop'] = session.workshop
        return context
    
    def form_valid(self, form):
        session = self.get_session()
        form.instance.workshop = session.workshop
        form.instance.session = session
        
        messages.success(
            self.request,
            f'Material "{form.instance.title}" has been uploaded successfully!'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('workshops:session_materials', kwargs={'session_id': self.kwargs['session_id']})


class EditSessionMaterialView(LoginRequiredMixin, UpdateView):
    """Edit an existing session material"""
    model = WorkshopMaterial
    form_class = WorkshopMaterialForm
    template_name = 'workshops/edit_material.html'
    pk_url_kwarg = 'material_id'
    
    def get_queryset(self):
        return WorkshopMaterial.objects.filter(
            session__workshop__instructor=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session'] = self.object.session
        context['workshop'] = self.object.workshop
        return context
    
    def form_valid(self, form):
        messages.success(
            self.request,
            f'Material "{form.instance.title}" has been updated successfully!'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('workshops:session_materials', kwargs={'session_id': self.object.session.id})


class DeleteSessionMaterialView(LoginRequiredMixin, DeleteView):
    """Delete a session material"""
    model = WorkshopMaterial
    pk_url_kwarg = 'material_id'
    template_name = 'workshops/delete_material.html'
    
    def get_queryset(self):
        return WorkshopMaterial.objects.filter(
            session__workshop__instructor=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session'] = self.object.session
        context['workshop'] = self.object.workshop
        return context
    
    def delete(self, request, *args, **kwargs):
        material = self.get_object()
        session_id = material.session.id
        material_title = material.title
        
        # Delete the file if it exists
        if material.file:
            material.file.delete()
        
        result = super().delete(request, *args, **kwargs)
        
        messages.success(
            request,
            f'Material "{material_title}" has been deleted successfully!'
        )
        
        return result
    
    def get_success_url(self):
        return reverse('workshops:session_materials', kwargs={'session_id': self.kwargs['session_id']})


class ParticipantMaterialsView(LoginRequiredMixin, TemplateView):
    """View materials for a specific session from participant perspective"""
    template_name = 'workshops/participant_materials.html'
    
    def get_object(self):
        return get_object_or_404(
            WorkshopSession, 
            id=self.kwargs['session_id']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.get_object()
        
        # Check if user is registered for this session
        registration = WorkshopRegistration.objects.filter(
            session=session,
            student=self.request.user,
            status__in=['registered', 'attended']
        ).first()
        
        if not registration:
            messages.error(self.request, 'You are not registered for this session.')
            return context
        
        # Get accessible materials based on timing
        now = timezone.now()
        session_start = session.start_datetime
        session_end = session.end_datetime
        
        accessible_materials = []
        for material in session.materials.all().order_by('order', 'title'):
            if material.can_be_accessed_by_registration(registration):
                accessible_materials.append(material)
        
        context.update({
            'session': session,
            'workshop': session.workshop,
            'registration': registration,
            'materials': accessible_materials,
            'now': now,
            'session_start': session_start,
            'session_end': session_end,
        })
        
        return context
