#!/usr/bin/env python
"""
Create sample workshop data for testing
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Add the project directory to Python path
sys.path.append('/Users/michaelpiraner/Documents/Projects/recordered')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')
django.setup()

from django.contrib.auth.models import User
from apps.workshops.models import WorkshopCategory, Workshop, WorkshopSession

def create_sample_data():
    """Create sample workshops, categories, and sessions"""
    print("Creating sample workshop data...")
    
    # Create superuser if it doesn't exist
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@recordered.com',
            password='admin123'
        )
        print(f"Created superuser: {admin_user.username}")
    else:
        admin_user = User.objects.get(username='admin')
        print(f"Using existing superuser: {admin_user.username}")
    
    # Create workshop categories
    categories_data = [
        {
            'name': 'Web Development',
            'description': 'Learn modern web development technologies and frameworks',
            'color': 'primary'
        },
        {
            'name': 'Data Science',
            'description': 'Data analysis, machine learning, and data visualization',
            'color': 'secondary'
        },
        {
            'name': 'Design',
            'description': 'UI/UX design, graphic design, and design thinking',
            'color': 'accent'
        },
        {
            'name': 'Business',
            'description': 'Entrepreneurship, marketing, and business strategy',
            'color': 'success'
        }
    ]
    
    categories = {}
    for cat_data in categories_data:
        category, created = WorkshopCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'slug': cat_data['name'].lower().replace(' ', '-'),
                'description': cat_data['description'],
                'color': cat_data['color'],
                'is_active': True
            }
        )
        categories[cat_data['name']] = category
        print(f"{'Created' if created else 'Found'} category: {category.name}")
    
    # Create workshops
    workshops_data = [
        {
            'title': 'Building Modern React Applications',
            'slug': 'modern-react-applications',
            'category': 'Web Development',
            'short_description': 'Learn to build scalable React applications with modern hooks, context, and best practices.',
            'description': '''Master React.js by building real-world applications. This comprehensive workshop covers:
            
- Modern React hooks (useState, useEffect, useContext, custom hooks)
- Component composition and reusability
- State management with Context API and Redux Toolkit
- API integration and data fetching
- Testing React components
- Performance optimization techniques
- Deployment strategies

You'll build a complete todo application with authentication, real-time updates, and responsive design.''',
            'learning_objectives': '''By the end of this workshop, you will be able to:
- Create functional React components using modern hooks
- Manage complex application state effectively
- Integrate with REST APIs and handle async operations
- Write unit tests for React components
- Optimize React app performance
- Deploy React applications to production''',
            'prerequisites': '''- Basic knowledge of HTML, CSS, and JavaScript
- Familiarity with ES6+ features (arrow functions, destructuring, modules)
- Node.js and npm installed on your computer
- A code editor (VS Code recommended)''',
            'materials_needed': '''- Computer with Node.js 16+ installed
- Code editor (VS Code with React extensions)
- Git for version control
- Web browser with React DevTools extension''',
            'difficulty_level': 'intermediate',
            'estimated_duration': 180,
            'tags': 'react, javascript, frontend, hooks, state-management',
            'is_free': False,
            'price': 99.00,
            'is_featured': True
        },
        {
            'title': 'Python Data Analysis with Pandas',
            'slug': 'python-data-analysis-pandas',
            'category': 'Data Science',
            'short_description': 'Master data manipulation and analysis using pandas, the most popular Python data library.',
            'description': '''Dive deep into data analysis with pandas. This hands-on workshop includes:
            
- Loading data from various sources (CSV, JSON, databases)
- Data cleaning and preprocessing techniques
- Exploratory data analysis (EDA)
- Data aggregation and groupby operations
- Merging and joining datasets
- Time series analysis
- Data visualization with matplotlib and seaborn
- Performance optimization for large datasets

Work with real datasets to solve practical data problems.''',
            'learning_objectives': '''You will learn to:
- Load and inspect data from multiple sources
- Clean messy data and handle missing values
- Perform complex data transformations
- Create insightful visualizations
- Analyze time series data
- Optimize pandas operations for performance''',
            'prerequisites': '''- Basic Python programming knowledge
- Understanding of variables, functions, and control structures
- Jupyter Notebook familiarity preferred''',
            'materials_needed': '''- Python 3.8+ installed
- Jupyter Notebook or JupyterLab
- pandas, matplotlib, seaborn libraries
- Sample datasets (provided)''',
            'difficulty_level': 'beginner',
            'estimated_duration': 240,
            'tags': 'python, pandas, data-analysis, visualization',
            'is_free': True,
            'price': 0.00,
            'is_featured': True
        },
        {
            'title': 'UI/UX Design Fundamentals',
            'slug': 'ui-ux-design-fundamentals',
            'category': 'Design',
            'short_description': 'Learn the principles of user-centered design and create compelling digital experiences.',
            'description': '''Master the fundamentals of UI/UX design in this comprehensive workshop:
            
- User research and persona development
- Information architecture and user flows
- Wireframing and prototyping
- Visual design principles (color, typography, layout)
- Usability testing and iteration
- Design systems and component libraries
- Mobile-first and responsive design
- Accessibility considerations

Practice with design tools like Figma and create a complete app design.''',
            'learning_objectives': '''You will be able to:
- Conduct user research and create personas
- Design intuitive user flows and wireframes
- Apply visual design principles effectively
- Create interactive prototypes
- Test designs with real users
- Build consistent design systems''',
            'prerequisites': '''- No prior design experience required
- Interest in user experience and visual design
- Willingness to think creatively''',
            'materials_needed': '''- Computer with internet access
- Figma account (free)
- Notebook for sketching
- Optional: Drawing tablet''',
            'difficulty_level': 'beginner',
            'estimated_duration': 300,
            'tags': 'design, ui, ux, figma, prototyping',
            'is_free': False,
            'price': 149.00,
            'is_featured': False
        },
        {
            'title': 'Django REST API Development',
            'slug': 'django-rest-api-development',
            'category': 'Web Development',
            'short_description': 'Build robust REST APIs with Django REST Framework and industry best practices.',
            'description': '''Create professional REST APIs using Django REST Framework:
            
- Django models and database design
- Serializers for data transformation
- ViewSets and generic views
- Authentication and permissions
- API documentation with Swagger
- Testing API endpoints
- Performance optimization
- Deployment considerations

Build a complete blog API with user authentication and CRUD operations.''',
            'learning_objectives': '''Learn to:
- Design RESTful API architectures
- Implement authentication and authorization
- Create comprehensive API documentation
- Write tests for API endpoints
- Optimize API performance
- Deploy APIs to production''',
            'prerequisites': '''- Python programming experience
- Basic Django knowledge helpful
- Understanding of HTTP methods and status codes''',
            'materials_needed': '''- Python 3.8+ installed
- Django and DRF libraries
- API testing tool (Postman recommended)
- Code editor''',
            'difficulty_level': 'intermediate',
            'estimated_duration': 270,
            'tags': 'django, rest-api, python, backend',
            'is_free': False,
            'price': 129.00,
            'is_featured': False
        },
        {
            'title': 'Startup Marketing Essentials',
            'slug': 'startup-marketing-essentials',
            'category': 'Business',
            'short_description': 'Learn cost-effective marketing strategies to grow your startup from zero to first customers.',
            'description': '''Master startup marketing with limited budget and resources:
            
- Market research and customer validation
- Building a marketing funnel
- Content marketing and SEO
- Social media marketing strategies
- Email marketing automation
- Growth hacking techniques
- Analytics and measurement
- Customer retention strategies

Create a complete marketing plan for your startup idea.''',
            'learning_objectives': '''You will learn to:
- Validate your market and find product-market fit
- Create compelling marketing messages
- Build cost-effective marketing funnels
- Leverage social media for growth
- Measure and optimize marketing performance
- Retain and grow your customer base''',
            'prerequisites': '''- Startup idea or business concept
- Basic understanding of digital marketing
- Willingness to learn and experiment''',
            'materials_needed': '''- Computer with internet access
- Google Analytics account
- Social media accounts
- Notebook for planning''',
            'difficulty_level': 'beginner',
            'estimated_duration': 210,
            'tags': 'marketing, startup, growth, social-media',
            'is_free': True,
            'price': 0.00,
            'is_featured': False
        }
    ]
    
    workshops = {}
    for workshop_data in workshops_data:
        category = categories[workshop_data['category']]
        
        workshop, created = Workshop.objects.get_or_create(
            slug=workshop_data['slug'],
            defaults={
                'title': workshop_data['title'],
                'category': category,
                'short_description': workshop_data['short_description'],
                'description': workshop_data['description'],
                'learning_objectives': workshop_data['learning_objectives'],
                'prerequisites': workshop_data['prerequisites'],
                'materials_needed': workshop_data['materials_needed'],
                'difficulty_level': workshop_data['difficulty_level'],
                'estimated_duration': workshop_data['estimated_duration'],
                'tags': workshop_data['tags'],
                'is_free': workshop_data['is_free'],
                'price': workshop_data['price'],
                'is_featured': workshop_data['is_featured'],
                'instructor': admin_user,
                'status': 'published'
            }
        )
        workshops[workshop_data['title']] = workshop
        print(f"{'Created' if created else 'Found'} workshop: {workshop.title}")
    
    # Create workshop sessions
    base_date = timezone.now() + timedelta(days=7)  # Start sessions in a week
    
    sessions_data = [
        # React workshop sessions
        {
            'workshop': 'Building Modern React Applications',
            'start_offset_days': 0,
            'start_hour': 10,
            'duration_hours': 3,
            'max_participants': 25
        },
        {
            'workshop': 'Building Modern React Applications',
            'start_offset_days': 14,
            'start_hour': 14,
            'duration_hours': 3,
            'max_participants': 25
        },
        
        # Python Data Analysis sessions
        {
            'workshop': 'Python Data Analysis with Pandas',
            'start_offset_days': 3,
            'start_hour': 9,
            'duration_hours': 4,
            'max_participants': 30
        },
        {
            'workshop': 'Python Data Analysis with Pandas',
            'start_offset_days': 10,
            'start_hour': 13,
            'duration_hours': 4,
            'max_participants': 30
        },
        
        # UI/UX Design sessions
        {
            'workshop': 'UI/UX Design Fundamentals',
            'start_offset_days': 5,
            'start_hour': 10,
            'duration_hours': 5,
            'max_participants': 20
        },
        
        # Django API sessions
        {
            'workshop': 'Django REST API Development',
            'start_offset_days': 12,
            'start_hour': 11,
            'duration_hours': 4.5,
            'max_participants': 20
        },
        
        # Marketing sessions
        {
            'workshop': 'Startup Marketing Essentials',
            'start_offset_days': 2,
            'start_hour': 15,
            'duration_hours': 3.5,
            'max_participants': 50
        },
        {
            'workshop': 'Startup Marketing Essentials',
            'start_offset_days': 16,
            'start_hour': 10,
            'duration_hours': 3.5,
            'max_participants': 50
        }
    ]
    
    for session_data in sessions_data:
        workshop = workshops[session_data['workshop']]
        start_datetime = base_date + timedelta(
            days=session_data['start_offset_days'],
            hours=session_data['start_hour']
        )
        end_datetime = start_datetime + timedelta(hours=session_data['duration_hours'])
        
        session, created = WorkshopSession.objects.get_or_create(
            workshop=workshop,
            start_datetime=start_datetime,
            defaults={
                'end_datetime': end_datetime,
                'timezone_name': 'US/Pacific',
                'max_participants': session_data['max_participants'],
                'waitlist_enabled': True,
                'meeting_url': f'https://zoom.us/j/{workshop.id}123456789',
                'meeting_id': f'{workshop.id}123456789',
                'meeting_password': 'workshop123',
                'is_active': True
            }
        )
        print(f"{'Created' if created else 'Found'} session: {session.workshop.title} on {session.start_datetime.strftime('%Y-%m-%d %H:%M')}")
    
    print("\nSample data creation completed!")
    print(f"Created {WorkshopCategory.objects.count()} categories")
    print(f"Created {Workshop.objects.count()} workshops")
    print(f"Created {WorkshopSession.objects.count()} sessions")
    print("\nAdmin credentials:")
    print("Username: admin")
    print("Password: admin123")
    print("\nYou can access the admin at: http://127.0.0.1:8002/admin/")

if __name__ == '__main__':
    create_sample_data()