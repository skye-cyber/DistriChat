import time
import threading
import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class NodeMiddlewareX:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If this is a node, register with central server on startup
        if hasattr(settings, "IS_NODE") and settings.IS_NODE:
            self.register_with_central_server()

        response = self.get_response(request)
        return response

    def register_with_central_server(self):
        """Register this node with the central server."""
        try:
            # Check if we're already registered
            from .models import NodeMetadata

            if NodeMetadata.objects.filter(
                url=settings.NODE_URL, name=settings.NODE_NAME
            ).exists():
                return

            # Register with central server
            registration_data = {
                "node_name": settings.NODE_NAME,
                "node_url": settings.NODE_URL,
                "admin_email": "admin@chatserver.local",
                "description": f"Local development node - {settings.NODE_NAME}",
                "max_rooms_capacity": settings.MAX_ROOMS,
                "api_key": settings.NODE_API_KEY,
            }

            response = requests.post(
                f"{settings.CENTRAL_SERVER_URL}/nodes/register/",
                json=registration_data,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f"Node {settings.NODE_NAME} registered with central server")

                # Auto-approve for development
                registration_id = response.json().get("registration_id")
                # if registration_id:
                # self.auto_approve_node(registration_id)
            else:
                logger.error(f"Failed to register node: {response.text}")

        except Exception as e:
            logger.error(f"Node registration error: {e}")


class NodeMiddleware:
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
        while not NodeMiddleware._registered:
            with self._lock:
                if NodeMiddleware._registering:
                    return  # Another thread is handling registration

                NodeMiddleware._registering = True

            try:
                success = self.register_with_central_server()
                if success:
                    NodeMiddleware._registered = True
                    logger.info(
                        f"✅ Node {settings.NODE_NAME} registered successfully."
                    )
                    break
                else:
                    logger.warning(f"⚠️ Registration failed. Retrying in 10s...")
            except Exception as e:
                logger.error(f"🔥 Node registration exception: {e}")

            finally:
                NodeMiddleware._registering = False

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
