from abc import ABC, abstractmethod
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .forms import ContactForm, ProfileForm, FilterForm


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'stats': [
                {'icon': 'users', 'value': '2,500+', 'label': 'Students Taught', 'color': 'primary'},
                {'icon': 'book-open', 'value': '45', 'label': 'Courses Created', 'color': 'secondary'},
                {'icon': 'award', 'value': '98%', 'label': 'Success Rate', 'color': 'accent'},
                {'icon': 'calendar', 'value': '8+', 'label': 'Years Experience', 'color': 'info'},
            ],
            'featured_courses': [
                {
                    'title': 'Full-Stack Web Development',
                    'description': 'Learn modern web development with Python, Django, and JavaScript.',
                    'level': 'Intermediate',
                    'duration': '12 weeks',
                    'students': 450,
                    'rating': 4.8,
                    'price': 299,
                    'image': 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=400',
                },
                {
                    'title': 'Data Science Fundamentals',
                    'description': 'Master data analysis, visualization, and machine learning basics.',
                    'level': 'Beginner',
                    'duration': '8 weeks',
                    'students': 320,
                    'rating': 4.9,
                    'price': 199,
                    'image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400',
                },
                {
                    'title': 'Advanced Python Programming',
                    'description': 'Deep dive into Python with advanced concepts and best practices.',
                    'level': 'Advanced',
                    'duration': '10 weeks',
                    'students': 180,
                    'rating': 4.7,
                    'price': 399,
                    'image': 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=400',
                },
            ]
        })
        return context


class ComponentShowcaseView(TemplateView):
    template_name = 'core/components.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'cards': [
                {
                    'title': 'Basic Card',
                    'content': 'This is a simple card with basic styling.',
                    'variant': 'default',
                },
                {
                    'title': 'Featured Course',
                    'content': 'Advanced Python Programming - Learn advanced concepts and patterns.',
                    'variant': 'course',
                    'image': 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=300',
                    'price': 299,
                    'rating': 4.8,
                    'students': 1250,
                },
                {
                    'title': 'Success Story',
                    'content': 'Amazing course! Helped me land my dream job in tech.',
                    'variant': 'testimonial',
                    'author': 'Sarah Johnson',
                    'role': 'Software Engineer',
                    'avatar': 'https://images.unsplash.com/photo-1494790108755-2616b7c03e35?w=100',
                },
                {
                    'title': 'Workshop Alert',
                    'content': 'Join our upcoming AI workshop this weekend!',
                    'variant': 'notification',
                    'urgency': 'high',
                    'action_text': 'Register Now',
                },
            ],
            'buttons': [
                {'text': 'Primary Button', 'variant': 'primary', 'color': 'primary'},
                {'text': 'Secondary Button', 'variant': 'secondary', 'color': 'secondary'},
                {'text': 'Success Button', 'variant': 'primary', 'color': 'success'},
                {'text': 'Warning Button', 'variant': 'outline', 'color': 'warning'},
                {'text': 'Error Button', 'variant': 'primary', 'color': 'error'},
                {'text': 'Ghost Button', 'variant': 'ghost', 'color': 'neutral'},
            ],
            'badges': [
                {'text': 'New', 'color': 'primary'},
                {'text': 'Hot', 'color': 'error'},
                {'text': 'Popular', 'color': 'success'},
                {'text': 'Limited', 'color': 'warning'},
                {'text': 'Free', 'color': 'info'},
            ]
        })
        return context


class FormExampleView(FormView):
    template_name = 'core/forms.html'
    form_class = ContactForm
    success_url = reverse_lazy('core:forms')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'profile_form': ProfileForm(),
            'filter_form': FilterForm(),
        })
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Thank you for your message! We\'ll get back to you soon.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class InteractiveView(TemplateView):
    template_name = 'core/interactive.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tabs': [
                {'id': 'courses', 'title': 'My Courses', 'active': True},
                {'id': 'progress', 'title': 'Progress'},
                {'id': 'certificates', 'title': 'Certificates'},
                {'id': 'settings', 'title': 'Settings'},
            ],
            'notifications': [
                {'title': 'New course available', 'message': 'Advanced Django has been released!', 'type': 'info'},
                {'title': 'Assignment due', 'message': 'Python project due in 2 days', 'type': 'warning'},
                {'title': 'Certificate earned', 'message': 'Congratulations on completing Web Dev 101!', 'type': 'success'},
            ]
        })
        return context


# ============================================================================
# Base Checkout Views (Shared across apps)
# ============================================================================


