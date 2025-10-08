import logging
from django.http import JsonResponse
from nodes.models import Node

logger = logging.getLogger(__name__)


def authenticate_node(request, node_id):
    """
    Authenticate node using API key
    Returns (node, error_response) tuple
    """
    try:
        # Get API key from header
        api_key = request.headers.get("X-Node-API-Key")
        if not api_key:
            logger.warning(f"❌ Missing API key for node {node_id}")
            return None, JsonResponse(
                {"status": "error", "message": "API key required"}, status=401
            )

        # Find node
        try:
            node = Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            logger.warning(f"❌ Node not found: {node_id}")
            return None, JsonResponse(
                {"status": "error", "message": "Node not found"}, status=404
            )

        # Verify API key
        if node.api_key != api_key:
            logger.warning(f"❌ Invalid API key for node {node.name}")
            return None, JsonResponse(
                {"status": "error", "message": "Invalid API key"}, status=403
            )

        # Check if node is active
        if node.status == "maintenance":
            logger.warning(f"⚠️ Node {node.name} is in maintenance mode")
            # Still allow heartbeat but log it

        logger.debug(f"✅ Node authenticated: {node.name}")
        return node, None

    except Exception as e:
        logger.error(f"💥 Authentication error: {e}")
        return None, JsonResponse(
            {"status": "error", "message": "Authentication failed"}, status=500
        )
