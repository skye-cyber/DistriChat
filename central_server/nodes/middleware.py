import requests
from django.conf import settings
import logging
from django.http import JsonResponse
import threading
from typing import Any
import time

logger = logging.getLogger(__name__)


class Util:
    @staticmethod
    def schema(data: Any, model: str) -> dict:
        return {
            "action": "create",
            "data": data,
            "model": model,
            "source_node": {
                "name": getattr(settings, "NODE_NAME", "CENTRAL_SERVER"),
                "url": getattr(settings, "NODE_URL", ""),
            },
        }


dict_schema = Util.schema


# API key authentication middleware
class NodeAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/nodes/sync/"):
            api_key = request.headers.get("X-Node-API-Key")
            if not self.validate_api_key(api_key):
                return JsonResponse({"error": "Invalid API key"}, status=401)

        return self.get_response(request)


class NodeRegistrationMiddleware:
    _registering = False  # currently registering?
    _registered = False  # registration successful?
    _lock = threading.Lock()  # ensures thread-safety

    def __init__(self, get_response):
        self.get_response = get_response

        # Run registration in a background thread on startup
        if getattr(settings, "IS_NODE", False):
            threading.Thread(target=self._ensure_registration, daemon=True).start()

    def __call__(self, request):
        return self.get_response(request)

    def _ensure_registration(self):
        """Ensure registration happens once, with retry on failure."""
        while not NodeRegistrationMiddleware._registered:
            with self._lock:
                if NodeRegistrationMiddleware._registering:
                    return  # Another thread is handling registration

                NodeRegistrationMiddleware._registering = True

            try:
                success = self.register_with_central_server()
                if success:
                    NodeRegistrationMiddleware._registered = True
                    logger.info(
                        f"✅ Node {settings.NODE_NAME} registered successfully."
                    )
                    break
                else:
                    logger.warning("⚠️ Registration failed. Retrying in 10s...")
            except Exception as e:
                logger.error(f"🔥 Node registration exception: {e}")

            finally:
                NodeRegistrationMiddleware._registering = False

            # Retry after delay
            time.sleep(10)

    def register_with_central_server(self):
        """Attempt to register this node with the central server."""
        from .models import NodeMetadata

        # Skip if already registered locally
        if NodeMetadata.objects.filter(
            url=settings.NODE_URL, name=settings.NODE_NAME
        ).exists():
            logger.info(f"Node {settings.NODE_NAME} already registered locally.")
            return True

        registration_data = {
            "node_name": settings.NODE_NAME,
            "node_url": settings.NODE_URL,
            "admin_email": "admin@chatserver.local",
            "description": f"Local development node - {settings.NODE_NAME}",
            "max_rooms_capacity": settings.MAX_ROOMS,
            "api_key": settings.NODE_API_KEY,
        }

        try:
            response = requests.post(
                f"{settings.CENTRAL_SERVER_URL}/nodes/register/",
                json=registration_data,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(
                    f"✅ Registered node {settings.NODE_NAME} with central server."
                )
                return True
            else:
                logger.error(f"❌ Registration failed: {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Network error during registration: {e}")
            return False


class NodePeerSyncMiddleware:
    """Middleware for node peer synchronization in a distributed system."""

    # Class-level cache to track sync status
    _sync_initiated = False
    _sync_lock = threading.Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize peer sync only once per process
        if not self._sync_initiated and not getattr(settings, "IS_NODE", False):
            with self._sync_lock:
                if not self._sync_initiated:  # Double-check locking
                    self._sync_initiated = True
                    # Run sync in background thread to avoid blocking request
                    threading.Thread(
                        target=self.run_peer_sync, daemon=True, name="NodePeerSync-Init"
                    ).start()

        response = self.get_response(request)
        return response

    def run_peer_sync(self):
        """Run peer synchronization with central server - all nodes in one call."""
        try:
            from .models import Node

            nodes = Node.objects.all()
            if not nodes:
                logger.warning("No nodes found for peer synchronization")
                return

            # Prepare all nodes data for single API call
            nodes_data = dict_schema([node.to_dict for node in nodes], "nodes")

            for node in nodes_data["data"]:
                target_url = f"{node['url']}/nodes/api/peer/init/"
                SyncHandler(nodes_data, target_url, "node").sync()

        except Exception as e:
            raise
            logger.error(f"Peer sync initialization failed: {e}")


class NodeUserAutoSyncMiddleware:
    """Middleware for node peer synchronization in a distributed system."""

    # Class-level cache to track sync status
    _sync_initiated = False
    _sync_lock = threading.Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize peer sync only once per process
        if not self._sync_initiated and not getattr(settings, "IS_NODE", False):
            with self._sync_lock:
                if not self._sync_initiated:  # Double-check locking
                    self._sync_initiated = True
                    # Run sync in background thread to avoid blocking request
                    threading.Thread(
                        target=self.run_peer_sync, daemon=True, name="UserSync-Init"
                    ).start()

        response = self.get_response(request)
        return response

    def run_peer_sync(self):
        """Run peer synchronization with central server - all nodes in one call."""
        try:
            from django.contrib.auth import get_user_model
            from nodes.models import Node

            User = get_user_model()

            users_data = [user.to_sync_dict for user in User.objects.all()]

            if not users_data:
                logger.warning("No nodes found for peer synchronization")
                return

            # Prepare all nodes data for single API call
            user_sync_data = dict_schema(users_data, "user")

            for url in Node.objects.values_list("url"):
                target_url = f"{url[0]}/nodes/api/sync/receive/"
                SyncHandler(user_sync_data, target_url, "user").sync()

        except Exception as e:
            logger.error(f"Peer sync initialization failed: {e}")


class NodeSessionAutoSyncMiddleware:
    """Middleware for node peer synchronization in a distributed system."""

    # Class-level cache to track sync status
    _sync_initiated = False
    _sync_lock = threading.Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize peer sync only once per process
        if not self._sync_initiated and not getattr(settings, "IS_NODE", False):
            with self._sync_lock:
                if not self._sync_initiated:  # Double-check locking
                    self._sync_initiated = True
                    # Run sync in background thread to avoid blocking request
                    threading.Thread(
                        target=self.run_peer_sync,
                        daemon=True,
                        name="UserSessionSync-Init",
                    ).start()

        response = self.get_response(request)
        return response

    def run_peer_sync(self):
        """Run peer synchronization with central server - all nodes in one call."""
        try:
            from nodes.models import Node
            from users.models import UserSession

            users_data = [session.to_dict for session in UserSession.objects.all()]

            if not users_data:
                logger.warning("No nodes found for peer synchronization")
                return

            # Prepare all nodes data for single API call
            user_sync_data = dict_schema(users_data, "session", "session")

            for url in Node.objects.values_list("url"):
                target_url = f"{url[0]}/nodes/api/sync/receive/"
                SyncHandler(user_sync_data, target_url, "session").sync()

        except Exception as e:
            logger.error(f"Peer sync initialization failed: {e}")


class SyncHandler:
    def __init__(self, data, url, target, auth_key=None):
        self.target = target
        self.data = data
        self.url = url
        self.auth_key = auth_key

    def sync(self):
        """Sync all nodes with the central server in a single API call."""
        try:
            logger.info(f"Syncing {self.target} to: {self.url}")

            response = requests.post(
                self.url,
                json=self.data,
                headers={
                    "X-ORIGIN": "CENTRAL_SERVER",
                    "X-AUTH": "BYPASS_AUTH",
                    "X-Origin-Node-Api-Key": self.auth_key,
                    "Content-Type": "application/json",
                },
                timeout=10,  # Increased timeout for bulk operation
            )

            if response.status_code == 200:
                print(
                    (
                        f"\033[1;32m{self.target.title()}\033[0;32m sync successful\033[0m"
                    )
                )
                logger.info(f"{self.target.title()} sync successful")
                # self._handle_bulk_sync_response(response, self.data)
                return True
            else:
                logger.error(
                    f"{self.target.title()} sync failed: HTTP {response.status_code} - {response.text if len(response.text) < 200 else ""}"
                )

        except requests.exceptions.Timeout:
            logger.error(f"{self.target.title()} sync timeout for {self.url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed for target node server: {self.url}")
        except Exception as e:
            logger.error(f"Unexpected error during  {self.target} sync: {e}")
