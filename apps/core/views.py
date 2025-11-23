from abc import ABC, abstractmethod
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from .forms import ContactForm, ProfileForm, FilterForm


class AboutView(TemplateView):
    """Public About page showcasing platform mission and founder"""
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # FAQ data
        context['faqs'] = [
            {
                'question': 'What types of lessons do you offer?',
                'answer': 'We offer three main types of learning: <strong>Private Lessons</strong> - personalized one-on-one instruction tailored to your goals; <strong>Group Workshops</strong> - collaborative sessions covering specific topics or techniques; and <strong>Online Courses</strong> - self-paced structured learning with video lessons and materials.'
            },
            {
                'question': 'How do group workshops work?',
                'answer': 'Workshops are scheduled group sessions focused on specific topics like technique, ensemble playing, or music theory. Browse available workshops, register for ones that interest you, and pay online. You\'ll receive confirmation and details about the workshop location (online or in-person). Workshops are a great way to learn with other musicians in a collaborative environment.'
            },
            {
                'question': 'What are online courses and how do they work?',
                'answer': 'Online courses are self-paced learning programs with structured curriculum. Each course includes video lessons, practice materials, assignments, and progress tracking. You can work through the content at your own pace, on your own schedule. Once enrolled, you have access to all course materials and can track your progress through each module.'
            },
            {
                'question': 'How do I get started with private lessons?',
                'answer': 'First, create an account and complete your profile. Then apply to study with a teacher by visiting their profile. Once accepted, you can request lessons at times that work for you. Your teacher will review and approve your lesson requests, after which you can pay and confirm your booking.'
            },
            {
                'question': 'Are lessons available online or in-person?',
                'answer': 'Yes! For <strong>private lessons</strong>, each teacher sets their preferences - online via Zoom, in-person at their studio, or at your location. <strong>Workshops</strong> can be held online or in-person, as specified in the workshop details. <strong>Online courses</strong> are entirely self-paced and accessible from anywhere.'
            },
            {
                'question': 'What is your cancellation policy?',
                'answer': 'For <strong>private lessons</strong>, students can request to cancel or reschedule by submitting a request to their teacher. Cancellations made 48+ hours in advance may be eligible for a refund (minus platform fees). For <strong>workshops</strong>, cancellation policies are listed on each workshop page. <strong>Course</strong> enrollments are generally non-refundable once you\'ve accessed the content.'
            },
            {
                'question': 'How does payment work?',
                'answer': 'All payments are processed securely through Stripe. For <strong>private lessons</strong>, you pay after your teacher approves your lesson request. For <strong>workshops and courses</strong>, payment is required during registration. A small platform fee helps support platform infrastructure and ongoing development.'
            },
            {
                'question': 'Can I register my child for lessons, workshops, or courses?',
                'answer': 'Yes! Parents and guardians can create child profiles and register them for any of our offerings. For private lessons, you apply on behalf of your child. For workshops and courses, you can enroll them during registration. Simply add a child profile in your account settings.'
            },
            {
                'question': 'What resources and materials are included?',
                'answer': 'For <strong>private lessons</strong>, teachers share documents, sheet music, and practice materials that stay in your document library. <strong>Workshops</strong> often include handouts and follow-up materials. <strong>Online courses</strong> include comprehensive video lessons, downloadable materials, practice exercises, and sometimes quizzes or assignments - all accessible anytime.'
            },
            {
                'question': 'Do you offer exam preparation?',
                'answer': 'Yes! Teachers can register students for music exams including ABRSM, Trinity, and other exam boards through the private lessons program. We help track your preparation, repertoire pieces, and exam registration details all in one place.'
            },
        ]

        return context


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


