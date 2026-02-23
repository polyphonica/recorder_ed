"""
State-only: remove Quiz, QuizQuestion, QuizAnswer, QuizAttempt from courses app.
The underlying DB tables (courses_quiz, etc.) become orphaned and can be
dropped in a future cleanup migration once the data is confirmed migrated.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0022_course_courses_cou_instruc_f1fbcf_idx'),
        ('quizzes', '0002_migrate_course_quiz_data'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='QuizAttempt'),
                migrations.DeleteModel(name='QuizAnswer'),
                migrations.DeleteModel(name='QuizQuestion'),
                migrations.DeleteModel(name='Quiz'),
            ],
            database_operations=[],
        ),
    ]
