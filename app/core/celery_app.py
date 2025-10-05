from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "laundry_notifications",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.notification_tasks",
        "app.tasks.order_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.order_tasks.*": {"queue": "orders"},
    },

    # Task execution settings
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Result backend settings
    result_expires=3600,  # 1 hour

    # Beat schedule for periodic tasks
    beat_schedule={
        "retry-failed-notifications": {
            "task": "app.tasks.notification_tasks.retry_failed_notifications",
            "schedule": 300.0,  # Every 5 minutes
        },
        "send-scheduled-notifications": {
            "task": "app.tasks.notification_tasks.send_scheduled_notifications",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-old-notifications": {
            "task": "app.tasks.notification_tasks.cleanup_old_notifications",
            "schedule": 86400.0,  # Daily
        },
    },
)

# Configure logging
celery_app.conf.worker_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
)
celery_app.conf.worker_task_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
)

if __name__ == "__main__":
    celery_app.start()
