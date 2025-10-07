from django.dispatch import receiver
from django.db.models.signals import post_save
from nodes.models import Node
import requests
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Node)
def create_node(sender, instance, **kwargs):
    """Automatically save update node metadata when node is created"""
    data = instance.to_dict()
    api_url = f"{data["url"]}/nodes/meta/set/"
    return meta_update_handler(api_url, data)


@receiver(post_save, sender=Node)
def save_node(sender, instance, **kwargs):
    """Automatically save update node metadata when node is updated"""
    data = instance.to_dict()
    api_url = f"{data["url"]}/nodes/meta/set/"
    return meta_update_handler(api_url, data)


def meta_update_handler(api_url, data):
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
        logger.info(f"Meta update completed: {result}")
        return result
    else:
        logger.error(f"Meta update failed: {response.text}")
        return None
