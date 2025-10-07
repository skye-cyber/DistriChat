from django.contrib import admin
from .models import (
    Node,
    ChatRoom,
    RoomMembership,
    Message,
    MessageReadStatus,
    SystemLog,
)


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "url",
        "status",
        "load",
        "current_rooms",
        "max_rooms",
        "last_heartbeat",
    )
    list_filter = ("status", "created_at")
    search_fields = ("name", "url")
    readonly_fields = ("last_heartbeat", "created_at", "updated_at")


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "room_type",
        "node",
        "created_by",
        "member_count",
        "created_at",
    )
    list_filter = ("room_type", "node", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "role", "joined_at")
    list_filter = ("role", "joined_at")
    search_fields = ("user__username", "room__name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "room", "content_preview", "message_type", "created_at")
    list_filter = ("message_type", "created_at", "is_deleted")
    search_fields = ("content", "sender__username", "room__name")
    readonly_fields = ("created_at", "updated_at")

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content"


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "read_at")
    list_filter = ("read_at",)
    search_fields = ("user__username", "message__content")


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("level", "category", "message_preview", "user", "node", "timestamp")
    list_filter = ("level", "category", "timestamp")
    search_fields = ("message",)
    readonly_fields = ("timestamp",)

    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message

    message_preview.short_description = "Message"
