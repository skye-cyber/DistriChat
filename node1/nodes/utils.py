from django.utils import timezone
from datetime import datetime
import threading
from django.conf import settings
from nodes.models import PeerNode

# Thread-local storage for tracking sync origins
_sync_origin_local = threading.local()


def fromiso_timezone_aware(iso_string: str):
    if not isinstance(iso_string, str):
        return iso_string
    dt_object = datetime.fromisoformat(iso_string)
    if not timezone.is_aware(dt_object):
        dt_object = timezone.make_aware(dt_object)

    return dt_object


class TriggerOriginHandler:
    def __init__(self):
        # self.set_defaults()
        pass

    def set_defaults(self):
        try:
            _sync_origin_local.node_name = settings.NODE_NAME
            _sync_origin_local.node_id = (
                PeerNode.objects.filter(name=settings.NODE_NAME).first().id
            )
        except Exception:
            pass

    def set_sync_origin(self, id, name):
        """Set the originating node for the current sync operation"""
        _sync_origin_local.node_id = id
        _sync_origin_local.node_name = name

    def get_sync_origin(self):
        """Get the originating node for the current sync operation"""
        id = getattr(_sync_origin_local, "node_id", None)
        name = getattr(_sync_origin_local, "node_id", None)
        return id, name

    def clear_sync_origin(self):
        """Clear the sync origin after operation
        if hasattr(_sync_origin_local, "node_id"):
            delattr(_sync_origin_local, "node_id")
        if hasattr(_sync_origin_local, "node_name"):
            delattr(_sync_origin_local, "node_name")
        """

        # Set to defaults instead
        self.set_defaults()


handler = TriggerOriginHandler()
