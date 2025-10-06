from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from nodes.models import NodeRegistration, LoadBalanceRule
from chat.models import Node, NodeHeartbeat, SystemLog, ChatRoom, Message
import json
import logging
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


def is_admin(user):
    """Check if user is admin/staff."""
    return user.is_staff


class NodeManager:
    """Utility class for node management operations."""

    @staticmethod
    def create_node(name, url, max_rooms=50, user=None):
        """Create a new node with validation."""
        if Node.objects.filter(Q(name=name) | Q(url=url)).exists():
            raise ValueError("Node with this name or URL already exists")

        node = Node.objects.create(
            name=name, url=url, max_rooms=max_rooms, status="offline"
        )

        SystemLog.objects.create(
            level="info",
            category="node",
            message=f"Node created: {node.name}",
            user=user,
            node=node,
        )
        return node

    @staticmethod
    def delete_node(node_id, user=None):
        """Delete a node with validation."""
        node = Node.objects.get(id=node_id)

        if node.chat_rooms.filter(is_active=True).exists():
            raise ValueError("Cannot delete node with active rooms")

        node_name = node.name
        node.delete()

        SystemLog.objects.create(
            level="warning",
            category="node",
            message=f"Node deleted: {node_name}",
            user=user,
        )

    @staticmethod
    def process_heartbeat(node_id, data):
        """Process node heartbeat data."""
        node = Node.objects.get(id=node_id)

        # Create heartbeat record
        NodeHeartbeat.objects.create(
            node=node,
            load=data.get("load", 0),
            active_connections=data.get("active_connections", 0),
            memory_usage=data.get("memory_usage", 0),
            cpu_usage=data.get("cpu_usage", 0),
        )

        # Update node status
        node.last_heartbeat = timezone.now()
        node.status = "online"
        node.load = data.get("load", 0)
        node.current_rooms = data.get("active_rooms", 0)
        node.save()

        SystemLog.objects.create(
            level="info",
            category="node",
            message=f"Heartbeat received from {node.name}",
            node=node,
            details=data,
        )


@login_required
@user_passes_test(is_admin)
def nodes_dashboard(request):
    """Admin dashboard for node management."""
    nodes = (
        Node.objects.all()
        .annotate(room_count=Count("chat_rooms"), heartbeat_count=Count("heartbeats"))
        .order_by("-created_at")
    )

    context = {
        "nodes": nodes,
        "pending_registrations": NodeRegistration.objects.filter(status="pending"),
        "load_rules": LoadBalanceRule.objects.filter(is_active=True),
        "total_rooms": ChatRoom.objects.count(),
        "total_messages": Message.objects.count(),
        "total_users": User.objects.count(),
    }
    return render(request, "nodes/dashboard.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def node_heartbeat(request, node_id):
    """Receive heartbeat from nodes."""
    try:
        data = json.loads(request.body)
        NodeManager.process_heartbeat(node_id, data)
        return JsonResponse({"status": "success"})
    except Node.DoesNotExist:
        logger.error(f"Node {node_id} not found")
        return JsonResponse({"error": "Node not found"}, status=404)
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_node(request):
    """Register a new node (public API)."""
    try:
        data = json.loads(request.body)

        registration = NodeRegistration.objects.create(
            node_name=data["node_name"],
            node_url=data["node_url"],
            admin_email=data["admin_email"],
            description=data.get("description", ""),
            max_rooms_capacity=data.get("max_rooms_capacity", 50),
        )

        SystemLog.objects.create(
            level="info",
            category="node",
            message=f'Node registration: {data["node_name"]}',
            details=data,
        )

        return JsonResponse(
            {"status": "success", "registration_id": str(registration.id)}
        )
    except KeyError as e:
        return JsonResponse({"error": f"Missing field: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def create_node(request):
    """Create a new node directly (admin only)."""
    try:
        name = request.POST.get("name")
        url = request.POST.get("url")
        max_rooms = int(request.POST.get("max_rooms", 50))

        if not name or not url:
            return JsonResponse({"error": "Name and URL are required"}, status=400)

        node = NodeManager.create_node(name, url, max_rooms, request.user)
        return JsonResponse({"status": "success", "node_id": str(node.id)})

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create node error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def approve_node(request, registration_id):
    """Approve a node registration."""
    try:
        registration = get_object_or_404(NodeRegistration, id=registration_id)

        node = NodeManager.create_node(
            registration.node_name,
            registration.node_url,
            registration.max_rooms_capacity,
            request.user,
        )

        registration.status = "approved"
        registration.approved_by = request.user
        registration.approved_at = timezone.now()
        registration.save()

        SystemLog.objects.create(
            level="info",
            category="node",
            message=f"Node approved: {node.name}",
            user=request.user,
            node=node,
        )

        return JsonResponse({"status": "success", "node_id": str(node.id)})

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Approve node error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def reject_node(request, registration_id):
    """Reject a node registration."""
    try:
        registration = get_object_or_404(NodeRegistration, id=registration_id)
        registration.status = "rejected"
        registration.save()

        SystemLog.objects.create(
            level="warning",
            category="node",
            message=f"Node registration rejected: {registration.node_name}",
            user=request.user,
        )

        return JsonResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Reject node error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["DELETE"])
def delete_node(request, node_id):
    """Delete a node."""
    try:
        NodeManager.delete_node(node_id, request.user)
        return JsonResponse({"status": "success"})
    except Node.DoesNotExist:
        return JsonResponse({"error": "Node not found"}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Delete node error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@user_passes_test(is_admin)
def system_logs(request):
    """View system logs."""
    logs = SystemLog.objects.select_related("user", "node").order_by("-timestamp")[:100]
    return render(request, "nodes/system_logs.html", {"logs": logs})


@login_required
def node_status_api(request):
    """API endpoint for node status."""
    nodes = Node.objects.annotate(room_count=Count("chat_rooms")).values(
        "id", "name", "status", "load", "room_count", "last_heartbeat"
    )

    nodes_list = list(nodes)
    for node in nodes_list:
        if node["last_heartbeat"]:
            node["last_heartbeat"] = node["last_heartbeat"].isoformat()

    return JsonResponse({"nodes": nodes_list})


@login_required
@user_passes_test(is_admin)
def node_detail(request, node_id):
    """Get detailed node information."""
    try:
        node = Node.objects.annotate(
            room_count=Count("chat_rooms"), heartbeat_count=Count("heartbeats")
        ).get(id=node_id)

        recent_heartbeats = node.heartbeats.order_by("-timestamp")[:10]

        data = {
            "id": str(node.id),
            "name": node.name,
            "url": node.url,
            "status": node.status,
            "load": node.load,
            "max_rooms": node.max_rooms,
            "current_rooms": node.current_rooms,
            "room_count": node.room_count,
            "heartbeat_count": node.heartbeat_count,
            "last_heartbeat": node.last_heartbeat.isoformat()
            if node.last_heartbeat
            else None,
            "created_at": node.created_at.isoformat(),
            "recent_heartbeats": [
                {
                    "timestamp": hb.timestamp.isoformat(),
                    "load": hb.load,
                    "active_connections": hb.active_connections,
                    "memory_usage": hb.memory_usage,
                    "cpu_usage": hb.cpu_usage,
                }
                for hb in recent_heartbeats
            ],
        }

        return JsonResponse({"status": "success", "node": data})
    except Node.DoesNotExist:
        return JsonResponse({"error": "Node not found"}, status=404)
