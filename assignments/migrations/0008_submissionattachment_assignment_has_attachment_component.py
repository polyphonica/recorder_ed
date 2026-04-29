from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import assignments.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0007_assignment_reference_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='has_attachment_component',
            field=models.BooleanField(default=False, help_text='Student will need to scan/photograph handwritten work and upload it'),
        ),
        migrations.CreateModel(
            name='SubmissionAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to=assignments.models._submission_attachment_path)),
                ('label', models.CharField(blank=True, max_length=200)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='assignments.assignmentsubmission')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submission_attachments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['uploaded_at'],
            },
        ),
    ]
