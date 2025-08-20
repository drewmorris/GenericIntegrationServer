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

# Configure for test environments - run tasks synchronously
import sys
is_testing = (
    os.getenv("TESTING") == "1" or 
    "pytest" in sys.modules or 
    "pytest" in os.getenv("_", "") or
    any("pytest" in arg for arg in sys.argv)
)

if is_testing:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    print("🔧 Celery configured for testing - tasks will run synchronously")

# beat schedule: enhanced scheduling for CC-Pairs
celery_app.conf.beat_schedule = {
    "scan-due-profiles": {
        "task": "orchestrator.scan_due_profiles",
        "schedule": 60.0,
    },
    "scan-due-cc-pairs": {
        "task": "orchestrator.scan_due_cc_pairs",
        "schedule": 30.0,  # Check every 30 seconds for more responsive scheduling
    },
    "cleanup-stale-attempts": {
        "task": "orchestrator.cleanup_stale_attempts",
        "schedule": 300.0,  # Every 5 minutes
    },
    "prune-cc-pairs": {
        "task": "orchestrator.prune_cc_pairs",
        "schedule": 3600.0,  # Every hour
    }
}

# autodiscover tasks in this package
celery_app.autodiscover_tasks([__name__])

# Import schedulers to register tasks
from . import scheduler  # noqa: F401
from . import cc_pair_scheduler  # noqa: F401
from . import cc_pair_tasks  # noqa: F401 