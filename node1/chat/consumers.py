import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, RoomMembership
from users.models import UserActivity
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]

        # Check if user is authenticated and can join the room
        if self.user.is_anonymous:
            await self.close()
            return

        if not await self.is_room_member():
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Update user online status
        await self.update_user_online_status(True)

        # Send join notification
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_join",
                "user": self.user.username,
                "user_id": str(self.user.id),
            },
        )

        logger.info(f"User {self.user.username} connected to room {self.room_id}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Update user online status
        await self.update_user_online_status(False)

        # Send leave notification
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_leave",
                "user": self.user.username,
                "user_id": str(self.user.id),
            },
        )

        logger.info(f"User {self.user.username} disconnected from room {self.room_id}")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type", "chat_message")

            if message_type == "chat_message":
                message_content = text_data_json["message"]
                await self.handle_chat_message(message_content)
            elif message_type == "typing":
                await self.handle_typing_indicator(text_data_json)
            elif message_type == "read_receipt":
                await self.handle_read_receipt(text_data_json)

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def handle_chat_message(self, message_content):
        """Handle incoming chat messages."""
        # Save message to database
        message = await self.save_message(message_content)

        if message:
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message_content,
                    "sender": self.user.username,
                    "sender_id": str(self.user.id),
                    "color": self.user.color_scheme,
                    "timestamp": message.created_at.isoformat(),
                    "message_id": str(message.id),
                },
            )

            # Log activity
            await self.log_message_activity(message)

    async def handle_typing_indicator(self, data):
        """Handle typing indicators."""
        is_typing = data.get("typing", False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "user": self.user.username,
                "user_id": str(self.user.id),
                "typing": is_typing,
            },
        )

    async def handle_read_receipt(self, data):
        """Handle read receipts."""
        message_id = data.get("message_id")
        if message_id:
            await self.mark_message_as_read(message_id)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read_receipt",
                    "user": self.user.username,
                    "user_id": str(self.user.id),
                    "message_id": message_id,
                },
            )

    # Handler methods for different message types
    async def chat_message(self, event):
        """Receive chat message from room group."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "message": event["message"],
                    "sender": event["sender"],
                    "sender_id": event["sender_id"],
                    "color": event["color"],
                    "timestamp": event["timestamp"],
                    "message_id": event["message_id"],
                }
            )
        )

    async def user_join(self, event):
        """Handle user join notifications."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_join",
                    "user": event["user"],
                    "user_id": event["user_id"],
                    "timestamp": timezone.now().isoformat(),
                }
            )
        )

    async def user_leave(self, event):
        """Handle user leave notifications."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_leave",
                    "user": event["user"],
                    "user_id": event["user_id"],
                    "timestamp": timezone.now().isoformat(),
                }
            )
        )

    async def typing_indicator(self, event):
        """Handle typing indicators."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "user": event["user"],
                    "user_id": event["user_id"],
                    "typing": event["typing"],
                }
            )
        )

    async def read_receipt(self, event):
        """Handle read receipts."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "read_receipt",
                    "user": event["user"],
                    "user_id": event["user_id"],
                    "message_id": event["message_id"],
                }
            )
        )

    # Database operations
    @database_sync_to_async
    def is_room_member(self):
        """Check if user is a member of the room."""
        return RoomMembership.objects.filter(
            room_id=self.room_id, user=self.user
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database."""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            message = Message.objects.create(
                room=room, sender=self.user, content=content
            )

            # Update user message count
            self.user.total_messages_sent += 1
            self.user.save()

            return message
        except ChatRoom.DoesNotExist:
            logger.error(f"Room {self.room_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def update_user_online_status(self, is_online):
        """Update user's online status."""
        self.user.is_online = is_online
        self.user.save()

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark a message as read by the user."""
        try:
            from .models import MessageReadStatus

            message = Message.objects.get(id=message_id)
            MessageReadStatus.objects.get_or_create(message=message, user=self.user)
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found")

    @database_sync_to_async
    def log_message_activity(self, message):
        """Log message sending activity."""
        UserActivity.objects.create(
            user=self.user,
            activity_type="message_sent",
            description=f'Sent message in room "{message.room.name}"',
            metadata={
                "room_id": str(message.room.id),
                "message_id": str(message.id),
                "message_length": len(message.content),
            },
        )
