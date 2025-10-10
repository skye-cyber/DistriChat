from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import requests
import logging
import threading
from nodes.utils import handler
from nodes.models import PeerNode

logger = logging.getLogger(__name__)

# Thread-local storage for node metadata
_node_metadata_local = threading.local()
# print(handler.get_sync_origin())


class NodeSyncSignalHandler:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if not self._initialized:
            self.central_server_url = getattr(settings, "CENTRAL_SERVER_URL", None)
            self.is_node = getattr(settings, "IS_NODE", False)
            self._node_metadata = None
            self._initialized = True

    @property
    def node_metadata(self):
        """Lazy loading of node metadata"""
        if not hasattr(_node_metadata_local, "node_metadata"):
            if self._node_metadata is None:
                self._load_node_metadata()
            _node_metadata_local.node_metadata = self._node_metadata
        return _node_metadata_local.node_metadata

    def _load_node_metadata(self):
        """Load node metadata only when needed"""
        try:
            from nodes.models import NodeMetadata

            node_name = getattr(settings, "NODE_NAME", None)
            if node_name:
                self._node_metadata = NodeMetadata.objects.filter(
                    name=node_name
                ).first()
                if not self._node_metadata:
                    logger.warning(f"NodeMetadata not found for name: {node_name}")
            else:
                logger.warning("NODE_NAME not set in settings")
        except Exception as e:
            logger.error(f"Failed to load node metadata: {e}")
            self._node_metadata = None

    @property
    def node_api_key(self):
        return (
            getattr(self.node_metadata, "api_key", None) if self.node_metadata else None
        )

    @property
    def node_id(self):
        return getattr(self.node_metadata, "id", None) if self.node_metadata else None

    def should_sync(self):
        """Check if sync should be performed"""
        # handler.set_defaults()
        origin_id, origin_name = handler.get_sync_origin()
        logger.debug("Env", origin_id, origin_name)

        q_origin_node = PeerNode.objects.filter(id=origin_id)

        origin = None
        same_origin = False
        if q_origin_node.exists():
            origin = q_origin_node.first()
            same_origin = origin.name != settings.NODE_NAME

        logger.debug(
            f"\033[1mShould broadcast sync:\033[0m Same origin:\033[35m {origin_name} - {same_origin}\033[0m"
        )
        return (
            self.is_node
            and self.central_server_url
            and self.node_api_key
            and self.node_id
            and (not same_origin and origin_name != "CENTRAL_SERVER")
        )

    def send_sync_request(self, model_name, instance, action, data=None):
        """Send sync request to central server with rate limiting"""
        if not self.should_sync():
            logger.debug("\033[36mNot Syncing\033[0m")
            return

        # Use thread pool for async execution to avoid blocking
        thread = threading.Thread(
            target=self._send_sync_request_async,
            args=(model_name, instance, action, data),
            daemon=True,
        )
        thread.start()

    def _send_sync_request_async(self, model_name, instance, action, data=None):
        """Async implementation of sync request"""
        try:
            sync_data = {
                "model": model_name,
                "action": action,
                "data": self.serialize_instance(instance, data),
                "timestamp": timezone.now().isoformat(),
                "origin_node_id": str(self.node_id),
            }

            response = requests.post(
                f"{self.central_server_url}/nodes/api/sync/receive/",
                json=sync_data,
                headers={
                    "X-Node-API-Key": str(self.node_api_key),
                    "X-ORIGIN": settings.NODE_NAME,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )

            if response.status_code == 200:
                print(f"DEBUG: Sync successful for {model_name} {action}")
                logger.debug(
                    f"\033[32mSync to CENTRAL_SERVER successful for {model_name} {action}: {instance.id}\033[0m"
                )
            else:
                logger.warning(
                    f"\033[31mSync to CENTRAL_SERVER failed {response.status_code}: {model_name} {action}\033[0m"
                )

        except requests.exceptions.Timeout:
            logger.warning(f"Sync timeout for {model_name} {action}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error during sync for {model_name} {action}")
        except Exception as e:
            raise
            logger.error(f"Sync error for {model_name} {action}: {e}")

    def serialize_instance(self, instance, data=None):
        """Serialize model instance for sync with optimized field selection"""
        # Use model's to_sync_dict if available
        if data and isinstance(data, dict):
            return data
        if hasattr(instance, "to_sync_dict"):
            try:
                return (
                    instance.to_sync_dict
                    if isinstance(instance.to_sync_dict, dict)
                    else instance.to_sync_dict()
                )
            except Exception:
                pass

        data = {"id": str(instance.id)}
        model_class = type(instance)

        # Model-specific field mappings
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
        """Optimized message serialization"""
        return {
            "id": str(instance.id),
            "room_id": str(instance.room_id),
            "sender_username": str(instance.sender_username),
            "content": instance.content,
            "message_type": instance.message_type,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
            "is_edited": instance.is_edited,
            "is_deleted": instance.is_deleted,
        }

    def _serialize_chatroom(self, instance):
        """Optimized chatroom serialization"""
        return {
            "id": str(instance.id),
            "node_id": str(instance.node.id),
            "name": instance.name,
            "description": instance.description or "",
            "room_type": instance.room_type,
            # "node_id": str(self.node_id),
            "created_by_username": str(instance.created_by_username),
            "is_active": instance.is_active,
            "max_members": instance.max_members,
            "created_at": instance.created_at.isoformat(),
            "sync_version": 1,
        }

    def _serialize_room_membership(self, instance):
        """Optimized room membership serialization"""
        return {
            "key": f"{instance.room.id}_{instance.user.id}",
            "id": str(instance.id),
            "room_id": str(instance.room_id),
            "username": str(instance.username),
            "role": instance.role,
            "joined_at": instance.joined_at.isoformat(),
            "last_read": instance.last_read,
        }

    def _serialize_message_read_status(self, instance):
        """Optimized message read status serialization"""
        return {
            "id": str(instance.id),
            "message_id": str(instance.message_id),
            "username": str(instance.username),
            "read_at": instance.read_at.isoformat(),
        }

    def _serialize_user_session(self, instance):
        """Optimized user session serialization"""
        return {
            "username": str(instance.user.username),
            "session_key": instance.session_key,
            "ip_address": instance.ip_address or "",
            "user_agent": instance.user_agent or "",
            "last_activity": instance.last_activity.isoformat(),
        }

    def _serialize_custom_user(self, instance):
        """Optimized custom user serialization"""
        return {
            "password": instance.password,
            "user_id": str(instance.id),
            "username": instance.username,
            "email": instance.email,
            "is_online": instance.is_online,
            "last_seen": instance.last_seen.isoformat() if instance.last_seen else None,
            "avatar": str(instance.avatar) if instance.avatar else None,
            "bio": instance.bio or "",
            "notification_enabled": instance.notification_enabled,
            "sound_enabled": instance.sound_enabled,
            "total_messages_sent": instance.total_messages_sent,
            "rooms_joined": instance.rooms_joined,
        }


# Global signal handler instance
_sync_handler = None


def get_sync_handler():
    """Lazy initialization of sync handler"""
    global _sync_handler
    if _sync_handler is None:
        _sync_handler = NodeSyncSignalHandler()
    return _sync_handler


def safe_sync_signal(instance, model_name, action, created=None, data=None):
    """
    Safe wrapper for sync signals that handles initialization issues
    """
    try:
        handler = get_sync_handler()
        if handler.should_sync():
            handler.send_sync_request(model_name, instance, action, data)
    except Exception as e:
        raise
        logger.error(f"Safe sync signal error for {model_name} {action}: {e}")


# Signal receivers with safe execution
@receiver(post_save, sender="chat.Message")
def message_saved(sender, instance, created, **kwargs):
    """Trigger sync when message is created or updated"""
    safe_sync_signal(instance, "message", "create" if created else "update", created)


@receiver(pre_delete, sender="chat.Message")
def message_deleted(sender, instance, **kwargs):
    """Trigger sync when message is deleted"""
    safe_sync_signal(instance, "message", "delete", data=instance.to_sync_dict())


@receiver(post_save, sender="chat.ChatRoom")
def chatroom_saved(sender, instance, created, **kwargs):
    """Trigger sync when chat room is created or updated"""
    print("DISPATCHING ROOM CREATION UPDATE SIGNAL..")
    safe_sync_signal(instance, "chatroom", "create" if created else "update", created)


@receiver(pre_delete, sender="chat.ChatRoom")
def chatroom_deleted(sender, instance, **kwargs):
    """Trigger sync when chat room is deleted"""
    print("DISPATCHING ROOM DELETION SIGNAL..")
    safe_sync_signal(instance, "chatroom", "delete", data=instance.to_sync_dict())


@receiver(post_save, sender="chat.RoomMembership")
def room_membership_saved(sender, instance, created, **kwargs):
    """Trigger sync when room membership changes"""
    safe_sync_signal(
        instance, "roommembership", "create" if created else "update", created
    )


@receiver(pre_delete, sender="chat.RoomMembership")
def room_membership_deleted(sender, instance, **kwargs):
    """Trigger sync when room membership is removed"""
    safe_sync_signal(instance, "roommembership", "delete", data=instance.to_sync_dict())


@receiver(post_save, sender="users.CustomUser")
def user_saved(sender, instance, created, **kwargs):
    """Trigger sync when user is saved"""
    safe_sync_signal(instance, "user", "create" if created else "update", created)


@receiver(pre_delete, sender="users.CustomUser")
def user_deleted(sender, instance, **kwargs):
    """Trigger sync when user is deleted"""
    print("DISPATCHING USER CREATION UPDATE SIGNAL..")
    safe_sync_signal(instance, "user", "delete", data=instance.to_sync_dict())


@receiver(post_save, sender="chat.MessageReadStatus")
def message_status_saved(sender, instance, created, **kwargs):
    """Trigger sync when message status is saved"""
    print("DISPATCHING MESSAGE READ SIGNAL..")
    safe_sync_signal(
        instance, "messagereadstatus", "create" if created else "update", created
    )


@receiver(pre_delete, sender="chat.MessageReadStatus")
def message_read_status_deleted(sender, instance, **kwargs):
    """Trigger sync when message status is deleted"""
    safe_sync_signal(
        instance, "messagereadstatus", "delete", data=instance.to_sync_dict()
    )


@receiver(post_save, sender="users.UserSession")
def session_saved(sender, instance, created, **kwargs):
    """Trigger sync when session is saved"""
    safe_sync_signal(instance, "session", "create" if created else "update", created)


@receiver(pre_delete, sender="users.UserSession")
def session_deleted(sender, instance, **kwargs):
    """Trigger sync when session is deleted"""
    safe_sync_signal(instance, "session", "delete", data=instance.to_sync_dict())
