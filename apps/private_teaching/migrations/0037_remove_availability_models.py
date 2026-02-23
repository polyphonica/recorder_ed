"""
State-only migration: remove TeacherAvailability, AvailabilityException,
TeacherAvailabilitySettings from private_teaching state.

No database operations — the tables are unchanged and are now owned by the scheduling app.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0001_initial'),
        ('private_teaching', '0036_remove_exam_models'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='TeacherAvailability'),
                migrations.DeleteModel(name='AvailabilityException'),
                migrations.DeleteModel(name='TeacherAvailabilitySettings'),
            ],
            database_operations=[],
        ),
    ]
