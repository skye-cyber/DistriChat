from django.utils import timezone
from datetime import datetime
import threading
from django.conf import settings
from nodes.models import PeerNode
import logging

logger = logging.getLogger(__name__)

# Thread-local storage for tracking sync origins
_sync_origin_local = threading.local()


def fromiso_timezone_aware(iso_string: str):
    if not isinstance(iso_string, str):
        return iso_string
    try:
        dt_object = datetime.fromisoformat(iso_string)
        if not timezone.is_aware(dt_object):
            dt_object = timezone.make_aware(dt_object)
        return dt_object
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse datetime from ISO string: {iso_string} - {e}")
        return None


class TriggerOriginHandler:
    def __init__(self):
        # self.set_defaults(False)
        pass

    def set_defaults(self, db=True):
        """Set default values for sync origin"""
        try:
            node_name = getattr(settings, "NODE_NAME", None)
            _sync_origin_local.node_name = node_name

            if db and node_name:
                peer_node = PeerNode.objects.filter(name=node_name).first()
                _sync_origin_local.node_id = peer_node.id if peer_node else None
            else:
                _sync_origin_local.node_id = None

        except Exception as e:
            logger.warning(f"Failed to set default sync origin: {e}")
            _sync_origin_local.node_id = None
            _sync_origin_local.node_name = getattr(settings, "NODE_NAME", None)

    def set_sync_origin(self, node_id, node_name):
        """Set the originating node for the current sync operation"""
        _sync_origin_local.node_id = node_id
        _sync_origin_local.node_name = node_name
        logger.debug(f"Set sync origin: ID={node_id}, Name={node_name}")

    def get_sync_origin(self):
        """Get the originating node for the current sync operation"""
        node_id = getattr(_sync_origin_local, "node_id", None)
        node_name = getattr(_sync_origin_local, "node_name", None)
        logger.debug(f"Get sync origin: ID={node_id}, Name={node_name}")
        return node_id, node_name

    def clear_sync_origin(self):
        """Clear the sync origin after operation and set to defaults"""
        logger.debug("Clearing sync origin and setting defaults")
        self.set_defaults()

    def ensure_origin_initialized(self):
        """Ensure the origin is properly initialized"""
        node_id, node_name = self.get_sync_origin()
        if node_id is None or node_name is None:
            logger.warning("Sync origin not properly initialized, setting defaults")
            self.set_defaults(db=True)  # Force DB lookup


# Global handler instance
handler = TriggerOriginHandler()
