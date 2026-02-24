import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recordered.settings')

app = Celery('recordered')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
