import threading
import logging
import requests
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from users.models import UserProfile
from django.db import transaction
from nodes.models import Node

logger = logging.getLogger(__name__)

# Thread-local storage for tracking sync origins
_sync_origin_local = threading.local()


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create user profile when a new user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=get_user_model())
def save_user_profile(sender, instance, **kwargs):
    """Automatically save user profile when user is saved"""
    if hasattr(instance, "profile"):
        instance.profile.save()


class CentralSyncSignalHandler:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.is_central_server = getattr(settings, "IS_CENTRAL_SERVER", True)
            self._initialized = True

    def set_sync_origin(self, node_id):
        """Set the originating node for the current sync operation"""
        _sync_origin_local.node_id = node_id

    def get_sync_origin(self):
        """Get the originating node for the current sync operation"""
        return getattr(_sync_origin_local, "node_id", None)

    def clear_sync_origin(self):
        """Clear the sync origin after operation"""
        if hasattr(_sync_origin_local, "node_id"):
            delattr(_sync_origin_local, "node_id")

    def should_sync_to_node(self, target_node_id, originating_node_id):
        """Check if we should sync to a specific node (avoid loops)"""
        return target_node_id != originating_node_id

    def get_active_nodes(self, exclude_node_id=None):
        """Get all active nodes excluding the specified one"""
        try:
            nodes = Node.objects.filter(status="online")
            if exclude_node_id:
                nodes = nodes.exclude(id=exclude_node_id)
            return nodes
        except Exception as e:
            logger.error(f"Error fetching active nodes: {e}")
            return []

    def send_sync_to_nodes(self, model_name, instance, action, originating_node_id):
        """Send sync updates to all other nodes except the originating one"""
        if not self.is_central_server:
            return

        # Use thread pool for async execution
        thread = threading.Thread(
            target=self._send_sync_to_nodes_async,
            args=(model_name, instance, action, originating_node_id),
            daemon=True,
        )
        thread.start()

    def _send_sync_to_nodes_async(
        self, model_name, instance, action, originating_node_id
    ):
        """Async implementation of node sync"""
        try:
            active_nodes = self.get_active_nodes(exclude_node_id=originating_node_id)

            if not active_nodes:
                logger.debug("No active nodes to sync with")
                return

            sync_data = {
                "model": model_name,
                "action": action,
                "data": self.serialize_instance(instance),
                "timestamp": timezone.now().isoformat(),
                # Track where it came from
                "origin_node_id": str(originating_node_id),
                "central_sync": True,  # Mark as coming from central
            }

            successful_syncs = 0
            total_nodes = len(active_nodes)

            for node in active_nodes:
                if not self.should_sync_to_node(node.id, originating_node_id):
                    continue

                try:
                    response = requests.post(
                        # Node's sync endpoint
                        f"{node.url}/api/sync/receive/",
                        json=sync_data,
                        headers={
                            "X-Central-API-Key": getattr(
                                settings, "CENTRAL_API_KEY", ""
                            ),
                            "Content-Type": "application/json",
                        },
                        timeout=5,  # Shorter timeout for nodes
                    )

                    if response.status_code == 200:
                        successful_syncs += 1
                        logger.debug(f"Sync successful to node {node.name}")
                    else:
                        logger.warning(
                            f"Sync failed to node {node.name}: {response.status_code}"
                        )

                except requests.exceptions.Timeout:
                    logger.warning(f"Sync timeout to node {node.name}")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Connection error to node {node.name}")
                except Exception as e:
                    logger.error(f"Sync error to node {node.name}: {e}")

            logger.info(f"Sync completed: {successful_syncs}/{total_nodes} nodes")

        except Exception as e:
            logger.error(f"Error in node sync process: {e}")

    def serialize_instance(self, instance):
        """Serialize model instance for sync (same as node version)"""
        if hasattr(instance, "to_sync_dict"):
            return instance.to_sync_dict()

        data = {"id": str(instance.id)}
        model_class = type(instance)

        field_mappings = {
            "Message": self._serialize_message,
            "ChatRoom": self._serialize_chatroom,
            "RoomMembership": self._serialize_room_membership,
            "MessageReadStatus": self._serialize_message_read_status,
            "UserSession": self._serialize_user_session,
            "CustomUser": self._serialize_custom_user,
        }

        serializer = field_mappings.get(model_class.__name__)
        if serializer:
            data.update(serializer(instance))

        return data

    def _serialize_message(self, instance):
        return {
            "id": str(instance.id),
            "room_id": str(instance.room_id),
            "sender_id": str(instance.sender_id),
            "content": instance.content,
            "message_type": instance.message_type,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
            "is_edited": instance.is_edited,
            "is_deleted": instance.is_deleted,
        }

    def _serialize_chatroom(self, instance):
        return {
            "id": str(instance.id),
            "name": instance.name,
            "description": instance.description or "",
            "room_type": instance.room_type,
            "created_by_id": str(instance.created_by_id),
            "is_active": instance.is_active,
            "max_members": instance.max_members,
            "created_at": instance.created_at.isoformat(),
        }

    def _serialize_room_membership(self, instance):
        return {
            "id": str(instance.id),
            "room_id": str(instance.room_id),
            "user_id": str(instance.user_id),
            "role": instance.role,
            "joined_at": instance.joined_at.isoformat(),
        }

    def _serialize_message_read_status(self, instance):
        return {
            "message_id": str(instance.message_id),
            "user_id": str(instance.user_id),
            "read_at": instance.read_at.isoformat(),
        }

    def _serialize_user_session(self, instance):
        return {
            "user_id": str(instance.user.id),
            "session_key": instance.session_key,
            "ip_address": instance.ip_address or "",
            "user_agent": instance.user_agent or "",
            "last_activity": instance.last_activity.isoformat(),
        }

    def _serialize_custom_user(self, instance):
        return {
            "user_id": str(instance.id),
            "username": instance.username,
            "email": instance.email,
            "is_online": instance.is_online,
            "last_seen": instance.last_seen.isoformat() if instance.last_seen else None,
            "avatar": str(instance.avatar) if instance.avatar else None,
            "bio": instance.bio or "",
            "notification_enabled": instance.notification_enabled,
            "sound_enabled": instance.sound_enabled,
        }


