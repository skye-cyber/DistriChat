import time
import threading
import requests
from django.conf import settings
from django.utils import timezone
import logging
from nodes.models import PeerNode

logger = logging.getLogger(__name__)


class NodeRegistrationMiddlewareX:
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
                    logger.warning(f"⚠️ Registration failed. Retrying in 10s...")
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


class NodeHeartbeatMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._last_heartbeat_sent = None
        self._heartbeat_interval = 30  # Send heartbeat max every 30 seconds

    def __call__(self, request):
        # Process request first
        response = self.get_response(request)

        # Send heartbeat after successful request processing
        if response.status_code < 500:  # Only if not server error
            self._send_heartbeat_async()

        return response

    def _should_send_heartbeat(self):
        """Check if we should send heartbeat (rate limiting)"""
        if not self._last_heartbeat_sent:
            return True

        time_since_last = (timezone.now() - self._last_heartbeat_sent).total_seconds()
        return time_since_last >= self._heartbeat_interval

    def _send_heartbeat_async(self):
        """Send heartbeat in background thread"""
        if not self._should_send_heartbeat():
            return

        thread = threading.Thread(target=self._send_heartbeat, daemon=True)
        thread.start()

    def _send_heartbeat(self):
        """Send heartbeat to central server"""
        try:
            logger.info("Sending heartbeat")
            # Get node info
            node = PeerNode.objects.get(name=settings.NODE_NAME)

            # Update local heartbeat timestamp
            node.last_heartbeat = timezone.now()
            node.status = "online"
            node.save(update_fields=["last_heartbeat", "status", "updated_at"])

            # Prepare heartbeat data
            heartbeat_data = {
                "node_id": str(node.id),
                "status": "online",
                "load": node.load,
                "current_rooms": node.current_rooms,
                "available_capacity": node.available_capacity,
                "max_rooms": node.max_rooms,
                "timestamp": timezone.now().isoformat(),
                "origin_node_id": str(node.id),
            }

            # Send to central server
            if hasattr(settings, "CENTRAL_SERVER_URL") and settings.CENTRAL_SERVER_URL:
                response = requests.patch(
                    f"{settings.CENTRAL_SERVER_URL}/nodes/api/heartbeat/{node.id}/",
                    json=heartbeat_data,
                    headers={
                        "X-Node-API-Key": node.api_key,
                        "X-ORIGIN": settings.NODE_NAME,
                        "Content-Type": "application/json",
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    print("\033[32m✅ Heartbeat sent to central server\033[0m")
                    logger.debug("✅ Heartbeat sent to central server")
                    self._last_heartbeat_sent = timezone.now()
                else:
                    logger.warning(
                        f"❌ Heartbeat failed: {response.status_code} - {response.text}"
                    )

        except PeerNode.DoesNotExist:
            logger.error("❌ Node not found for heartbeat")
        except requests.exceptions.ConnectionError:
            logger.warning("🌐 Central server unreachable for heartbeat")
        except requests.exceptions.Timeout:
            logger.warning("⏰ Heartbeat timeout")
        except Exception as e:
            logger.error(f"💥 Heartbeat error: {e}")
