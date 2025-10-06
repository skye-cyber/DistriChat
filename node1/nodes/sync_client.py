# nodes/sync_client.py
import requests
import json
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class NodeSyncClient:
    def __init__(self, node_id, central_server_url, api_key):
        self.node_id = node_id
        self.central_server_url = central_server_url
        self.api_key = api_key
        self.last_sync = None

    def sync_with_central(self, sync_type="incremental"):
        """Sync this node's data with central server"""
        try:
            # Prepare sync data
            sync_data = self.prepare_sync_data(sync_type)

            # Send to central server
            response = requests.post(
                f"{self.central_server_url}/nodes/sync/{self.node_id}/",
                json=sync_data,
                headers={
                    "X-Node-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                self.last_sync = timezone.now()
                logger.info(f"Sync completed: {result}")
                return result
            else:
                logger.error(f"Sync failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Sync error: {e}")
            return None

    def pull_from_central(self, since=None):
        """Pull updates from central server"""
        try:
            params = {}
            if since:
                params["since"] = since.isoformat()

            response = requests.get(
                f"{self.central_server_url}/nodes/sync/{self.node_id}/",
                params=params,
                headers={"X-Node-API-Key": self.api_key},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self.process_pulled_data(data["sync_data"])
                return data
            else:
                logger.error(f"Pull failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Pull error: {e}")
            return None

    def prepare_sync_data(self, sync_type):
        """Prepare data for syncing"""
        from chat.models import Message
        from django.utils import timezone

        if sync_type == "full":
            messages = Message.objects.all().order_by("created_at")
        else:
            # Incremental sync - only new messages since last sync
            if self.last_sync:
                messages = Message.objects.filter(created_at__gt=self.last_sync)
            else:
                messages = Message.objects.all().order_by("created_at")

        sync_data = {
            "sync_type": sync_type,
            "node_id": str(self.node_id),
            "timestamp": timezone.now().isoformat(),
            "messages": [
                {
                    "id": str(msg.id),
                    "room_id": str(msg.room.id),
                    "sender_id": str(msg.sender.id),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "updated_at": msg.updated_at.isoformat(),
                    "content_hash": self.calculate_hash(msg.content),
                }
                for msg in messages
            ],
        }

        return sync_data

    def calculate_hash(self, content):
        """Calculate content hash for deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()

    def process_pulled_data(self, sync_data):
        """Process data pulled from central server"""
        from chat.models import Message, ChatRoom
        from users.models import User

        for msg_data in sync_data.get("messages", []):
            # Check if message already exists
            if not Message.objects.filter(id=msg_data["id"]).exists():
                try:
                    # Get or create related objects
                    room = ChatRoom.objects.get(id=msg_data["room_id"])
                    sender = User.objects.get(id=msg_data["sender_id"])

                    # Create message
                    Message.objects.create(
                        id=msg_data["id"],
                        room=room,
                        sender=sender,
                        content=msg_data["content"],
                        created_at=msg_data["created_at"],
                        updated_at=msg_data["updated_at"],
                    )
                except Exception as e:
                    logger.error(f"Failed to process message {msg_data['id']}: {e}")
