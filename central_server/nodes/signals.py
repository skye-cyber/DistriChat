from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import transaction
from nodes.models import Node
import requests
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Node)
def sync_node_metadata(sender, instance, created, **kwargs):
    """Sync node metadata with the central server after creation or update."""
    # Avoid recursive triggers or invalid URLs
    if not instance.url:
        logger.warning("Skipping metadata sync: Node URL missing.")
        return

    data = instance.to_dict()
    api_url = f"{instance.url.rstrip('/')}/nodes/meta/set/"

    # Defer API call until after transaction is fully committed
    transaction.on_commit(lambda: _meta_update_handler(api_url, data, created))


def _meta_update_handler(api_url, data, created=False):
    """Send metadata to remote node after save."""
    try:
        response = requests.post(
            api_url,
            json=data,
            headers={
                "X-ORIGIN": "CENTRAL_SERVER",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"Meta {'creation' if created else 'update'} successful: {result}"
            )
            return result
        else:
            logger.error(
                f"Meta {'creation' if created else 'update'} failed "
                f"({response.status_code}): {response.text}"
            )
            return None

    except requests.RequestException as e:
        logger.error(f"Request error syncing metadata: {e}")
        return None
