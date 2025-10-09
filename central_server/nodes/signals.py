from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from django.db import transaction
from nodes.models import Node, NodeRegistration
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

    data = instance.to_dict
    api_url = f"{instance.url.rstrip('/')}/nodes/api/meta/set/"

    # Defer API call until after transaction is fully committed
    transaction.on_commit(lambda: _meta_update_handler(api_url, data, created, False))


@receiver(pre_delete, sender=Node)
def sync_peer_delete(sender, instance, **kwargs):
    """Sync node metadata with the central server after creation or update."""
    # Avoid recursive triggers or invalid URLs
    if not instance.url:
        logger.warning("Skipping metadata sync: Node URL missing.")
        return

    # Reset approval
    reg = NodeRegistration.objects.filter(
        node_name=instance.name, node_url=instance.url
    )

    data = {
        "api_key": instance.api_key,
        "id": str(instance.id),
    }
    api_url = f"{instance.url.rstrip('/')}/nodes/api/peer/delete/"

    def reset_reg():
        if reg.exists():
            req_rec = reg.first()
            req_rec.status = "pending"
            req_rec.approved_at = None
            req_rec.approved_by = None
            req_rec.save()

    # Reset Approval on delete commit
    transaction.on_commit(lambda: reset_reg())

    # Defer API call until after transaction is fully committed
    transaction.on_commit(lambda: _meta_update_handler(api_url, data, False, True))


def _meta_update_handler(api_url, data, created=False, deleted=False):
    """Send metadata to remote node after save."""
    try:
        response = (
            requests.delete(
                api_url,
                json=data,
                headers={
                    "X-ORIGIN": "CENTRAL_SERVER",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if deleted
            else requests.post(
                api_url,
                json=data,
                headers={
                    "X-ORIGIN": "CENTRAL_SERVER",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"{'Meta+PeerNode' if not deleted else "PeerNode"} {'creation' if created else 'deleted' if deleted else 'update'} successful: {result}"
            )
            return result
        else:
            logger.error(
                f"{'Meta+PeerNode' if not deleted else "PeerNode"} {'creation' if created else 'deleted' if deleted else 'update'} failed "
                f"({response.status_code}): {api_url}- {response.text[:30]}"
            )
            return None

    except requests.RequestException as e:
        logger.error(
            f"Request error syncing {'Metadata+PeerNode' if not deleted else "PeerNode"}: {e}"
        )
        return None
