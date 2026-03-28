"""
Drop the orphaned courses_quiz* tables left behind by 0023_remove_quiz_models.
Data was migrated to the quizzes app in quizzes/0002_migrate_course_quiz_data.
These tables have no corresponding Django models and their FK to courses_lesson
was blocking lesson deletions.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0024_historicalcourseenrollment'),
        ('quizzes', '0002_migrate_course_quiz_data'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS courses_quizattempt CASCADE;
                DROP TABLE IF EXISTS courses_quizanswer CASCADE;
                DROP TABLE IF EXISTS courses_quizquestion CASCADE;
                DROP TABLE IF EXISTS courses_quiz CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
