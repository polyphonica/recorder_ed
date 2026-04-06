from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0003_remove_examregistration_fee_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='examregistration',
            name='programme_approved',
            field=models.BooleanField(default=False, help_text='Whether the student/guardian has approved the exam programme'),
        ),
        migrations.AddField(
            model_name='examregistration',
            name='programme_approved_at',
            field=models.DateTimeField(blank=True, help_text='When the student/guardian approved the programme', null=True),
        ),
        migrations.AddField(
            model_name='historicalexamregistration',
            name='programme_approved',
            field=models.BooleanField(default=False, help_text='Whether the student/guardian has approved the exam programme'),
        ),
        migrations.AddField(
            model_name='historicalexamregistration',
            name='programme_approved_at',
            field=models.DateTimeField(blank=True, help_text='When the student/guardian approved the programme', null=True),
        ),
        migrations.AlterField(
            model_name='examregistration',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('registered', 'Registered'),
                    ('submitted', 'Exam Submitted'),
                    ('results_received', 'Results Received'),
                ],
                default='draft',
                help_text='Current exam status',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='historicalexamregistration',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('registered', 'Registered'),
                    ('submitted', 'Exam Submitted'),
                    ('results_received', 'Results Received'),
                ],
                default='draft',
                help_text='Current exam status',
                max_length=20,
            ),
        ),
    ]
