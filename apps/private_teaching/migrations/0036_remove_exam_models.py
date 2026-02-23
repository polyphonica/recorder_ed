"""
State-only migration: remove ExamBoard, ExamRegistration, ExamPiece from
private_teaching state.

No database operations — the tables are unchanged and are now owned by the exams app.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0001_initial'),
        ('lessons', '0015_update_exam_registration_fk'),
        ('private_teaching', '0035_remove_practiceentry'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='ExamBoard'),
                migrations.DeleteModel(name='ExamRegistration'),
                migrations.DeleteModel(name='ExamPiece'),
            ],
            database_operations=[],
        ),
    ]