# Global central signal handler instance
_central_sync_handler = None


def get_central_sync_handler():
    global _central_sync_handler
    if _central_sync_handler is None:
        _central_sync_handler = CentralSyncSignalHandler()
    return _central_sync_handler


def safe_central_sync(instance, model_name, action, originating_node_id):
    """
    Safe wrapper for central sync that prevents loops
    """
    try:
        handler = get_central_sync_handler()
        if handler.is_central_server and originating_node_id:
            handler.send_sync_to_nodes(
                model_name, instance, action, originating_node_id
            )
    except Exception as e:
        logger.error(f"Central sync error for {model_name} {action}: {e}")


# Central server signal receivers
@receiver(post_save, sender="chat.Message")
def central_message_saved(sender, instance, created, **kwargs):
    """Central: Sync message to other nodes"""
    # Check if this save came from a sync operation
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        # This save came from a node sync, so propagate to other nodes
        safe_central_sync(
            instance, "message", "create" if created else "update", sync_origin
        )


@receiver(post_save, sender="chat.ChatRoom")
def central_chatroom_saved(sender, instance, created, **kwargs):
    """Central: Sync chatroom to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(
            instance, "chatroom", "create" if created else "update", sync_origin
        )


@receiver(post_save, sender="chat.RoomMembership")
def central_room_membership_saved(sender, instance, created, **kwargs):
    """Central: Sync membership to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(
            instance, "roommembership", "create" if created else "update", sync_origin
        )


@receiver(post_save, sender="users.CustomUser")
def central_user_saved(sender, instance, created, **kwargs):
    """Central: Sync user to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(
            instance, "user", "create" if created else "update", sync_origin
        )


@receiver(post_save, sender="chat.MessageReadStatus")
def central_message_status_saved(sender, instance, created, **kwargs):
    """Central: Sync read status to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(
            instance,
            "messagereadstatus",
            "create" if created else "update",
            sync_origin,
        )


# Delete handlers
@receiver(post_delete, sender="chat.Message")
def central_message_deleted(sender, instance, **kwargs):
    """Central: Sync message deletion to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(instance, "message", "delete", sync_origin)


@receiver(post_delete, sender="chat.ChatRoom")
def central_chatroom_deleted(sender, instance, **kwargs):
    """Central: Sync chatroom deletion to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(instance, "chatroom", "delete", sync_origin)


@receiver(post_delete, sender="chat.RoomMembership")
def central_room_membership_deleted(sender, instance, **kwargs):
    """Central: Sync membership deletion to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(instance, "roommembership", "delete", sync_origin)


@receiver(post_delete, sender="users.CustomUser")
def central_user_deleted(sender, instance, **kwargs):
    """Central: Sync user deletion to other nodes"""
    sync_origin = get_central_sync_handler().get_sync_origin()
    if sync_origin:
        safe_central_sync(instance, "user", "delete", sync_origin)
        safe_central_sync(instance, "user", "delete", sync_origin)
