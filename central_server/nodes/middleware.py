import requests
from django.conf import settings
from django.utils import timezone
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class NodeMiddleware:
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
            from .models import Node

            if Node.objects.filter(url=settings.NODE_URL).exists():
                return

            # Register with central server
            registration_data = {
                "node_name": settings.NODE_NAME,
                "node_url": settings.NODE_URL,
                "admin_email": "admin@chatserver.local",
                "description": f"Local development node - {settings.NODE_NAME}",
                "max_rooms_capacity": settings.MAX_ROOMS,
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
                if registration_id:
                    self.auto_approve_node(registration_id)
            else:
                logger.error(f"Failed to register node: {response.text}")

        except Exception as e:
            logger.error(f"Node registration error: {e}")

    def auto_approve_node(self, registration_id):
        """Auto-approve this node for development."""
        try:
            # In production, this would require admin approval
            # For development, we auto-approve
            from .models import Node

            # Create node directly since we're in development
            node = Node.objects.create(
                name=settings.NODE_NAME,
                url=settings.NODE_URL,
                max_rooms=settings.MAX_ROOMS,
                status="online",
            )
            logger.info(f"Node {node.name} auto-approved for development")

        except Exception as e:
            logger.error(f"Auto-approval error: {e}")


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
