from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserSession, UserActivity


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_online", "last_seen", "is_staff")
    list_filter = ("is_online", "is_staff", "is_superuser", "created_at")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("last_seen", "created_at", "updated_at")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Chat Features",
            {
                "fields": (
                    "is_online",
                    "last_seen",
                    "avatar",
                    "bio",
                    "color_scheme",
                    "notification_enabled",
                    "sound_enabled",
                    "total_messages_sent",
                    "rooms_joined",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "last_activity", "created_at")
    list_filter = ("last_activity", "created_at")
    search_fields = ("user__username", "user__email", "ip_address")
    readonly_fields = ("created_at", "last_activity")


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "ip_address", "created_at")
    list_filter = ("activity_type", "created_at")
    search_fields = ("user__username", "user__email", "ip_address")
    readonly_fields = ("created_at",)
