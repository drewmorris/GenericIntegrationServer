from __future__ import annotations

import os
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
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