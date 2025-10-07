from django.db import models
from django.contrib.auth import get_user_model
from nodes.models import Node
import uuid


class ChatRoom(models.Model):
    """
    Represents a chat room that can be hosted on any node.
    """

    ROOM_TYPES = [
        ("public", "Public"),
        ("private", "Private"),
        ("direct", "Direct Message"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="public")
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="chat_rooms")
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="created_rooms"
    )
    members = models.ManyToManyField(
        get_user_model(), through="RoomMembership", related_name="chat_rooms"
    )
    is_active = models.BooleanField(default=True)
    max_members = models.IntegerField(
        default=100, help_text="Maximum members allowed in room"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_rooms"
        ordering = ["-created_at"]
        unique_together = ["name", "node"]

    def __str__(self):
        return f"{self.name} (Node: {self.node.name})"

    @property
    def member_count(self):
        """Get current number of members in room"""
        return self.members.count()

    @property
    def online_member_count(self):
        """Get number of currently online members"""
        return self.members.filter(profile__is_online=True).count()

    def add_member(self, user):
        """Add a member to the room"""
        RoomMembership.objects.get_or_create(room=self, user=user)

    def remove_member(self, user):
        """Remove a member from the room"""
        RoomMembership.objects.filter(room=self, user=user).delete()

    def to_sync_dict(self):
        """Convert chat room to sync dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "room_type": self.room_type,
            "node_id": str(self.node.id),
            "created_by_id": str(self.created_by.id),
            "is_active": self.is_active,
            "max_members": self.max_members,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sync_version": 1,
        }


class RoomMembership(models.Model):
    """
    Through model for ChatRoom members with additional metadata.
    """

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "room_memberships"
        unique_together = ["room", "user"]

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"

    def to_sync_dict(self):
        """Convert room membership to sync dictionary"""
        return {
            "id": f"{self.room.id}_{self.user.id}",  # Composite key
            "room_id": str(self.room.id),
            "user_id": str(self.user.id),
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
            "last_read": self.last_read.isoformat() if self.last_read else None,
            "sync_version": 1,
        }


class Message(models.Model):
    """
    Represents a message in a chat room.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=[
            ("text", "Text"),
            ("image", "Image"),
            ("file", "File"),
            ("system", "System Message"),
        ],
        default="text",
    )
    # For media messages
    media_url = models.URLField(blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.IntegerField(blank=True, null=True)

    # Message status
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("synced", "Synced"), ("failed", "Failed")],
        default="pending",
    )
    last_sync_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"

    @property
    def timestamp(self):
        """Formatted timestamp for display"""
        return self.created_at

    def mark_as_read_by(self, user):
        """Mark this message as read by a user"""
        MessageReadStatus.objects.get_or_create(message=self, user=user)

    def to_sync_dict(self):
        """Convert message to sync dictionary"""
        return {
            "id": str(self.id),
            "room_id": str(self.room.id),
            "sender_id": str(self.sender.id),
            "content": self.content,
            "message_type": self.message_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "sync_version": 1,  # For conflict resolution
        }


class MessageReadStatus(models.Model):
    """
    Tracks which users have read which messages.
    """

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="read_status"
    )
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="message_reads"
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_read_status"
        unique_together = ["message", "user"]

    def __str__(self):
        return f"{self.user.username} read message at {self.read_at}"


class SystemLog(models.Model):
    """
    System-wide logging for monitoring and debugging.
    """

    LOG_LEVELS = [
        ("debug", "Debug"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("critical", "Critical"),
    ]

    LOG_CATEGORIES = [
        ("node", "Node"),
        ("message", "Message"),
        ("user", "get_user_model()"),
        ("system", "System"),
        ("security", "Security"),
    ]

    level = models.CharField(max_length=20, choices=LOG_LEVELS)
    category = models.CharField(max_length=20, choices=LOG_CATEGORIES)
    message = models.TextField()
    details = models.JSONField(blank=True, null=True)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, blank=True, null=True
    )
    node = models.ForeignKey(Node, on_delete=models.SET_NULL, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["level", "timestamp"]),
            models.Index(fields=["category", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] {self.message}"


class SyncSession(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    source_node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="sync_sources"
    )
    target_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="sync_targets",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    sync_type = models.CharField(
        max_length=20, choices=[("full", "Full"), ("incremental", "Incremental")]
    )
    messages_synced = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]


class MessageSyncLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    sync_session = models.ForeignKey(
        SyncSession, on_delete=models.CASCADE, related_name="synced_messages"
    )
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    action = models.CharField(
        max_length=10,
        choices=[("create", "Create"), ("update", "Update"), ("delete", "Delete")],
    )
    synced_at = models.DateTimeField(auto_now_add=True)
