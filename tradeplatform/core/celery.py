import os

from celery import Celery
from celery.schedules import crontab

app = Celery("trader", include=["apps.trades.tasks", "apps.registration.tasks"])
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "make_trades": {"task": "apps.trades.tasks.start_trade", "schedule": crontab()}
}
