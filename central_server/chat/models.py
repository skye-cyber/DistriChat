from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid


class Node(models.Model):
    """
    Represents a distributed node in the system.
    """

    NODE_STATUS = [
        ("online", "Online"),
        ("offline", "Offline"),
        ("maintenance", "Maintenance"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=200, help_text="Node's base URL")
    status = models.CharField(max_length=20, choices=NODE_STATUS, default="offline")
    load = models.FloatField(default=0.0, help_text="Current load percentage (0-100)")
    max_rooms = models.IntegerField(
        default=50, help_text="Maximum rooms this node can handle"
    )
    current_rooms = models.IntegerField(
        default=0, help_text="Current number of active rooms"
    )
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    api_key = models.CharField(max_length=64, unique=True, blank=True, null=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_enabled = models.BooleanField(default=True)
    auto_sync_interval = models.IntegerField(default=300)  # 5 minutes in seconds

    class Meta:
        db_table = "nodes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"

    def generate_api_key(self):
        """Generate secure API key for node"""
        import secrets

        self.api_key = secrets.token_urlsafe(32)
        self.save()

    @property
    def is_online(self):
        """Check if node is currently online based on heartbeat"""
        if not self.last_heartbeat:
            return False
        return (
            timezone.now() - self.last_heartbeat
        ).total_seconds() < 60  # 1 minute threshold

    @property
    def available_capacity(self):
        """Calculate available room capacity"""
        return max(0, self.max_rooms - self.current_rooms)

    def update_load(self):
        """Update node load based on current rooms"""
        if self.max_rooms > 0:
            self.load = (self.current_rooms / self.max_rooms) * 100
        else:
            self.load = 0
        self.save()


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


class UserProfile(models.Model):
    """
    Extended user profile with chat-specific information.
    """

    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="profile"
    )

    # Online status
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    # get_user_model() preferences
    color_scheme = models.CharField(
        max_length=20,
        default="blue",
        choices=[
            ("blue", "Blue"),
            ("green", "Green"),
            ("purple", "Purple"),
            ("red", "Red"),
            ("yellow", "Yellow"),
            ("indigo", "Indigo"),
            ("pink", "Pink"),
        ],
    )
    notification_enabled = models.BooleanField(default=True)
    sound_enabled = models.BooleanField(default=True)

    # get_user_model() stats
    total_messages_sent = models.IntegerField(default=0)
    rooms_joined = models.IntegerField(default=0)

    # Profile information
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True, null=True, max_length=500)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def color(self):
        """Get user's color for UI elements"""
        return self.color_scheme

    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = timezone.now()
        self.save()

    def increment_message_count(self):
        """Increment total messages sent"""
        self.total_messages_sent += 1
        self.save()


class NodeHeartbeat(models.Model):
    """
    Tracks heartbeat signals from nodes for monitoring.
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="heartbeats")
    timestamp = models.DateTimeField(auto_now_add=True)
    load = models.FloatField(help_text="Node load at heartbeat time")
    active_connections = models.IntegerField(
        help_text="Number of active WebSocket connections"
    )
    memory_usage = models.FloatField(help_text="Memory usage in MB")
    cpu_usage = models.FloatField(help_text="CPU usage percentage")

    class Meta:
        db_table = "node_heartbeats"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Heartbeat for {self.node.name} at {self.timestamp}"


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
        Node, on_delete=models.CASCADE, related_name="sync_targets"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
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