class BaseCheckoutSuccessView(LoginRequiredMixin, TemplateView, ABC):
    """
    Abstract base view for handling successful Stripe checkout returns

    Subclasses must implement:
    - get_object_model(): Return the model class for the purchase object
    - get_object_id_kwarg(): Return the URL kwarg name for the object ID
    - get_redirect_url_name(): Return the URL name to redirect on error
    - get_context_extras(): Return additional context for the template
    """

    @abstractmethod
    def get_object_model(self):
        """Return the model class to query (e.g., WorkshopRegistration, CourseEnrollment, Order)"""
        pass

    @abstractmethod
    def get_object_id_kwarg(self):
        """Return the URL kwarg name for the object ID (e.g., 'registration_id', 'enrollment_id', 'order_id')"""
        pass

    @abstractmethod
    def get_redirect_url_name(self):
        """Return the URL name to redirect to on error (e.g., 'workshops:list', 'courses:list')"""
        pass

    @abstractmethod
    def get_context_extras(self, obj):
        """
        Return additional context dictionary for the template

        Args:
            obj: The retrieved object (registration, enrollment, or order)

        Returns:
            Dictionary of additional context variables
        """
        pass

    def get_object_queryset(self):
        """
        Return the queryset for retrieving the object
        Override this to add select_related/prefetch_related optimizations
        """
        return self.get_object_model().objects.all()

    def get_object_filter_kwargs(self, object_id):
        """
        Return filter kwargs for retrieving the object
        Override this to customize the filter (e.g., add additional conditions)
        """
        return {
            'id': object_id,
            'student': self.request.user
        }

    def perform_post_checkout_actions(self, obj):
        """
        Perform any additional actions after successful checkout
        Override this to add custom behavior (e.g., clear cart)

        Args:
            obj: The retrieved object
        """
        pass

    def get(self, request, *args, **kwargs):
        object_id = kwargs.get(self.get_object_id_kwarg())

        try:
            queryset = self.get_object_queryset()
            filter_kwargs = self.get_object_filter_kwargs(object_id)
            obj = queryset.get(**filter_kwargs)

            # Perform any post-checkout actions (e.g., clear cart)
            self.perform_post_checkout_actions(obj)

            # Build context
            context = self.get_context_data(**kwargs)
            context.update(self.get_context_extras(obj))

            return self.render_to_response(context)

        except self.get_object_model().DoesNotExist:
            messages.error(request, 'Item not found.')
            return redirect(self.get_redirect_url_name())


class BaseCheckoutCancelView(LoginRequiredMixin, TemplateView, ABC):
    """
    Abstract base view for handling cancelled Stripe checkout

    Subclasses must implement:
    - get_object_model(): Return the model class for the purchase object
    - get_object_id_kwarg(): Return the URL kwarg name for the object ID
    - get_redirect_url_name(): Return the URL name to redirect on error
    - get_context_extras(): Return additional context for the template (optional for redirect-based views)
    - get_cancel_message(): Return the message to display on cancellation
    """

    # Set to True if view should redirect instead of rendering a template
    redirect_on_cancel = False

    @abstractmethod
    def get_object_model(self):
        """Return the model class to query (e.g., WorkshopRegistration, CourseEnrollment, Order)"""
        pass

    @abstractmethod
    def get_object_id_kwarg(self):
        """Return the URL kwarg name for the object ID (e.g., 'registration_id', 'enrollment_id', 'order_id')"""
        pass

    @abstractmethod
    def get_redirect_url_name(self):
        """Return the URL name to redirect to on error or after cancellation (e.g., 'workshops:list', 'private_teaching:cart')"""
        pass

    @abstractmethod
    def get_cancel_message(self):
        """Return the warning message to display when payment is cancelled"""
        pass

    def get_context_extras(self, obj):
        """
        Return additional context dictionary for the template
        Only needed if redirect_on_cancel is False

        Args:
            obj: The retrieved object (registration, enrollment, or order)

        Returns:
            Dictionary of additional context variables
        """
        return {}

    def get_object_queryset(self):
        """
        Return the queryset for retrieving the object
        Override this to add select_related/prefetch_related optimizations
        """
        return self.get_object_model().objects.all()

    def get_object_filter_kwargs(self, object_id):
        """
        Return filter kwargs for retrieving the object
        Override this to customize the filter
        """
        return {
            'id': object_id,
            'student': self.request.user
        }

    def mark_payment_failed(self, obj):
        """
        Mark the payment as failed
        Override this if your model uses different field names or logic
        """
        obj.payment_status = 'failed'
        obj.save()

    def get(self, request, *args, **kwargs):
        object_id = kwargs.get(self.get_object_id_kwarg())

        try:
            queryset = self.get_object_queryset()
            filter_kwargs = self.get_object_filter_kwargs(object_id)
            obj = queryset.get(**filter_kwargs)

            # Mark payment as failed
            self.mark_payment_failed(obj)

            # Show warning message
            messages.warning(request, self.get_cancel_message())

            # Either redirect or render template
            if self.redirect_on_cancel:
                return redirect(self.get_redirect_url_name())
            else:
                context = self.get_context_data(**kwargs)
                context.update(self.get_context_extras(obj))
                return self.render_to_response(context)

        except self.get_object_model().DoesNotExist:
            messages.error(request, 'Item not found.')
            return redirect(self.get_redirect_url_name())
