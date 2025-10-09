from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
from django.contrib.auth import get_user_model


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)

    # User preferences
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

    # Stats
    total_messages_sent = models.IntegerField(default=0)
    rooms_joined = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.username

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

    @property
    def is_admin(self):
        return self.is_superuser

    def _serialize_custom_user(self, instance):
        """Optimized custom user serialization"""
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
            "total_messages_sent": instance.total_messages_sent,
            "rooms_joined": instance.rooms_joined,
        }

    @property
    def to_sync_dict(self):
        """Optimized custom user sync"""
        return {
            "user_id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_online": self.is_online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "avatar": str(self.avatar) if self.avatar else None,
            "bio": self.bio or "",
            "notification_enabled": self.notification_enabled,
            "sound_enabled": self.sound_enabled,
            "total_messages_sent": self.total_messages_sent,
            "rooms_joined": self.rooms_joined,
        }


class UserSession(models.Model):
    """
    Track user sessions for online status.
    """

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sessions"
    )
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_sessions"
        ordering = ["-last_activity"]

    def __str__(self):
        return f"{self.user.username} - {self.last_activity}"

    def to_sync_dict(self):
        return {
            "user_id": str(self.user.id),
            "session_key": self.session_key,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "last_activity": self.last_activity,
        }


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

    def to_sync_dict(self):
        return {
            "user_id": self.user.id,
            "email": self.email,
            "is_online": self.is_online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "avatar": str(self.avatar) if self.avatar else None,
            "bio": self.bio or "",
            "notification_enabled": self.notification_enabled,
            "sound_enabled": self.sound_enabled,
            "total_messages_sent": self.total_messages_sent,
            "rooms_joined": self.rooms_joined,
        }


class UserActivity(models.Model):
    """
    Log user activities for analytics and monitoring.
    """

    ACTIVITY_TYPES = [
        ("login", "User Login"),
        ("logout", "User Logout"),
        ("message_sent", "Message Sent"),
        ("room_joined", "Room Joined"),
        ("room_created", "Room Created"),
        ("node_connected", "Node Connected"),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="activities"
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_activities"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"
