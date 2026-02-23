"""
State-only: remove private lesson quiz models from private_teaching app.
DB tables remain (owned by apps.quizzes).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('private_teaching', '0037_remove_availability_models'),
        ('quizzes', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='PrivateLessonQuizAttempt'),
                migrations.DeleteModel(name='PrivateLessonQuizAssignment'),
                migrations.DeleteModel(name='PrivateLessonQuizAnswer'),
                migrations.DeleteModel(name='PrivateLessonQuizQuestion'),
                migrations.DeleteModel(name='PrivateLessonQuiz'),
            ],
            database_operations=[],
        ),
    ]
