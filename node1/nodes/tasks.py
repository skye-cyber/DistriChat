# nodes/tasks.py (Celery tasks)
from celery import shared_task
from celery.schedules import crontab
from .sync_client import NodeSyncClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_sync_nodes():
    """Automatically sync all nodes on a schedule"""
    from .models import Node

    nodes = Node.objects.filter(status="online")

    for node in nodes:
        try:
            sync_client = NodeSyncClient(
                node_id=node.id,
                central_server_url=settings.CENTRAL_SERVER_URL,
                api_key=node.api_key,
            )

            # Perform incremental sync
            result = sync_client.sync_with_central("incremental")

            if result:
                logger.info(f"Auto-sync completed for {node.name}")
            else:
                logger.warning(f"Auto-sync failed for {node.name}")

        except Exception as e:
            logger.error(f"Auto-sync error for {node.name}: {e}")


# Celery beat schedule
CELERY_BEAT_SCHEDULE = {
    "auto-sync-nodes-every-5-minutes": {
        "task": "nodes.tasks.auto_sync_nodes",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}
