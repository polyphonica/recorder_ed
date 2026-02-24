"""
State-only migration: remove PracticeEntry from private_teaching state.

No database operations — the 'private_teaching_practiceentry' table is unchanged
and is now owned by the practice app.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('private_teaching', '0034_remove_cart_update_cartitem_fk'),
        ('practice', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='PracticeEntry'),
            ],
            database_operations=[],
        ),
    ]
