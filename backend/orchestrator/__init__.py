from __future__ import annotations

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("integration_server", broker=REDIS_URL, backend=REDIS_URL)
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