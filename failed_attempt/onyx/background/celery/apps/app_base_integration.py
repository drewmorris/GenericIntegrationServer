# Simplified Celery app setup for integration server
import logging
import os
from typing import Any, Dict

from celery import Celery
from celery.signals import (
    after_setup_logger,
    after_setup_task_logger, 
    worker_ready,
    worker_shutdown,
)

from onyx.utils.logger import setup_logger, PlainFormatter
from onyx.redis.redis_pool import get_redis_client
from onyx.configs.app_configs import (
    REDIS_DB_NUMBER_CELERY,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DB
)

logger = setup_logger()


class IntegrationServerCelery(Celery):
    """Simplified Celery app for integration server operations"""
    
    def __init__(self, app_name: str = "integration_server"):
        super().__init__(app_name)
        self.logger = setup_logger(f"celery.{app_name}")
        self.setup_integration_server_config()
        self.setup_logging()
        
    def setup_integration_server_config(self) -> None:
        """Configure Celery for integration server"""
        redis_url = f"redis://localhost:6379/{REDIS_DB_NUMBER_CELERY or 0}"
        
        self.conf.update({
            # Redis broker and result backend
            'broker_url': redis_url,
            'result_backend': redis_url,
            
            # Task serialization
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            'timezone': 'UTC',
            'enable_utc': True,
            
            # Task execution
            'task_acks_late': True,
            'worker_prefetch_multiplier': 1,
            'task_reject_on_worker_lost': True,
            
            # Result settings  
            'result_expires': 3600,
            
            # Worker settings
            'worker_max_tasks_per_child': 1000,
            'worker_disable_rate_limits': False,
            
            # Task routing
            'task_default_queue': 'integration_server',
            'task_default_exchange': 'integration_server',
            'task_default_routing_key': 'integration_server.default',
            
            # Task routes for integration server operations
            'task_routes': {
                'connector_operations.*': {'queue': 'connectors'},
                'monitoring.*': {'queue': 'monitoring'},
                'periodic.*': {'queue': 'periodic'},
            },
            
            # Monitoring
            'worker_send_task_events': True,
            'task_send_sent_event': True,
        })
        
        self.logger.info("Integration server Celery configuration complete")
        
    def setup_logging(self) -> None:
        """Setup logging for integration server"""
        # Simple logging setup without the complex search system requirements
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        
        @after_setup_logger.connect
        def setup_celery_logging(sender=None, logger=None, loglevel=None, logfile=None, format=None, colorize=None, **cwds):
            if logger:
                logger.setLevel(getattr(logging, log_level))
                
        @after_setup_task_logger.connect  
        def setup_task_logging(sender=None, logger=None, loglevel=None, logfile=None, format=None, colorize=None, **cwds):
            if logger:
                logger.setLevel(getattr(logging, log_level))


def create_celery_app(app_name: str = "integration_server") -> IntegrationServerCelery:
    """Create Celery app for integration server"""
    logger.info(f"Creating integration server Celery app: {app_name}")
    
    celery_app = IntegrationServerCelery(app_name)
    
    # Setup worker lifecycle
    @worker_ready.connect
    def worker_ready_handler(sender, **kwargs):
        logger.info(f"Integration server worker ready: {sender}")
        
    @worker_shutdown.connect  
    def worker_shutdown_handler(sender, **kwargs):
        logger.info(f"Integration server worker shutdown: {sender}")
        
    return celery_app


# Create the default integration server Celery app
celery_app = create_celery_app()


# Task logger for integration server tasks
def get_task_logger_integration_server(name: str) -> logging.Logger:
    """Get task logger for integration server"""
    return setup_logger(f"task.{name}")