class SearchableListViewMixin:
    """
    Mixin for list views that provides common search, filtering, and sorting functionality.

    Subclasses should define:
    - search_fields: List of field names to search (e.g., ['title', 'description'])
    - filter_mappings: Dict mapping GET params to queryset filters (e.g., {'category': 'category'})
    - sort_options: Dict mapping sort params to queryset order_by values (e.g., {'title': 'title'})
    - default_sort: Default sort order (e.g., 'title')

    Usage example:
        class MyListView(SearchableListViewMixin, ListView):
            search_fields = ['title', 'description']
            filter_mappings = {'category': 'category', 'status': 'status'}
            sort_options = {'title': 'title', 'date': '-created_at'}
            default_sort = 'title'
    """

    # Configuration attributes (override in subclass)
    search_fields = []
    filter_mappings = {}
    sort_options = {}
    default_sort = None

    def apply_search_filter(self, queryset):
        """Apply search filtering based on 'search' GET parameter"""
        search_query = self.request.GET.get('search', '').strip()

        if search_query and self.search_fields:
            # Build Q object for OR search across all search fields
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_query})
            queryset = queryset.filter(q_objects)

        return queryset

    def apply_get_filters(self, queryset):
        """Apply filters based on GET parameters and filter_mappings"""
        for param_name, queryset_filter in self.filter_mappings.items():
            param_value = self.request.GET.get(param_name)

            if param_value:
                # Support both simple filters and callable filters
                if callable(queryset_filter):
                    queryset = queryset_filter(queryset, param_value)
                else:
                    queryset = queryset.filter(**{queryset_filter: param_value})

        return queryset

    def apply_sorting(self, queryset):
        """Apply sorting based on 'sort' GET parameter"""
        sort_param = self.request.GET.get('sort', self.default_sort)

        if sort_param and sort_param in self.sort_options:
            order_by = self.sort_options[sort_param]
            # Support both single field and tuple/list of fields
            if isinstance(order_by, (tuple, list)):
                queryset = queryset.order_by(*order_by)
            else:
                queryset = queryset.order_by(order_by)
        elif self.default_sort:
            # Apply default sort if no valid sort param provided
            default_order = self.sort_options.get(self.default_sort, self.default_sort)
            if isinstance(default_order, (tuple, list)):
                queryset = queryset.order_by(*default_order)
            else:
                queryset = queryset.order_by(default_order)

        return queryset

    def filter_queryset(self, queryset):
        """
        Apply all filters to the queryset.
        Override this method if you need custom filtering logic.
        """
        queryset = self.apply_search_filter(queryset)
        queryset = self.apply_get_filters(queryset)
        queryset = self.apply_sorting(queryset)
        return queryset


# ============================================================================
# VIEW MIXINS FOR COMMON PATTERNS (Phase 2 Refactoring)
# ============================================================================


class SuccessMessageMixin:
    """
    Mixin to automatically show success messages after form submission.

    Set success_message attribute on your view:
        success_message = "Item created successfully!"

    Or use template strings with object fields:
        success_message = "{title} was created successfully!"

    Usage:
        class MyCreateView(SuccessMessageMixin, CreateView):
            success_message = "Course '{title}' created successfully!"
    """
    success_message = ""

    def get_success_message(self, cleaned_data=None):
        """
        Get the success message, optionally formatting with cleaned_data or object fields
        Override this method for dynamic messages.
        """
        if not self.success_message:
            return ""

        # Try to format with object if available
        if hasattr(self, 'object') and self.object:
            try:
                return self.success_message.format(**self.object.__dict__)
            except (AttributeError, KeyError):
                pass

        # Try to format with cleaned_data
        if cleaned_data:
            try:
                return self.success_message.format(**cleaned_data)
            except (AttributeError, KeyError):
                pass

        return self.success_message

    def form_valid(self, form):
        response = super().form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response


class SetUserFieldMixin:
    """
    Mixin to automatically set a user field on form submission.

    Set user_field_name attribute (defaults to 'instructor'):
        user_field_name = 'teacher'  # or 'author', 'created_by', etc.

    Usage:
        class MyCreateView(SetUserFieldMixin, CreateView):
            user_field_name = 'instructor'  # Will set form.instance.instructor = request.user
    """
    user_field_name = 'instructor'  # Default field name

    def form_valid(self, form):
        # Set the user field on the instance
        setattr(form.instance, self.user_field_name, self.request.user)
        return super().form_valid(form)


class UserFilterMixin:
    """
    Mixin to automatically filter queryset by current user.

    Set user_field_name attribute (defaults to 'instructor'):
        user_field_name = 'teacher'  # Filter by teacher=request.user

    Usage:
        class MyListView(UserFilterMixin, ListView):
            user_field_name = 'instructor'  # Filters objects where instructor=request.user
    """
    user_field_name = 'instructor'  # Default field name

    def get_queryset(self):
        queryset = super().get_queryset()
        filter_kwargs = {self.user_field_name: self.request.user}
        return queryset.filter(**filter_kwargs)


class OwnershipRequiredMixin:
    """
    Mixin to ensure the current user owns the object being accessed.

    Requires:
    - ownership_check_method: Name of method on object to check ownership (default: 'is_owned_by')
    - ownership_denied_message: Message to show on permission failure
    - ownership_denied_url: URL name to redirect to on failure

    The object's ownership check method should accept request.user and return bool:
        def is_owned_by(self, user):
            return self.instructor == user

    Usage:
        class MyUpdateView(OwnershipRequiredMixin, UpdateView):
            ownership_check_method = 'is_owned_by'
            ownership_denied_message = 'You do not have permission to edit this item.'
            ownership_denied_url = 'courses:list'
    """
    ownership_check_method = 'is_owned_by'
    ownership_denied_message = 'You do not have permission to access this item.'
    ownership_denied_url = None  # Must be set by subclass

    def dispatch(self, request, *args, **kwargs):
        # Get the object
        self.object = self.get_object()

        # Check ownership
        check_method = getattr(self.object, self.ownership_check_method, None)
        if not check_method or not check_method(request.user):
            messages.error(request, self.ownership_denied_message)
            if self.ownership_denied_url:
                return redirect(self.ownership_denied_url)
            else:
                raise ValueError("ownership_denied_url must be set on OwnershipRequiredMixin")

        return super().dispatch(request, *args, **kwargs)


