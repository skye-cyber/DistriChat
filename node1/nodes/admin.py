from django.contrib import admin
from nodes.models import NodeMetadata, PeerNode


@admin.register(PeerNode)
class PeerNodeAdmin(admin.ModelAdmin):
    """
    Admin configuration for PeerNode model.
    """

    list_display = (
        "name",
        "url",
        "status",
        "load",
        "current_rooms",
        "max_rooms",
        "available_capacity",
        "is_online",
        "last_heartbeat",
        "last_sync",
        "sync_enabled",
        "created_at",
    )

    list_filter = (
        "status",
        "sync_enabled",
        "created_at",
    )

    search_fields = (
        "name",
        "url",
        "api_key",
    )

    readonly_fields = (
        "id",
        "api_key",
        "created_at",
        "updated_at",
        "load",
        "available_capacity",
        "is_online",
    )

    fieldsets = (
        ("Node Information", {"fields": ("name", "url", "status")}),
        (
            "Capacity & Load",
            {"fields": ("max_rooms", "current_rooms", "load", "available_capacity")},
        ),
        (
            "Synchronization",
            {"fields": ("sync_enabled", "auto_sync_interval", "last_sync")},
        ),
        ("Security", {"fields": ("api_key",)}),
        ("Monitoring", {"fields": ("last_heartbeat", "is_online")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    ordering = ("-created_at",)
    list_per_page = 25

    def get_queryset(self, request):
        """Optimize queryset for better performance."""
        qs = super().get_queryset(request)
        return qs.defer("api_key")  # don’t load the key unless needed

    @admin.display(boolean=True, description="Online")
    def is_online(self, obj):
        """Show green checkmark if node is online."""
        return obj.is_online

    @admin.display(description="Available Capacity")
    def available_capacity(self, obj):
        """Show available capacity as integer."""
        return obj.available_capacity


@admin.register(NodeMetadata)
class NodeMetadataAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing node metadata.
    """

    list_display = (
        "name",
        "url",
        "api_key",
        "created_at",
        "updated_at",
    )
    list_filter = ("name", "api_key", "created_at")
    search_fields = ("name", "url")
    readonly_fields = ("id", "updated_at", "created_at")
    ordering = ("-created_at",)
    list_editable = ("url",)
    list_per_page = 25

    fieldsets = (
        (
            "Node Metadata",
            {
                "fields": (
                    "name",
                    "url",
                    "api_key",
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
