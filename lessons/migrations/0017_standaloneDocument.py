from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('lessons', '0016_historicallesson'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StandaloneDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.CharField(blank=True, help_text="Optional note, e.g. 'Treble clef — 8 staves per page'", max_length=500)),
                ('document', models.FileField(upload_to='standalone_documents/')),
                ('share_with_all_students', models.BooleanField(default=True, help_text='Make available to all current students')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='standalone_documents', to=settings.AUTH_USER_MODEL)),
                ('shared_with_students', models.ManyToManyField(blank=True, help_text='Specific students to share with (only used when not sharing with all)', related_name='shared_standalone_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
