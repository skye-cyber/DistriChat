from django.contrib import admin
from nodes.models import NodeMetadata


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
