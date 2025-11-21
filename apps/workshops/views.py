from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, RedirectView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.core.paginator import Paginator

from apps.core.views import (
    BaseCheckoutSuccessView, BaseCheckoutCancelView, SearchableListViewMixin,
    SuccessMessageMixin, SetUserFieldMixin, UserFilterMixin
)
from .models import (
    Workshop, WorkshopCategory, WorkshopSession,
    WorkshopRegistration, WorkshopMaterial, WorkshopInterest,
    WorkshopTermsAndConditions, TermsAcceptance
)
from .forms import WorkshopRegistrationForm, WorkshopForm, WorkshopSessionForm, WorkshopFilterForm, WorkshopInterestForm, WorkshopMaterialForm
from .mixins import InstructorRequiredMixin
from .notifications import WorkshopInterestNotificationService


def create_terms_acceptance(registration, request_or_session_data):
    """
    Create a TermsAcceptance record for a workshop registration.

    Args:
        registration: WorkshopRegistration object
        request_or_session_data: Either a Django request object or a dict with session data
                                  containing 'terms_accepted' with version, ip_address, user_agent

    Returns:
        TermsAcceptance object or None if terms data not found
    """
    # Extract terms acceptance data
    if hasattr(request_or_session_data, 'session'):
        # It's a request object
        terms_data = request_or_session_data.session.get('terms_accepted')
        ip_address = request_or_session_data.META.get('REMOTE_ADDR', '')
        user_agent = request_or_session_data.META.get('HTTP_USER_AGENT', '')
    else:
        # It's a dict with session data
        terms_data = request_or_session_data.get('terms_accepted')
        ip_address = terms_data.get('ip_address', '') if terms_data else ''
        user_agent = terms_data.get('user_agent', '') if terms_data else ''

    if not terms_data:
        return None

    # Get the terms version
    version_number = terms_data.get('version')
    if not version_number:
        return None

    try:
        terms_version = WorkshopTermsAndConditions.objects.get(version=version_number)
    except WorkshopTermsAndConditions.DoesNotExist:
        # If specific version not found, use current version
        terms_version = WorkshopTermsAndConditions.objects.filter(is_current=True).first()
        if not terms_version:
            return None

    # Create TermsAcceptance record
    terms_acceptance = TermsAcceptance.objects.create(
        student=registration.student,
        registration=registration,
        terms_version=terms_version,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return terms_acceptance


class WorkshopListView(SearchableListViewMixin, ListView):
    """Display list of workshops with filtering and search"""
    model = Workshop
    template_name = 'workshops/workshop_list.html'
    context_object_name = 'workshops'
    paginate_by = 12

    # Configure SearchableListViewMixin
    search_fields = ['title', 'description', 'tags']
    filter_mappings = {
        'difficulty': 'difficulty_level',
        'delivery_method': 'delivery_method',
        'price': lambda qs, val: qs.filter(is_free=True) if val == 'free' else qs.filter(is_free=False) if val == 'paid' else qs,
    }
    sort_options = {
        'featured': ('-is_featured', '-created_at'),
        'newest': '-created_at',
        'price_low': 'price',
        'price_high': '-price',
        'rating': '-average_rating',
    }
    default_sort = 'featured'

    def dispatch(self, request, *args, **kwargs):
        # If user is logged in and is a student (not a teacher), redirect to their dashboard
        # UNLESS they explicitly want to browse workshops (via ?browse=all query param)
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            profile = request.user.profile
            # Allow students to browse if they have the browse parameter
            browse_param = request.GET.get('browse')
            # Redirect students to their dashboard (but not teachers or if browsing)
            if profile.is_student and not profile.is_teacher and browse_param != 'all':
                return redirect('workshops:student_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Workshop.objects.filter(status='published').select_related(
            'instructor', 'category'
        ).prefetch_related('sessions')

        # Category filtering from URL kwargs
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Apply search, filters, and sorting from mixin
        queryset = self.filter_queryset(queryset)

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
        
        # Check if user is registered for this workshop (for messaging button)
        user_is_registered = False
        if self.request.user.is_authenticated:
            user_is_registered = WorkshopRegistration.objects.filter(
                student=self.request.user,
                session__workshop=workshop,
                status__in=['registered', 'promoted', 'attended']
            ).exists()

        # Get current terms for T&Cs modal
        from .models import WorkshopTermsAndConditions
        current_terms = WorkshopTermsAndConditions.objects.filter(is_current=True).first()

        context.update({
            'upcoming_sessions': upcoming_sessions,
            'pre_materials': pre_materials,
            'session_materials': session_materials,
            'related_workshops': related_workshops,
            'similar_workshops_with_sessions': similar_workshops_with_sessions,
            'user_is_registered': user_is_registered,
            'current_terms': current_terms,
        })

        # Add cart session IDs for logged-in users
        if self.request.user.is_authenticated:
            from .cart import WorkshopCartManager
            cart_manager = WorkshopCartManager(self.request)
            cart = cart_manager.get_cart()
            if cart:
                context['cart_session_ids'] = list(
                    cart.workshop_items.values_list('session_id', flat=True)
                )
            else:
                context['cart_session_ids'] = []
        else:
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

        # Create registration object
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

        # WAITLIST FLOW: If session is full, add to waitlist directly (no payment)
        if self.session.is_full:
            if self.session.waitlist_enabled:
                registration.status = 'waitlisted'
                registration.payment_status = 'not_required'  # Payment only required when promoted
                registration.save()

                student_name = registration.child_profile.full_name if registration.child_profile else 'You'
                messages.success(
                    self.request,
                    f'{student_name} {"has" if registration.child_profile else "have"} been added to the waitlist for this workshop.'
                )
                return redirect('workshops:registration_confirm', registration_id=registration.id)
            else:
                messages.error(
                    self.request,
                    'Sorry, this workshop session is full and waitlist is not available.'
                )
                return redirect('workshops:detail', slug=self.workshop.slug)

        # NORMAL FLOW: Session has capacity - use cart for payment flow
        # Store terms acceptance in session for later tracking
        from .models import WorkshopTermsAndConditions
        current_terms = WorkshopTermsAndConditions.objects.filter(is_current=True).first()
        if current_terms:
            # Store terms version and user agent for later acceptance tracking
            self.request.session['terms_accepted'] = {
                'version': current_terms.version,
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self.request.META.get('REMOTE_ADDR', ''),
            }

        # Get child profile ID if guardian
        child_profile_id = None
        if registration.child_profile:
            child_profile_id = str(registration.child_profile.id)

        # Add to cart with registration data
        from .cart import WorkshopCartManager
        cart_manager = WorkshopCartManager(self.request)

        # Prepare registration data
        registration_data = {
            'email': registration.email,
            'phone': registration.phone or '',
            'emergency_contact': registration.emergency_contact or '',
            'experience_level': registration.experience_level or '',
            'expectations': registration.expectations or '',
            'special_requirements': registration.special_requirements or '',
        }

        success, message = cart_manager.add_session(
            str(self.session.id),
            child_profile_id=child_profile_id,
            registration_data=registration_data
        )

        if success:
            messages.success(self.request, message)
            return redirect('workshops:cart')
        else:
            messages.error(self.request, message)
            return redirect('workshops:detail', slug=self.workshop.slug)

        # OLD DIRECT REGISTRATION CODE - Keeping for reference but now using cart flow
        """
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

        # Check if workshop requires payment (code moved to cart checkout process)
        # All workshop registration now goes through cart for consistency
        """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import WorkshopTermsAndConditions

        # Get current terms for display in modal
        current_terms = WorkshopTermsAndConditions.objects.filter(is_current=True).first()

        context.update({
            'workshop': self.workshop,
            'session': self.session,
            'is_waitlist': self.session.is_full,
            'current_terms': current_terms,
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
        """Handle payment initiation for promoted registrations"""
        registration = self.get_object()

        if registration.status == 'promoted':
            # Check if workshop requires payment
            if registration.session.workshop.price > 0:
                # Set payment fields
                registration.payment_amount = registration.session.workshop.price
                registration.payment_status = 'pending'
                registration.save(update_fields=['payment_amount', 'payment_status'])

                # Create Stripe checkout session
                from apps.payments.stripe_service import create_checkout_session
                from decimal import Decimal

                try:
                    # Build success and cancel URLs
                    success_url = request.build_absolute_uri(
                        reverse('workshops:checkout_success', kwargs={'registration_id': registration.id})
                    ) + '?session_id={CHECKOUT_SESSION_ID}'
                    cancel_url = request.build_absolute_uri(
                        reverse('workshops:checkout_cancel', kwargs={'registration_id': registration.id})
                    )

                    # Prepare item details
                    session_date_str = registration.session.start_datetime.strftime("%B %d, %Y at %I:%M %p")
                    item_name = registration.session.workshop.title
                    item_description = f'Promoted from waitlist - Session on {session_date_str}'

                    # Create Stripe checkout session
                    checkout_session = create_checkout_session(
                        amount=registration.session.workshop.price,
                        student=request.user,
                        teacher=registration.session.workshop.instructor,
                        domain='workshops',
                        success_url=success_url,
                        cancel_url=cancel_url,
                        item_name=item_name,
                        item_description=item_description,
                        metadata={
                            'registration_id': str(registration.id),
                            'workshop_id': str(registration.session.workshop.id),
                            'session_id': str(registration.session.id),
                            'user_id': str(request.user.id),
                            'type': 'workshop_promotion',
                        }
                    )

                    # Save Stripe checkout session ID
                    registration.stripe_checkout_session_id = checkout_session.id
                    registration.save(update_fields=['stripe_checkout_session_id'])

                    # Redirect to Stripe checkout
                    return redirect(checkout_session.url)

                except Exception as e:
                    messages.error(request, f'Payment processing error: {str(e)}')
                    return redirect('workshops:registration_confirm', registration_id=registration.id)
            else:
                # Free workshop - complete immediately
                registration.status = 'registered'
                registration.payment_status = 'not_required'
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

                messages.success(request, 'Registration completed! You are now registered for the workshop.')

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


class WorkshopCheckoutSuccessView(BaseCheckoutSuccessView):
    """Handle return from Stripe after successful checkout"""
    template_name = 'workshops/checkout_success.html'

    def get_object_model(self):
        return WorkshopRegistration

    def get_object_id_kwarg(self):
        return 'registration_id'

    def get_redirect_url_name(self):
        return 'workshops:list'

    def get_object_queryset(self):
        return WorkshopRegistration.objects.select_related('session__workshop')

    def perform_post_checkout_actions(self, obj):
        """Handle promotion confirmation for waitlist promotions"""
        registration = obj

        # Check if this is a promoted registration that needs confirmation
        if registration.status == 'promoted' and registration.payment_status == 'completed':
            # Update status to registered
            registration.status = 'registered'
            registration.save(update_fields=['status'])

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

    def get_context_extras(self, obj):
        return {
            'registration': obj,
            'workshop': obj.session.workshop,
            'session': obj.session,
        }


class WorkshopCheckoutCancelView(BaseCheckoutCancelView):
    """Handle cancelled checkout"""
    template_name = 'workshops/checkout_cancel.html'

    def get_object_model(self):
        return WorkshopRegistration

    def get_object_id_kwarg(self):
        return 'registration_id'

    def get_redirect_url_name(self):
        return 'workshops:list'

    def get_object_queryset(self):
        return WorkshopRegistration.objects.select_related('session__workshop')

    def get_cancel_message(self):
        return 'Payment was cancelled. You can try again from your registrations page.'

    def get_context_extras(self, obj):
        return {
            'registration': obj,
            'workshop': obj.session.workshop,
            'session': obj.session,
        }


class RegistrationCancelView(LoginRequiredMixin, View):
    """Cancel a workshop registration"""

    def get(self, request, *args, **kwargs):
        """Handle GET request - process cancellation immediately"""
        return self._cancel_registration(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle POST request - process cancellation"""
        return self._cancel_registration(request, *args, **kwargs)

    def _cancel_registration(self, request, *args, **kwargs):
        """Common cancellation logic"""
        registration_id = kwargs.get('registration_id')

        try:
            registration = WorkshopRegistration.objects.select_related(
                'session__workshop'
            ).get(
                id=registration_id,
                student=request.user
            )
        except WorkshopRegistration.DoesNotExist:
            messages.error(request, 'Registration not found.')
            return redirect('workshops:my_registrations')

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

            # Check if eligible for refund (7+ days before workshop)
            from django.utils import timezone
            from datetime import timedelta

            days_until_workshop = (registration.session.start_datetime - timezone.now()).days
            refund_processed = False

            print(f"[REFUND DEBUG] Days until workshop: {days_until_workshop}", flush=True)
            print(f"[REFUND DEBUG] Payment status: {registration.payment_status}", flush=True)
            print(f"[REFUND DEBUG] Eligible for refund: {days_until_workshop >= 7 and registration.payment_status in ['paid', 'completed']}", flush=True)

            if days_until_workshop >= 7 and registration.payment_status in ['paid', 'completed']:
                # Eligible for refund - process it automatically
                try:
                    from apps.payments.models import StripePayment
                    import stripe
                    from django.conf import settings

                    stripe.api_key = settings.STRIPE_SECRET_KEY

                    # Find the StripePayment record using payment_intent_id from registration
                    print(f"[REFUND DEBUG] Looking for StripePayment: student={request.user.email}, payment_intent={registration.stripe_payment_intent_id}", flush=True)

                    stripe_payment = None
                    if registration.stripe_payment_intent_id:
                        stripe_payment = StripePayment.objects.filter(
                            stripe_payment_intent_id=registration.stripe_payment_intent_id,
                            status='completed'
                        ).first()

                    print(f"[REFUND DEBUG] StripePayment found: {stripe_payment is not None}", flush=True)

                    if stripe_payment:
                        print(f"[REFUND DEBUG] Processing Stripe refund for payment_intent: {stripe_payment.stripe_payment_intent_id}", flush=True)
                        # Process refund via Stripe API
                        refund = stripe.Refund.create(
                            payment_intent=stripe_payment.stripe_payment_intent_id,
                            amount=int(registration.payment_amount * 100),  # Convert to cents
                        )

                        # Update our record
                        stripe_payment.mark_refunded(
                            refund_amount=registration.payment_amount,
                            stripe_refund_id=refund.id
                        )

                        refund_processed = True
                        messages.success(
                            request,
                            'You have cancelled with 7 or more days notice. Your registration has been cancelled and a refund will be issued.'
                        )
                    else:
                        messages.success(request, 'Your registration has been cancelled.')

                except Exception as e:
                    print(f"Failed to process automatic refund: {e}")
                    messages.warning(
                        request,
                        'Your registration has been cancelled. Please contact support regarding your refund.'
                    )
            else:
                # Not eligible for refund
                if days_until_workshop < 7:
                    messages.warning(
                        request,
                        'Unfortunately, you have not given at least 7 days notice to cancel your registration. Your registration has been cancelled but no refund is possible.'
                    )
                else:
                    messages.success(request, 'Your registration has been cancelled.')

            # Send cancellation notification to instructor
            try:
                from .notifications import InstructorNotificationService
                InstructorNotificationService.send_registration_cancelled_notification(registration)
            except Exception as e:
                print(f"Failed to send instructor cancellation notification: {e}")
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
        # Show all registrations except those with pending payment
        # Cart-based registrations have payment_status='completed' after webhook processes
        return WorkshopRegistration.objects.filter(
            student=self.request.user
        ).filter(
            Q(payment_status='completed') |
            Q(payment_status='not_required') |
            Q(payment_status__isnull=True)  # Legacy registrations without payment_status
        ).select_related(
            'session__workshop__instructor',
            'session__workshop__category',
            'child_profile'
        ).order_by('-paid_at', '-registration_date')  # Most recently paid first

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add current time for date comparisons in template
        from django.utils import timezone
        context['now'] = timezone.now()

        # Calculate registration counts by status
        all_registrations = self.get_queryset()
        context['confirmed_count'] = all_registrations.filter(status='registered').count()
        context['waitlisted_count'] = all_registrations.filter(status='waitlisted').count()
        context['attended_count'] = all_registrations.filter(attended=True).count()

        return context


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

        # Get interest requests for instructor's workshops
        interest_requests = WorkshopInterest.objects.filter(
            workshop__instructor=user,
            is_active=True
        ).select_related('workshop', 'user').order_by('-created_at')[:10]

        # Get workshop interest summary (count per workshop)
        from django.db.models import Count
        workshop_interest_summary = WorkshopInterest.objects.filter(
            workshop__instructor=user,
            is_active=True
        ).values('workshop__id', 'workshop__title', 'workshop__slug').annotate(
            total_interested=Count('id'),
            waiting_notification=Count('id', filter=Q(has_been_notified=False))
        ).order_by('-waiting_notification', '-total_interested')[:5]

        context.update({
            'workshops': workshops,
            'upcoming_sessions': upcoming_sessions,
            'recent_registrations': recent_registrations,
            'interest_requests': interest_requests,
            'workshop_interest_summary': workshop_interest_summary,
            'stats': {
                'total_workshops': len(workshops),
                'published_workshops': len([w for w in workshops if w.status == 'published']),
                'total_sessions': WorkshopSession.objects.filter(workshop__instructor=user).count(),
                'total_registrations': WorkshopRegistration.objects.filter(session__workshop__instructor=user).count(),
                'total_interest_requests': WorkshopInterest.objects.filter(workshop__instructor=user, is_active=True).count(),
            }
        })
        return context


class InstructorWorkshopsView(UserFilterMixin, InstructorRequiredMixin, ListView):
    """List of instructor's workshops. Uses UserFilterMixin."""
    model = Workshop
    template_name = 'workshops/instructor_workshops.html'
    context_object_name = 'workshops'
    paginate_by = 12
    user_field_name = 'instructor'

    def get_queryset(self):
        # UserFilterMixin automatically filters by instructor=self.request.user
        return super().get_queryset().select_related('category').prefetch_related('sessions').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get ALL workshops for stats (not just current page)
        all_workshops = Workshop.objects.filter(
            instructor=self.request.user
        ).prefetch_related('sessions')

        # Calculate total sessions and registrations across ALL workshops
        total_sessions = sum(workshop.sessions.count() for workshop in all_workshops)
        total_registrations = WorkshopRegistration.objects.filter(
            session__workshop__instructor=self.request.user,
            status__in=['registered', 'attended', 'waitlisted']
        ).count()

        context['total_sessions'] = total_sessions
        context['total_registrations'] = total_registrations

        return context


class CreateWorkshopView(SuccessMessageMixin, SetUserFieldMixin, LoginRequiredMixin, CreateView):
    """Create new workshop. Uses SuccessMessageMixin and SetUserFieldMixin."""
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/workshop_form.html'
    success_message = 'Workshop created successfully! Now add sessions to schedule when it will run.'
    user_field_name = 'instructor'

    def get_success_url(self):
        # Redirect to session management for the newly created workshop
        return reverse('workshops:manage_sessions', kwargs={'slug': self.object.slug})


class EditWorkshopView(SuccessMessageMixin, UserFilterMixin, LoginRequiredMixin, UpdateView):
    """Edit existing workshop. Uses SuccessMessageMixin and UserFilterMixin."""
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/workshop_form.html'
    success_message = 'Workshop updated successfully!'
    user_field_name = 'instructor'

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


class AttendanceSheetView(LoginRequiredMixin, TemplateView):
    """Generate printable attendance sheet for workshop session"""
    template_name = 'workshops/attendance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get session and verify instructor access
        session = get_object_or_404(
            WorkshopSession,
            id=self.kwargs['session_id'],
            workshop__instructor=self.request.user
        )

        # Get all registered and attended participants (not cancelled/no-show)
        registrations = WorkshopRegistration.objects.filter(
            session=session,
            status__in=['registered', 'attended', 'promoted']
        ).select_related(
            'student',
            'student__profile',
            'child_profile'
        ).order_by('student__last_name', 'student__first_name')

        context['session'] = session
        context['registrations'] = registrations

        return context


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

                # Send confirmation email for updated interest
                try:
                    WorkshopInterestNotificationService.send_interest_confirmation(existing_interest)
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send interest confirmation email: {str(e)}")

                messages.success(
                    self.request,
                    'Your workshop request has been updated! Check your email for confirmation.'
                )
                return redirect('workshops:detail', slug=self.workshop.slug)

        # Create new interest request
        interest = form.save()

        # Send confirmation email for new interest
        try:
            WorkshopInterestNotificationService.send_interest_confirmation(interest)
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send interest confirmation email: {str(e)}")

        messages.success(
            self.request,
            'Great! We\'ve recorded your interest in this workshop. '
            'Check your email for confirmation.'
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


class CreateSessionMaterialView(InstructorRequiredMixin, CreateView):
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Set initial values for checkboxes and order
        if not kwargs.get('instance'):
            kwargs['initial'] = {
                'is_downloadable': True,
                'requires_registration': True,
                'access_timing': 'always',
                'order': 0,
            }
        return kwargs

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

    def form_invalid(self, form):
        """Add debugging for form errors"""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Material upload form errors: {form.errors}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('workshops:session_materials', kwargs={'session_id': self.kwargs['session_id']})


class EditSessionMaterialView(InstructorRequiredMixin, UpdateView):
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


class DeleteSessionMaterialView(InstructorRequiredMixin, DeleteView):
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


# ==================== Cart Views ====================

from django.views.generic import TemplateView, View
from .cart import WorkshopCartManager


class WorkshopCartView(LoginRequiredMixin, TemplateView):
    """Display workshop cart"""
    template_name = 'workshops/cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_manager = WorkshopCartManager(self.request)
        context.update(cart_manager.get_cart_context())
        return context


class AddToCartView(LoginRequiredMixin, View):
    """Add workshop session to cart"""

    def post(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        child_profile_id = request.POST.get('child_profile_id')
        notes = request.POST.get('notes', '')

        # Store terms acceptance in session for later tracking
        from .models import WorkshopTermsAndConditions
        current_terms = WorkshopTermsAndConditions.objects.filter(is_current=True).first()
        if current_terms:
            request.session['terms_accepted'] = {
                'version': current_terms.version,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': request.META.get('REMOTE_ADDR', ''),
            }

        cart_manager = WorkshopCartManager(request)
        success, message = cart_manager.add_session(
            session_id,
            child_profile_id=child_profile_id,
            notes=notes
        )

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        # Redirect back to workshop detail or cart
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/workshops/'))
        return redirect(next_url)


class RemoveFromCartView(LoginRequiredMixin, View):
    """Remove workshop session from cart"""

    def post(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        cart_manager = WorkshopCartManager(request)

        success, message = cart_manager.remove_session(session_id)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('workshops:cart')


class ClearWorkshopCartView(LoginRequiredMixin, View):
    """Clear all workshop items from cart"""

    def post(self, request, *args, **kwargs):
        cart_manager = WorkshopCartManager(request)

        success, message = cart_manager.clear_workshop_cart()

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('workshops:cart')


class CheckoutSuccessView(LoginRequiredMixin, TemplateView):
    """Stripe payment successful for cart checkout"""
    template_name = 'workshops/cart_checkout_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = self.request.GET.get('session_id')
        context['session_id'] = session_id

        # Get recent registrations for this user
        # (webhook may have already created them)
        recent_registrations = WorkshopRegistration.objects.filter(
            student=self.request.user,
            payment_status='completed'
        ).select_related('session__workshop').order_by('-paid_at')[:5]

        context['registrations'] = recent_registrations
        return context


class CheckoutCancelView(LoginRequiredMixin, View):
    """Stripe payment cancelled for cart checkout"""

    def get(self, request):
        messages.warning(request, 'Payment was cancelled. Your cart items are still saved.')
        return redirect('workshops:cart')


class ProcessCartPaymentView(LoginRequiredMixin, View):
    """Process workshop cart payment - create Stripe checkout session"""

    def post(self, request, *args, **kwargs):
        """Handle checkout submission - create Stripe checkout session"""
        from apps.payments.stripe_service import create_checkout_session
        from decimal import Decimal

        cart_manager = WorkshopCartManager(request)
        cart = cart_manager.get_cart()

        if not cart or cart.workshop_items.count() == 0:
            messages.error(request, 'Your cart is empty')
            return redirect('workshops:cart')

        # Get cart items
        workshop_items = cart.workshop_items.select_related(
            'session__workshop__instructor'
        ).all()

        # Calculate total
        total_amount = sum(item.total_price for item in workshop_items)

        if total_amount == 0:
            # Free workshops - create registrations directly
            for item in workshop_items:
                registration = WorkshopRegistration.objects.create(
                    session=item.session,
                    student=request.user,
                    email=request.user.email,
                    child_profile=item.child_profile,
                    status='registered',
                    payment_status='not_required',
                    payment_amount=0
                )

                # Create terms acceptance record
                create_terms_acceptance(registration, request)

            # Clear cart
            cart.workshop_items.all().delete()

            messages.success(request, 'Successfully registered for workshop sessions!')
            return redirect('workshops:student_dashboard')

        # Paid workshops - use Stripe checkout
        try:
            # Build line items for Stripe (each workshop as separate line item)
            line_items = []
            for item in workshop_items:
                line_items.append({
                    'name': item.session.workshop.title,
                    'description': item.session.start_datetime.strftime('%b %d, %Y at %I:%M %p'),
                    'amount': item.price
                })

            # Store cart item IDs in metadata for webhook processing
            cart_item_ids = [str(item.id) for item in workshop_items]

            # Get first instructor (for commission calculation)
            first_teacher = workshop_items[0].session.workshop.instructor if workshop_items else None

            # Prepare metadata including terms acceptance
            metadata = {
                'cart_item_ids': ','.join(cart_item_ids),
                'item_count': len(cart_item_ids),
            }

            # Include terms acceptance data if available
            terms_data = request.session.get('terms_accepted')
            if terms_data:
                metadata['terms_version'] = terms_data.get('version')
                metadata['terms_ip_address'] = terms_data.get('ip_address', '')
                metadata['terms_user_agent'] = terms_data.get('user_agent', '')

            # Create Stripe checkout session with multiple line items
            from apps.payments.stripe_service import create_checkout_session_with_items
            checkout_session = create_checkout_session_with_items(
                line_items=line_items,
                student=request.user,
                teacher=first_teacher,
                domain='workshops',
                success_url=request.build_absolute_uri(
                    reverse('workshops:cart_checkout_success')
                ) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(
                    reverse('workshops:cart_checkout_cancel')
                ),
                metadata=metadata
            )

            # Redirect to Stripe
            return redirect(checkout_session.url)

        except Exception as e:
            messages.error(request, f'Payment error: {str(e)}. Please try again or contact support.')
            return redirect('workshops:cart')


class WorkshopTermsView(TemplateView):
    """Display current Workshop Terms and Conditions"""
    template_name = 'workshops/terms_and_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import WorkshopTermsAndConditions

        # Get current terms
        current_terms = WorkshopTermsAndConditions.objects.filter(is_current=True).first()
        context['terms'] = current_terms

        return context