class AjaxResponseMixin:
    """
    Mixin to handle AJAX requests and return JSON responses.

    Provides:
    - json_success(data): Return successful JSON response
    - json_error(message, status=400): Return error JSON response
    - is_ajax(): Check if request is AJAX

    Usage:
        class MyView(AjaxResponseMixin, View):
            def post(self, request):
                if not self.is_ajax():
                    return HttpResponseBadRequest()
                # ... do work ...
                return self.json_success({'message': 'Done!'})
    """

    def is_ajax(self):
        """Check if request is AJAX"""
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def json_success(self, data=None):
        """Return successful JSON response"""
        from django.http import JsonResponse
        response_data = {'success': True}
        if data:
            response_data.update(data)
        return JsonResponse(response_data)

    def json_error(self, message, status=400):
        """Return error JSON response"""
        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'error': message
        }, status=status)


class CourseOwnershipMixin:
    """
    Verify that the current user owns the course being accessed.
    Works with views that access Course, Topic, Lesson, or Quiz objects.

    Usage:
        class MyView(CourseOwnershipMixin, UpdateView):
            model = Lesson  # or Topic, Quiz, etc.
            # Mixin automatically verifies course ownership

    Attributes:
        ownership_denied_message: Custom message for permission denial
        ownership_denied_url: URL to redirect to on permission denial
    """
    ownership_denied_message = 'Permission denied'
    ownership_denied_url = 'courses:instructor_dashboard'

    def get_course_from_object(self, obj):
        """
        Extract the Course object from various model types.
        Override this if you have custom model relationships.
        """
        from apps.courses.models import Course, Topic, Lesson, Quiz, QuizQuestion

        if isinstance(obj, Course):
            return obj
        elif isinstance(obj, Topic):
            return obj.course
        elif isinstance(obj, Lesson):
            return obj.topic.course
        elif isinstance(obj, Quiz):
            return obj.lesson.topic.course
        elif isinstance(obj, QuizQuestion):
            return obj.quiz.lesson.topic.course
        else:
            # Try generic attribute access
            if hasattr(obj, 'course'):
                return obj.course
            elif hasattr(obj, 'topic'):
                return obj.topic.course if hasattr(obj.topic, 'course') else None
            elif hasattr(obj, 'lesson'):
                return obj.lesson.topic.course if hasattr(obj.lesson, 'topic') else None

        return None

    def dispatch(self, request, *args, **kwargs):
        """Verify ownership before dispatching"""
        # Get the object (if it exists - for UpdateView, DeleteView, etc.)
        if hasattr(self, 'get_object'):
            try:
                self.object = self.get_object()
                course = self.get_course_from_object(self.object)
            except:
                # Object doesn't exist yet (CreateView) or error getting it
                course = None
        else:
            course = None

        # If we have a course, verify ownership
        if course and hasattr(course, 'is_owned_by'):
            if not course.is_owned_by(request.user):
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(request, self.ownership_denied_message)
                return redirect(self.ownership_denied_url)

        return super().dispatch(request, *args, **kwargs)


class CourseContextMixin:
    """
    Automatically adds course, topic, and lesson to the context based on the object.

    Usage:
        class LessonUpdateView(CourseContextMixin, UpdateView):
            model = Lesson
            # Context automatically includes 'course', 'topic', 'lesson'
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self, 'object') and self.object:
            from apps.courses.models import Course, Topic, Lesson, Quiz, QuizQuestion

            obj = self.object

            # Add based on object type
            if isinstance(obj, Lesson):
                context['lesson'] = obj
                context['topic'] = obj.topic
                context['course'] = obj.topic.course
            elif isinstance(obj, Topic):
                context['topic'] = obj
                context['course'] = obj.course
            elif isinstance(obj, Course):
                context['course'] = obj
            elif isinstance(obj, Quiz):
                context['quiz'] = obj
                context['lesson'] = obj.lesson
                context['topic'] = obj.lesson.topic
                context['course'] = obj.lesson.topic.course
            elif isinstance(obj, QuizQuestion):
                context['question'] = obj
                context['quiz'] = obj.quiz
                context['lesson'] = obj.quiz.lesson
                context['topic'] = obj.quiz.lesson.topic
                context['course'] = obj.quiz.lesson.topic.course

        # Also check for course/topic set in dispatch
        if hasattr(self, 'course') and 'course' not in context:
            context['course'] = self.course
        if hasattr(self, 'topic') and 'topic' not in context:
            context['topic'] = self.topic
        if hasattr(self, 'lesson') and 'lesson' not in context:
            context['lesson'] = self.lesson

        return context
