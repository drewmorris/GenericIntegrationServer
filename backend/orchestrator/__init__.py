from __future__ import annotations

import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or BROKER_URL

# TODO(MVP): Switch broker/result back to Redis or RabbitMQ for production deployments
celery_app = Celery("integration_server", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.task_default_queue = "default"

# beat schedule: every minute run scan_due_profiles
celery_app.conf.beat_schedule = {
    "scan-due-profiles": {
        "task": "orchestrator.scan_due_profiles",
        "schedule": 60.0,
    }
}

# autodiscover tasks in this package
celery_app.autodiscover_tasks([__name__]) 