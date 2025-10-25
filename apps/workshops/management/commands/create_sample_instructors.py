from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create sample instructors and update existing users with proper names'
    
    def handle(self, *args, **options):
        # Update admin user with proper name
        try:
            admin_user = User.objects.get(username='admin')
            if not admin_user.first_name:
                admin_user.first_name = 'Admin'
                admin_user.last_name = 'User'
                admin_user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated admin user: {admin_user.first_name} {admin_user.last_name}')
                )
        except User.DoesNotExist:
            pass
            
        # Update test user with proper name
        try:
            test_user = User.objects.get(username='testuser')
            if not test_user.first_name:
                test_user.first_name = 'Test'
                test_user.last_name = 'Student'
                test_user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated test user: {test_user.first_name} {test_user.last_name}')
                )
        except User.DoesNotExist:
            pass
        
        # Create sample instructors
        instructors_data = [
            {
                'username': 'sarah_chen',
                'email': 'sarah.chen@recordered.com',
                'first_name': 'Sarah',
                'last_name': 'Chen',
                'password': 'instructor123'
            },
            {
                'username': 'mike_rodriguez',
                'email': 'mike.rodriguez@recordered.com',
                'first_name': 'Mike',
                'last_name': 'Rodriguez',
                'password': 'instructor123'
            },
            {
                'username': 'alex_kim',
                'email': 'alex.kim@recordered.com',
                'first_name': 'Alex',
                'last_name': 'Kim',
                'password': 'instructor123'
            },
            {
                'username': 'dr_patel',
                'email': 'priya.patel@recordered.com',
                'first_name': 'Dr. Priya',
                'last_name': 'Patel',
                'password': 'instructor123'
            }
        ]
        
        for instructor_data in instructors_data:
            user, created = User.objects.get_or_create(
                username=instructor_data['username'],
                defaults={
                    'email': instructor_data['email'],
                    'first_name': instructor_data['first_name'],
                    'last_name': instructor_data['last_name'],
                    'is_staff': True  # Make them staff so they can be instructors
                }
            )
            
            if created:
                user.set_password(instructor_data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created instructor: {user.first_name} {user.last_name} ({user.username})')
                )
            else:
                # Update existing user if needed
                if not user.first_name:
                    user.first_name = instructor_data['first_name']
                    user.last_name = instructor_data['last_name']
                    user.email = instructor_data['email']
                    user.is_staff = True
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated instructor: {user.first_name} {user.last_name} ({user.username})')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Instructor already exists: {user.first_name} {user.last_name} ({user.username})')
                    )
        
        self.stdout.write(
            self.style.SUCCESS('\nSample instructors created! You can now:')
        )
        self.stdout.write('1. Login to admin with existing credentials')
        self.stdout.write('2. Create workshops and assign them to instructors')
        self.stdout.write('3. Instructors will display with full names instead of usernames')
        self.stdout.write('\nInstructor login credentials:')
        for instructor_data in instructors_data:
            self.stdout.write(f'  {instructor_data["first_name"]} {instructor_data["last_name"]}: {instructor_data["username"]} / instructor123')