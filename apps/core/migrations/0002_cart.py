"""
State-only migration: register Cart in the core app.

The underlying table is 'private_teaching_cart' (unchanged).
No database operations are performed.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_update_site_domain'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Cart',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('session_key', models.CharField(blank=True, help_text='Session key for anonymous users', max_length=40, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('user', models.OneToOneField(
                            help_text='User who owns this cart',
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='lesson_cart',
                            to=settings.AUTH_USER_MODEL,
                        )),
                    ],
                    options={
                        'verbose_name': 'Shopping Cart',
                        'verbose_name_plural': 'Shopping Carts',
                        'ordering': ['-updated_at'],
                        'db_table': 'private_teaching_cart',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
