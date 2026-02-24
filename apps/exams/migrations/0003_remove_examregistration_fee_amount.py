from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0002_historicalexamregistration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='examregistration',
            name='fee_amount',
        ),
        migrations.RemoveField(
            model_name='historicalexamregistration',
            name='fee_amount',
        ),
    ]
