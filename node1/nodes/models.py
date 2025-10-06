from django.db import models

# from django.contrib.auth.models import User
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()


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
