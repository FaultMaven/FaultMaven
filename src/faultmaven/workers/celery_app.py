"""
Celery application configuration.

Configures Celery with Redis as broker and backend,
using settings from the unified config system.
"""

from celery import Celery

from faultmaven.config import get_settings
from faultmaven.logging_config import configure_logging

# Configure logging for worker process
configure_logging()

# Get settings
settings = get_settings()

# Build Redis URL for Celery
redis_url = settings.redis.connection_url

# Create Celery app
celery_app = Celery(
    "faultmaven",
    broker=redis_url,
    backend=redis_url,
    include=[
        "faultmaven.workers.tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    result_expires=86400,  # 24 hours

    # Task limits
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory leak protection)

    # Retry settings
    task_acks_late=True,  # Only ack after task completes
    task_reject_on_worker_lost=True,  # Requeue if worker dies

    # Result backend
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0,
        }
    },

    # Task routes (optional - for future queue separation)
    task_routes={
        "faultmaven.workers.tasks.process_document_task": {"queue": "documents"},
        "faultmaven.workers.tasks.generate_report_task": {"queue": "reports"},
    },

    # Default queue
    task_default_queue="default",
)


# Optional: Configure beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Example: Clean up expired sessions every hour
    # "cleanup-expired-sessions": {
    #     "task": "faultmaven.workers.tasks.cleanup_sessions_task",
    #     "schedule": 3600.0,  # Every hour
    # },
}
