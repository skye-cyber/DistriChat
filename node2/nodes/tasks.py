# nodes/tasks.py (Celery tasks)
from celery import shared_task
from celery.schedules import crontab
from .sync_client import NodeSyncClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_sync():
    """Automatically sync all nodes on a schedule"""
    try:
        sync_client = NodeSyncClient()

        # Perform incremental sync
        result = sync_client.sync_with_central("incremental")

        if result:
            logger.info(f"Auto-sync completed for {settings.NODE_NAME}")
        else:
            logger.warning(f"Auto-sync failed for {settings.NODE_NAME}")

    except Exception as e:
        logger.error(f"Auto-sync error for {settings.NODE_NAME}: {e}")


# Celery beat schedule
CELERY_BEAT_SCHEDULE = {
    "auto-sync-node-every-5-minutes": {
        "task": "nodes.tasks.auto_sync_node",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}
