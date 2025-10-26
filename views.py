from django.shortcuts import render
from django.views.generic import TemplateView

class DomainSelectorView(TemplateView):
    """Landing page where users select their domain (Workshops, Private Teaching, Courses)"""
    template_name = 'domain_selector.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Domain information for the selector
        context['domains'] = [
            {
                'name': 'Workshops',
                'url': 'workshops:list',
                'description': 'Group music workshops and masterclasses',
                'icon': '🎼',
                'color': 'bg-blue-500',
                'features': ['Group Learning', 'Expert Instructors', 'Various Instruments', 'All Skill Levels']
            },
            {
                'name': 'Private Lessons',
                'url': 'private_teaching:home', 
                'description': 'One-on-one personalized music lessons',
                'icon': '🎵',
                'color': 'bg-green-500',
                'features': ['Personal Attention', 'Flexible Scheduling', 'Customized Learning', 'Individual Progress']
            },
            {
                'name': 'Courses',
                'url': 'courses:list',
                'description': 'Structured music education programs',
                'icon': '🎓',
                'color': 'bg-purple-500',
                'features': ['Comprehensive Curriculum', 'Progressive Learning', 'Certification', 'Self-Paced'],
                'coming_soon': False
            }
        ]
        
        return context