from django.db import migrations


class Migration(migrations.Migration):
    """
    Rename privatelessonquiz_id → quiz_id in the M2M through table.

    When the model was PrivateLessonQuiz, Django generated the FK column as
    privatelessonquiz_id.  After renaming the model to Quiz, Django expects
    quiz_id.  The table name is unchanged (db_table keeps it consistent).
    """

    dependencies = [
        ('quizzes', '0002_migrate_course_quiz_data'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE private_teaching_privatelessonquiz_tags "
                "RENAME COLUMN privatelessonquiz_id TO quiz_id"
            ),
            reverse_sql=(
                "ALTER TABLE private_teaching_privatelessonquiz_tags "
                "RENAME COLUMN quiz_id TO privatelessonquiz_id"
            ),
        ),
    ]
