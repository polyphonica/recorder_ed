from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('aural_training', '0003_auraltestset_auraltest'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GlossaryTerm',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('term', models.CharField(max_length=100)),
                ('definition', models.TextField()),
                ('grade', models.PositiveSmallIntegerField(
                    blank=True,
                    choices=[(1, 'Grade 1'), (2, 'Grade 2'), (3, 'Grade 3'), (4, 'Grade 4'),
                             (5, 'Grade 5'), (6, 'Grade 6'), (7, 'Grade 7'), (8, 'Grade 8')],
                    help_text='Leave blank if not grade-specific.',
                    null=True,
                )),
                ('is_shared', models.BooleanField(
                    default=False,
                    help_text='If true, all students on the platform can see this term.',
                )),
                ('order', models.PositiveIntegerField(default=0, help_text='Lower numbers appear first within a grade.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='glossary_terms',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Glossary Term',
                'verbose_name_plural': 'Glossary Terms',
                'ordering': ['grade', 'order', 'term'],
            },
        ),
    ]
