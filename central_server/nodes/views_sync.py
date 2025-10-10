from chat.models import (
    Message,
    ChatRoom,
    RoomMembership,
    MessageReadStatus,
    SyncSession,
    MessageSyncLog,
    SystemLog,
)
from users.models import UserSession
import logging
from django.db import transaction, IntegrityError
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from nodes.models import Node
from django.utils import timezone
from django.contrib.auth import get_user_model
from chat.signals import get_central_sync_handler
from nodes.utils import fromiso_timezone_aware

User = get_user_model()

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class NodeSyncAPI(View):
    def post(self, request, node_id):
        """Receive sync data from nodes"""
        try:
            data = json.loads(request.body)

            # Validate node authentication
            if not self.authenticate_node(request, node_id):
                return JsonResponse({"error": "Authentication failed"}, status=401)

            # Process sync data
            result = self.process_sync_data(node_id, data)

            return JsonResponse(
                {
                    "status": "success",
                    "sync_id": str(result["sync_id"]),
                    "processed_messages": result["processed_count"],
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request, node_id):
        """Provide sync data to requesting nodes"""
        since = request.GET.get("since")
        room_id = request.GET.get("room_id")

        sync_data = self.get_sync_data(node_id, since, room_id)

        return JsonResponse(
            {"sync_data": sync_data, "server_timestamp": timezone.now().isoformat()}
        )

    def authenticate_node(self, request, node_id):
        """Authenticate node using API keys or tokens"""
        api_key = request.headers.get("X-Node-API-Key")
        node = Node.objects.filter(id=node_id, api_key=api_key).first()
        return node is not None

    def process_sync_data(self, node_id, data):
        """Process incoming sync data from nodes"""
        # Implementation for processing sync data
        pass


@method_decorator(csrf_exempt, name="dispatch")
class SyncReceiverAPI(View):
    def post(self, request):
        """Endpoint Receive sync data from nodes"""

        try:
            data = json.loads(request.body)
            handler = get_central_sync_handler()
            print(
                f"\033[1mRecv:\033[0m Action: {data['action']} \033[1mModel:\033[0m {data['model']} \033[1mFromNode:\033[0m {Node.objects.filter(id=data['origin_node_id']).first()}"
            )
            # Set the origin before saving
            node_id = data.get("origin_node_id")
            handler.set_sync_origin(node_id)

            # Authenticate node
            node = self.authenticate_node(request)
            if not node:
                return JsonResponse({"error": "Authentication failed"}, status=401)

            timestamp = data.get("timestamp")

            syncs = SyncSession.objects.create(
                source_node=node,
                started_at=timestamp,
                status="in_progress",
                sync_type="incremental",
            )

            SystemLog.objects.create(
                level="info",
                category="system",
                message=f"Sync triggered by signal from node:{node.name}",
                details=data,
                user=None,  # System triggered not user
                node=node,
            )

            model_name = data.get("model")
            action = data.get("action")
            sync_data = data.get("data")
            # node_id = data.get("node_id")

            # Process the sync request
            success = self.process_sync_request(
                node, model_name, action, sync_data, syncs
            )

            if success:
                syncs.status = "completed"
                syncs.completed_at = timezone.now()
                syncs.save()

                return JsonResponse(
                    {
                        "status": "success",
                        "processed_id": sync_data.get("id"),
                        "action": action,
                        "model": model_name,
                        "timestamp": timestamp,
                    },
                    status=200,
                )
            return JsonResponse(
                {
                    "status": "fail",
                    "processed_id": sync_data.get("id"),
                    "action": action,
                    "model": model_name,
                    "timestamp": timestamp,
                },
                status=500,
            )
        except Exception as e:
            logger.error(f"Sync receiver error: \033[31m{e}\033[0m")
            raise
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            # Always clear the origin
            handler.clear_sync_origin()

    def authenticate_node(self, request):
        """Authenticate node using API key"""
        api_key = request.headers.get("X-Node-API-Key")

        if not api_key:
            logger.info("Authentication failure: mising API KEY")
            return None
        logger.info(
            f"Node: {json.loads(request.body).get('node_id', '')} Authenticated"
        )

        return Node.objects.filter(api_key=api_key).first()

    def process_sync_request(self, node, model_name, action, sync_data, syncs):
        """Process incoming sync request"""
        with transaction.atomic():
            if model_name == "message":
                return self.process_message_sync(action, sync_data, node, syncs)
            elif model_name == "chatroom":
                return self.process_chatroom_sync(action, sync_data, node)
            elif model_name == "roommembership":
                return self.process_roommembership_sync(action, sync_data, node)
            elif model_name == "messagereadstatus":
                return self.process_messagereadstatus_sync(action, sync_data, node)
            elif model_name == "session":
                return self.process_session_sync(action, sync_data, node)
            elif model_name == "user":
                return self.process_user_sync(action, sync_data, node)
            else:
                raise ValueError(f"Unknown model: {model_name}")

    def process_message_sync(self, action, data, node, syncs):
        """Process message sync operations"""
        if action == "create":
            return self.create_or_update_message(data, node, syncs)
        elif action == "update":
            return self.create_or_update_message(data, node, syncs)
        elif action == "delete":
            return self.delete_message(data, syncs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create_or_update_message(self, data, node, syncs):
        """Create or update message in central server"""
        try:
            # Get related objects
            q_room = ChatRoom.objects.filter(id=data["room_id"])
            if not q_room.exists():
                logger.error(f"ChatRoom {data['room_id']} not found for message sync")
                return None

            room = q_room.first()
            sender = User.objects.get(username=data["sender_username"])
            # Create or update message
            message, created = Message.objects.update_or_create(
                id=data["id"],
                defaults={
                    "room": room,
                    "sender": sender,
                    "content": data["content"],
                    "message_type": data.get("message_type", "text"),
                    "created_at": fromiso_timezone_aware(data["created_at"]),
                    "updated_at": fromiso_timezone_aware(data["updated_at"]),
                    "is_edited": data.get("is_edited", False),
                    "is_deleted": data.get("is_deleted", False),
                },
            )

            MessageSyncLog.objects.create(
                sync_session=syncs,
                message=message,
                action="create" if created else "update",
            )

            if created:
                syncs.messages_synced += 1
                syncs.save()

            logger.info(
                f"{'Created' if created else 'Updated'} message {message.id} from node {node.name}"
            )
            return message

        except ChatRoom.DoesNotExist:
            syncs.status = "failed"
            syncs.save()
            logger.error(f"ChatRoom {data['room_id']} not found for message sync")
        except User.DoesNotExist:
            syncs.status = "failed"
            syncs.save()
            logger.error(f"User {data['sender_username']} not found for message sync")

    def delete_message(self, data, syncs) -> bool:
        """
        Delete message in central server
        Args:
        data: sync request data type->dict
        syncs: Sync Session"""
        try:
            q_message = Message.objects.filter(id=data["id"])
            if q_message.exists():
                q_message.first().delete()

                logger.info(f"Deleted message {data['id']}")
            logger.error(f"Message not found for deletion: {data['id']}")
            return True
        except Message.DoesNotExist:
            logger.warning(f"Message {data['id']} not found for deletion")
            return True  # Already deleted, consider success

    def process_chatroom_sync(self, action, data, node):
        """Process chatroom sync operations"""
        if action == "create":
            return self.create_or_update_chatroom(data, node)
        elif action == "update":
            return self.create_or_update_chatroom(data, node)
        elif action == "delete":
            return self.delete_chatroom(data)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create_or_update_chatroom(self, data, node):
        """Create or update chatroom in central server"""
        try:
            # Get related objects
            room_node = Node.objects.get(id=data["node_id"])
            created_by = User.objects.get(username=data["created_by_username"])

            # Create or update chatroom
            chatroom, created = ChatRoom.objects.update_or_create(
                id=data["id"],
                defaults={
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "room_type": data.get("room_type", "public"),
                    "node": room_node,
                    "created_by": created_by,
                    "is_active": data.get("is_active", True),
                    "max_members": data.get("max_members", 100),
                    "created_at": fromiso_timezone_aware(data["created_at"]),
                    "updated_at": fromiso_timezone_aware(
                        data.get("updated_at", data["created_at"])
                    ),
                },
            )

            logger.info(
                f"{'Created' if created else 'Updated'} chatroom {chatroom.name} from node {node.name}"
            )
            return chatroom

        except Node.DoesNotExist:
            logger.error(f"Node {data['node_id']} not found for chatroom sync")
            raise
        except User.DoesNotExist:
            logger.error(
                f"User {data['created_by_username']} not found for chatroom sync"
            )
            raise

    def delete_chatroom(self, data) -> bool:
        """Delete chatroom in central server"""
        try:
            q_chatroom = ChatRoom.objects.filter(id=data["id"])
            if q_chatroom.exists():
                room = q_chatroom.first()
                room.delete()
                logger.info(f"Deleted chatroom {data['id']}")
            return True
        except ChatRoom.DoesNotExist:
            logger.warning(f"ChatRoom {data['id']} not found for deletion")
            return True

    def process_roommembership_sync(self, action, data, node):
        """Process room membership sync operations"""
        if action == "create":
            return self.create_or_update_roommembership(data)
        elif action == "update":
            return self.create_or_update_roommembership(data)
        elif action == "delete":
            return self.delete_roommembership(data)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create_or_update_roommembership(self, data):
        """Create or update room membership in central server"""
        try:
            room = ChatRoom.objects.get(id=data["room_id"])
            user = User.objects.get(username=data["username"])

            membership, created = RoomMembership.objects.update_or_create(
                room=room,
                user=user,
                defaults={
                    "role": data.get("role", "member"),
                    "joined_at": fromiso_timezone_aware(data["joined_at"]),
                    "last_read": fromiso_timezone_aware(
                        data.get("last_read", data["joined_at"])
                    ),
                },
            )

            logger.info(
                f"{'Created' if created else 'Updated'} membership for user {user.username} in room {room.name}"
            )
            return membership

        except ChatRoom.DoesNotExist:
            logger.error(f"ChatRoom {data['room_id']} not found for membership sync")
            raise
        except User.DoesNotExist:
            logger.error(f"User {data['username']} not found for membership sync")
            raise

    def delete_roommembership(self, data) -> bool:
        """Delete room membership in central server"""
        try:
            room = ChatRoom.objects.get(id=data["room_id"])
            user = User.objects.get(username=data["username"])

            q_membership = RoomMembership.objects.filter(room=room, user=user)
            if q_membership.exists():
                q_membership.first().delete()
                logger.info(
                    f"Deleted membership for user {user.username} in room {room.name}"
                )
            return True

        except (ChatRoom.DoesNotExist, User.DoesNotExist, RoomMembership.DoesNotExist):
            logger.warning(f"RoomMembership not found for deletion: {data['room_id']}")
            return True

    def process_messagereadstatus_sync(self, action, data, node):
        """Process message sync operations"""
        if action == "create":
            return self.create_or_update_messagereadstatus(data, node)
        elif action == "update":
            return self.create_or_update_messagereadstatus(data, node)
        elif action == "delete":
            return self.delete_messagereadstatus(data)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create_or_update_messagereadstatus(self, data, node):
        """Create or update message in central server"""
        try:
            # Get related objects
            user = User.objects.get(username=data["username"])

            message = Message.objects.get(id=data["message_id"])

            # Create or update message
            messageStatus, created = MessageReadStatus.objects.update_or_create(
                id=data["id"],
                defaults={
                    "message": message,
                    "user": user,
                    "read_at": fromiso_timezone_aware(data["read_at"]),
                },
            )

            logger.info(
                f"{'Created' if created else 'Updated'} message read status {messageStatus.id} from node {node.name}"
            )
            return messageStatus

        except User.DoesNotExist:
            logger.error(
                f"User {data['room_id']} not found for message read status sync"
            )
            raise
        except Message.DoesNotExist:
            logger.error(
                f"Message {data['message_id']} not found for message read status sync"
            )

    def delete_messagereadstatus(self, data) -> bool:
        """Delete message in central server"""
        try:
            # Get related objects
            user = User.objects.get(username=data["username"])

            message = Message.objects.get(id=data["message_id"])

            q_messageStatus = MessageReadStatus.objects.filter(
                message=message, user=user
            )
            if q_messageStatus.exists():
                q_messageStatus.first().delete()
                logger.info(f"Deleted message {data['message_id']}")
            return True
        except MessageReadStatus.DoesNotExist:
            logger.warning(
                f"MessageReadStatus {data['message_id']} not found for deletion"
            )
            return True  # Already deleted, consider success
        except Message.DoesNotExist:
            logger.warning(f"Message {data['message_id']} not found for deletion")
            return True  # Already deleted, consider success

    def process_session_sync(self, action, data, node):
        """Process message sync operations"""
        if action == "create":
            return self.create_or_update_session(data, node)
        elif action == "update":
            return self.create_or_update_session(data, node)
        elif action == "delete":
            return self.delete_session(data)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create_or_update_session(self, data, node):
        """Create or update message in central server"""
        try:
            # Create or update message
            session, created = UserSession.objects.update_or_create(
                username=data["username"],
                defaults={
                    "session_key": data["session_key"],
                    "ip_address": data["ip_address"],
                    "user_agent": data["user_agent"],
                    "last_activity": data["last_activity"],
                },
            )

            logger.info(
                f"{'Created' if created else 'Updated'} session {session.id} from node {node.name}"
            )
            return session

        except UserSession.DoesNotExist:
            logger.error(f"Session {data['id']} not found for session sync")
            raise

    def delete_session(self, data) -> bool:
        """Delete message in central server"""
        try:
            # Get related objects
            session = UserSession.objects.get(id=data["id"])

            session.delete()
            logger.info(f"Deleted session {data['id']}")
            return True
        except UserSession.DoesNotExist:
            logger.warning(f"Session {data['id']} not found for deletion")
            return True  # Already deleted, consider success

    def process_user_sync(self, action, data, node):
        """Process message sync operations"""
        if action == "create":
            return self.create_or_update_user(data, node)
        elif action == "update":
            return self.create_or_update_user(data, node)
        elif action == "delete":
            return self.delete_session(data)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create_or_update_user(self, data, node):
        """Create or update message in central server"""
        try:
            with transaction.atomic():
                # Create or update message
                user, created = User.objects.update_or_create(
                    username=data["username"],
                    defaults={
                        "email": data["email"],
                        "is_online": data["is_online"],
                        "last_seen": fromiso_timezone_aware(data["last_seen"]),
                        "avatar": data["avatar"],
                        "bio": data["bio"],
                        "notification_enabled": data["notification_enabled"],
                        "sound_enabled": data["sound_enabled"],
                        "total_messages_sent": data["total_messages_sent"],
                        "rooms_joined": data["rooms_joined"],
                    },
                )

                # Avoid overwriting user password
                if created and data.get("password", None):
                    user_id = data.get("user_id", None)
                    user.id = user_id if user_id else user.id
                    user.password = data["password"]
                    user.save()

                logger.info(
                    f"{'Created' if created else 'Updated'} user: {user.id} from node {node.name}"
                )
            return user

        except IntegrityError as e:
            print(f"Error updating/creating user: \033[91m{e}\033[0m")
            logger.error(e)
        except User.DoesNotExist:
            logger.error(f"User {data['username']} not found for user sync")

    def delete_user(self, data) -> bool:
        """Delete message in central server"""
        try:
            # Get related objects
            q_user = User.objects.filter(username=data["username"])
            if q_user.exists():
                q_user.first().delete()
                logger.info(f"Deleted user {data['username']}")
            return True
        except User.DoesNotExist:
            logger.warning(f"User {data['username']} not found for deletion")
            return True  # Already deleted, consider success


@csrf_exempt
def sync_status(request):
    last_session = SyncSession.objects.order_by("-started_at").first()
    return last_session.status


@method_decorator(csrf_exempt, name="dispatch")
class SyncStatsAPI(View):
    def get(self, request):
        """Get sync status and statistics"""
        # Authenticate node
        node = self.authenticate_node(request)
        if not node:
            return JsonResponse({"error": "Authentication failed"}, status=401)

        stats = {
            "node_name": node.name,
            "last_sync": node.last_sync.isoformat() if node.last_sync else None,
            "sync_enabled": node.sync_enabled,
            "message_count": Message.objects.count(),
            "room_count": ChatRoom.objects.count(),
            "membership_count": RoomMembership.objects.count(),
            "central_server_time": timezone.now().isoformat(),
        }

        return JsonResponse({"status": "success", "stats": stats})

    def authenticate_node(self, request):
        """Authenticate node using API key"""
        api_key = request.headers.get("X-Node-API-Key")
        if not api_key:
            return None
        return Node.objects.filter(api_key=api_key).first()
