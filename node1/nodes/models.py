from django.db import models
from django.conf import settings


class NodeMetadata(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=100, default=settings.NODE_NAME, unique=True)
    url = models.URLField(
        max_length=200, default=settings.NODE_URL, help_text="Node's base URL"
    )
    api_key = models.CharField(max_length=64, unique=True)
    room_count = models.IntegerField(
        default=0, help_text="Current number of active rooms"
    )
    load = models.FloatField(default=0.0, help_text="Current load percentage (0-100)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}"

    @property
    def get_api_key(self):
        return self.api_key
