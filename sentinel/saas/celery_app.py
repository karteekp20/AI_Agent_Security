"""
Celery Application Configuration
Background task processing for report generation
"""

from celery import Celery
from .config import config

# Create Celery instance
celery_app = Celery(
    "sentinel",
    broker=config.celery.broker_url,
    backend=config.celery.result_backend,
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["sentinel.saas.tasks"])
