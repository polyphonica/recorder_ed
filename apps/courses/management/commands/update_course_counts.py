"""
Management command to update denormalized count fields on all courses.
Run this after adding lessons to ensure the course card displays are accurate.
"""
from django.core.management.base import BaseCommand
from apps.courses.models import Course


class Command(BaseCommand):
    help = 'Update denormalized count fields (total_topics, total_lessons, total_enrollments) for all courses'

    def handle(self, *args, **options):
        courses = Course.objects.all()
        total = courses.count()

        self.stdout.write(f'Updating counts for {total} courses...')

        updated = 0
        for course in courses:
            old_lessons = course.total_lessons
            old_topics = course.total_topics

            course.update_counts()

            if course.total_lessons != old_lessons or course.total_topics != old_topics:
                self.stdout.write(
                    f'  {course.title}: '
                    f'topics {old_topics}→{course.total_topics}, '
                    f'lessons {old_lessons}→{course.total_lessons}'
                )
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated} courses with changed counts'
            )
        )
