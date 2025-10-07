from django.contrib import admin
from .models import NodeRegistration, LoadBalanceRule, NodeHeartbeat


@admin.register(NodeRegistration)
class NodeRegistrationAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing node registration requests and approvals.
    """

    list_display = (
        "node_name",
        "node_url",
        "admin_email",
        "status",
        "approved_by",
        "approved_at",
        "created_at",
    )
    list_filter = ("status", "approved_by", "created_at")
    search_fields = ("node_name", "admin_email", "description")
    readonly_fields = ("id", "approved_at", "created_at")
    ordering = ("-created_at",)
    list_editable = ("status",)
    list_per_page = 25

    fieldsets = (
        (
            "Node Information",
            {
                "fields": (
                    "node_name",
                    "node_url",
                    "admin_email",
                    "description",
                    "max_rooms_capacity",
                )
            },
        ),
        (
            "Approval Details",
            {
                "fields": (
                    "status",
                    "approved_by",
                    "approved_at",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "id",
                    "created_at",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        Automatically set approved_by and approved_at when status changes to 'approved'.
        """
        from django.utils import timezone

        if obj.status == "approved" and not obj.approved_at:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(LoadBalanceRule)
class LoadBalanceRuleAdmin(admin.ModelAdmin):
    """
    Admin configuration for defining and managing load-balancing rules.
    """

    list_display = ("name", "rule_type", "is_active", "created_at", "updated_at")
    list_filter = ("rule_type", "is_active")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    list_editable = ("is_active",)
    list_per_page = 25

    fieldsets = (
        (
            "Rule Details",
            {
                "fields": (
                    "name",
                    "rule_type",
                    "is_active",
                    "config",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(NodeHeartbeat)
class NodeHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("node", "timestamp", "load", "active_connections")
    list_filter = ("timestamp",)
    readonly_fields = ("timestamp",)
