from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.contrib import messages
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
