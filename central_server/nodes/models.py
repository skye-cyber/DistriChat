from django.db import models
from django.utils import timezone
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()


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
    url = models.URLField(max_length=200, help_text="Node's base URL", unique=True)
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
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_node_name"),
            models.UniqueConstraint(fields=["url"], name="unique_node_url"),
        ]

    def save(self, *args, **kwargs):
        """Generate API key if not set"""

        if not self.api_key:
            self.api_key = self.generate_api_key()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status})"

    def generate_api_key(self):
        """Generate secure API key for node"""
        import secrets

        return secrets.token_urlsafe(32)

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

    def to_dict(self):
        return {
            "url": self.url,
            "name": self.name,
            "id": str(self.id),
            "api_key": self.api_key,
            "current_rooms": self.current_rooms,
            "max_rooms": self.max_rooms,
            "load": self.load,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "last_sync": self.last_sync,
        }


class NodeRegistration(models.Model):
    """
    Handles node registration requests and approvals.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node_name = models.CharField(max_length=100, unique=True)
    node_url = models.URLField(max_length=200)
    admin_email = models.EmailField()
    description = models.TextField(blank=True, null=True)
    max_rooms_capacity = models.IntegerField(default=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "node_registrations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Registration: {self.node_name} ({self.status})"


class LoadBalanceRule(models.Model):
    """
    Defines rules for load balancing across nodes.
    """

    RULE_TYPES = [
        ("round_robin", "Round Robin"),
        ("least_connections", "Least Connections"),
        ("weighted", "Weighted"),
        ("random", "Random"),
    ]

    name = models.CharField(max_length=100, unique=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(
        blank=True, null=True, help_text="Rule-specific configuration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "load_balance_rules"

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


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
