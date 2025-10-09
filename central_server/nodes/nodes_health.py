import logging
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.cache import cache
from .models import Node
from .utils import authenticate_node

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["PATCH"])
def node_heartbeat_processor(request, node_id):
    """
    Receive and process heartbeat from nodes
    PATCH /nodes/heartbeat/<uuid:node_id>/
    """
    try:
        # Authenticate the node
        node, auth_error = authenticate_node(request, node_id)
        if auth_error:
            return auth_error

        # Parse heartbeat data
        try:
            heartbeat_data = request.json() if hasattr(request, "json") else {}
        except Exception:
            heartbeat_data = {}

        print(f"\033[94m❤️  Heartbeat received from node\033[1;0m {node.name}\033[0m")
        logger.info(f"❤️ Heartbeat received from node {node.name}")

        # Process the heartbeat
        success = process_heartbeat(node, heartbeat_data)

        if success:
            # print(f"✅ \033[1m{node.name}:\033[32m Heartbeat successfully processed\033[0m")
            logger.debug(
                f"✅ \033[1m{node.name}:\033[32m Heartbeat successfully processed\033[0m"
            )
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Heartbeat received",
                    "timestamp": str(timezone.now().isoformat()),
                }
            )
        else:
            print(
                f"❌ \033[1;33m {node.name}:\033[31m Heartbeat processing failed\033[0m"
            )
            logger.error(
                f"❌ \033[1;33m {node.name}:\033[31m Heartbeat processing failed\033[0m"
            )
            return JsonResponse(
                {"status": "error", "message": "Failed to process heartbeat"},
                status=400,
            )

    except Node.DoesNotExist:
        logger.error(f"❌ Node not found for heartbeat: {node_id}")
        return JsonResponse(
            {"status": "error", "message": "Node not found"}, status=404
        )

    except Exception as e:
        logger.error(f"💥 Unexpected error in heartbeat receiver: {e}")
        return JsonResponse(
            {"status": "error", "message": "Internal server error"}, status=500
        )


def process_heartbeat(node, heartbeat_data):
    """Process heartbeat data and update node status"""
    try:
        # Update basic node status
        node.last_heartbeat = timezone.now()
        node.status = heartbeat_data.get("status", "online")

        # Update metrics if provided
        if "load" in heartbeat_data:
            node.load = float(heartbeat_data["load"])

        if "current_rooms" in heartbeat_data:
            node.current_rooms = int(heartbeat_data["current_rooms"])

        if "max_rooms" in heartbeat_data:
            node.max_rooms = int(heartbeat_data["max_rooms"])

        # Store system metrics in cache for quick access
        system_metrics = heartbeat_data.get("system_metrics", {})
        if system_metrics:
            cache_key = f"node_metrics_{node.id}"
            cache.set(
                cache_key,
                {**system_metrics, "last_updated": str(timezone.now().isoformat())},
                timeout=120,
            )  # Cache for 2 minutes

        # Update node in database
        node.save(
            update_fields=[
                "last_heartbeat",
                "status",
                "load",
                "current_rooms",
                "max_rooms",
                "updated_at",
            ]
        )

        logger.debug(
            f"📊 Node {node.name} updated - Load: {node.load}%, Rooms: {node.current_rooms}/{node.max_rooms}"
        )

        # Trigger any post-heartbeat processing
        post_heartbeat_processing(node, heartbeat_data)

        return True

    except Exception as e:
        raise
        logger.error(f"❌ Error processing heartbeat for node {node.name}: {e}")
        return False


def post_heartbeat_processing(node, heartbeat_data):
    """Perform additional processing after heartbeat"""
    try:
        # Update node health score
        update_node_health_score(node, heartbeat_data)

        # Check if node needs maintenance
        check_node_health(node, heartbeat_data)

        # Log heartbeat for analytics
        log_heartbeat_analytics(node, heartbeat_data)

    except Exception as e:
        logger.warning(f"⚠️ Post-heartbeat processing failed: {e}")


def update_node_health_score(node, heartbeat_data):
    """Calculate and update node health score"""
    try:
        system_metrics = heartbeat_data.get("system_metrics", {})

        # Simple health scoring based on metrics
        health_score = 100  # Start with perfect score

        # Deduct points based on system metrics
        cpu_usage = system_metrics.get("cpu_usage", 0)
        if cpu_usage > 90:
            health_score -= 30
        elif cpu_usage > 80:
            health_score -= 15
        elif cpu_usage > 70:
            health_score -= 5

        memory_usage = system_metrics.get("memory_usage", 0)
        if memory_usage > 90:
            health_score -= 20
        elif memory_usage > 80:
            health_score -= 10

        load = heartbeat_data.get("load", 0)
        if load > 90:
            health_score -= 20
        elif load > 80:
            health_score -= 10

        # Ensure score is within bounds
        health_score = max(0, min(100, health_score))

        # Store in cache
        cache_key = f"node_health_{node.id}"
        cache.set(
            cache_key,
            {
                "health_score": health_score,
                "last_calculated": str(timezone.now().isoformat()),
            },
            timeout=300,
        )  # 5 minutes

    except Exception as e:
        logger.warning(f"⚠️ Health score calculation failed: {e}")


def check_node_health(node, heartbeat_data):
    """Check if node needs maintenance or intervention"""
    try:
        system_metrics = heartbeat_data.get("system_metrics", {})

        warnings = []

        # Check CPU usage
        if system_metrics.get("cpu_usage", 0) > 90:
            warnings.append("High CPU usage")

        # Check memory usage
        if system_metrics.get("memory_usage", 0) > 90:
            warnings.append("High memory usage")

        # Check disk space
        if system_metrics.get("disk_usage", 0) > 90:
            warnings.append("Low disk space")

        # Check node load
        if heartbeat_data.get("load", 0) > 95:
            warnings.append("Node at capacity")

        # Log warnings if any
        if warnings:
            logger.warning(f"⚠️ Node {node.name} health warnings: {', '.join(warnings)}")

            # Could trigger alerts or notifications here
            # send_node_health_alert(node, warnings)

    except Exception as e:
        logger.warning(f"⚠️ Health check failed: {e}")


def log_heartbeat_analytics(node, heartbeat_data):
    """Log heartbeat for analytics and monitoring"""
    try:
        analytics_data = {
            "node_id": str(node.id),
            "node_name": node.name,
            "timestamp": str(timezone.now().isoformat()),
            "load": heartbeat_data.get("load", 0),
            "current_rooms": heartbeat_data.get("current_rooms", 0),
            "status": heartbeat_data.get("status", "online"),
            "system_metrics": heartbeat_data.get("system_metrics", {}),
        }

        # Store in cache for recent analytics
        cache_key = (
            f"heartbeat_analytics_{node.id}_{timezone.now().strftime('%Y%m%d_%H%M')}"
        )
        cache.set(cache_key, analytics_data, timeout=3600)  # 1 hour

        logger.debug(f"📈 Analytics logged for node {node.name}")

    except Exception as e:
        logger.warning(f"⚠️ Analytics logging failed: {e}")
