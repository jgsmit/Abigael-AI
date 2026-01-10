import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AbigaelAI.settings')

app = Celery('AbigaelAI')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Optional configuration, see the application documentation.
app.conf.update(
    result_expires=3600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
