"""
Data migration: transfer all PrivateLessonAssignment records to LessonAssignment,
and re-point Conversation.lesson_assignment accordingly.
"""
from django.db import migrations


def migrate_forward(apps, schema_editor):
    PLA = apps.get_model('private_teaching', 'PrivateLessonAssignment')
    LA = apps.get_model('lessons', 'LessonAssignment')
    Conversation = apps.get_model('messaging', 'Conversation')

    for pla in PLA.objects.select_related(
        'lesson', 'assignment', 'student', 'teacher', 'child_profile'
    ):
        if pla.lesson_id:
            # Lesson-linked: find or use existing LA for this lesson+assignment pair
            la, _ = LA.objects.get_or_create(
                lesson=pla.lesson,
                assignment=pla.assignment,
                defaults={'due_date': pla.due_date}
            )
        else:
            # Standalone: create LA with explicit student/teacher/child_profile
            la = LA.objects.create(
                lesson=None,
                assignment=pla.assignment,
                student=pla.student,
                teacher=pla.teacher,
                child_profile=pla.child_profile,
                due_date=pla.due_date,
            )
        # Re-point any conversations linked to this PLA → new/existing LA
        Conversation.objects.filter(
            private_lesson_assignment=pla
        ).update(lesson_assignment=la)


class Migration(migrations.Migration):
    dependencies = [
        ('private_teaching', '0031_lessoncancellationrequest_initiated_by'),
        ('lessons', '0014_alter_lessonassignment_unique_together_and_more'),
        ('messaging', '0005_conversation_lesson_assignment_and_more'),
    ]
    operations = [
        migrations.RunPython(migrate_forward, migrations.RunPython.noop)
    ]
