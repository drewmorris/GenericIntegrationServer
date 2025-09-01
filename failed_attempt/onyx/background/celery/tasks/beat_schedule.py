# Simplified beat schedule for integration server
from datetime import timedelta
from typing import Any

from onyx.configs.constants import OnyxCeleryTask, OnyxCeleryQueues, OnyxCeleryPriority

# Integration server beat schedule - much simpler than search/indexing system
BEAT_EXPIRES_DEFAULT = 15 * 60  # 15 minutes

# Simple beat tasks for integration server
beat_task_templates: list[dict] = [
    {
        "name": "monitor-connectors",
        "task": OnyxCeleryTask.SYSTEM_MONITORING.value,
        "schedule": timedelta(minutes=5),
        "options": {
            "expires": BEAT_EXPIRES_DEFAULT,
            "priority": OnyxCeleryPriority.MEDIUM.value,
            "queue": "monitoring",
        },
    },
    {
        "name": "cleanup-old-connector-tasks", 
        "task": OnyxCeleryTask.CONNECTOR_DELETE.value,
        "schedule": timedelta(hours=1),
        "options": {
            "expires": BEAT_EXPIRES_DEFAULT,
            "priority": OnyxCeleryPriority.LOW.value,
            "queue": "connector_deletion",
        },
    },
    {
        "name": "heartbeat",
        "task": "integration_server_heartbeat",
        "schedule": timedelta(minutes=1),
        "options": {
            "expires": 120,  # 2 minutes
            "priority": OnyxCeleryPriority.HIGH.value,
            "queue": "monitoring",
        },
    },
]

# Integration server doesn't need complex cloud-specific scheduling
cloud_beat_task_templates: list[dict] = []

def get_all_beat_task_configs() -> list[dict[str, Any]]:
    """Get all beat task configurations for integration server"""
    return beat_task_templates.copy()

def get_cloud_beat_task_configs() -> list[dict[str, Any]]:  
    """Integration server doesn't use cloud-specific tasks"""
    return []
