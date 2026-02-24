"""
State-only migration: update Lesson.exam_registration FK from
private_teaching.ExamRegistration to exams.ExamRegistration.

No database operations — the FK column is unchanged.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0001_initial'),
        ('lessons', '0014_alter_lessonassignment_unique_together_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='lesson',
                    name='exam_registration',
                    field=models.ForeignKey(
                        blank=True,
                        help_text='Link to exam if this lesson is for exam preparation',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='preparation_lessons',
                        to='exams.examregistration',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
