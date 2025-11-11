import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "larvixon_site.settings")

app = Celery("larvixon_site")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
