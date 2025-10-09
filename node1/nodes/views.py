from django.db import transaction, IntegrityError
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from chat.models import SystemLog, Message, ChatRoom
from nodes.models import NodeMetadata, PeerNode
import logging
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json

User = get_user_model()

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def save_meta(request):
    try:
        data = json.loads(request.body)
        id = data.get("id")
        api_key = data.get("api_key")
        url = data.get("url")
        name = data.get("name")
        room_count = data.get("current_rooms")
        load = data.get("load")

        if not all([id, api_key, url, name]):
            return JsonResponse(
                {"status": "error", "error": "Missing required fields"}, status=400
            )

        if url == settings.NODE_URL or name == settings.NODE_NAME:
            with transaction.atomic():
                meta, created = NodeMetadata.objects.get_or_create(
                    name=name,
                    defaults={
                        "id": id,
                        "api_key": api_key,
                        "room_count": room_count or 0,
                        "load": load or 0.0,
                    },
                )

                if not created:
                    meta.id = id
                    meta.api_key = api_key
                    meta.room_count = room_count or meta.room_count
                    meta.load = load or meta.load
                    meta.updated_at = timezone.now()
                    meta.save()

        status = create_update_peer(data)
        if status:
            return JsonResponse(
                {"status": "success", "action": "create" if created else "update"},
                status=200,
            )
        return JsonResponse(
            {"status": "fail", "action": "create" if created else "update"},
            status=200,
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "error": "Invalid JSON data"}, status=400
        )
    except IntegrityError as e:
        logger.error(f"IntegrityError: {e}")
        return JsonResponse(
            {"status": "error", "error": "Integrity constraint failed"}, status=400
        )
    except Exception as e:
        logger.exception("Unexpected error in save_meta")
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_peers(request):
    try:
        data = json.loads(request.body)
        nodes = data["data"]
        for node in nodes:
            if not node["name"] == settings.NODE_NAME:
                # print("CREATING PEER", node["name"])
                create_update_peer(node)
        return JsonResponse({"status": "success", "peers": len(nodes) - 1}, status=200)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "error": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        raise
        logger.exception("Unexpected error in create peers")
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


def create_update_peer(data):
    try:
        with transaction.atomic():
            peer, created = PeerNode.objects.get_or_create(
                name=data["name"],
                defaults={
                    "id": data["id"],
                    "url": data["url"],
                    "api_key": data["api_key"],
                    "current_rooms": data["current_rooms"] or 0,
                    "max_rooms": data["max_rooms"] or 50,
                    "load": data["load"] or 0.0,
                    "status": data["status"] or "offline",
                    "last_heartbeat": data["last_heartbeat"],
                    "last_sync": data["last_sync"],
                },
            )

            if not created:
                peer.id = data["id"]
                peer.api_key = data["api_key"]
                peer.current_rooms = data["current_rooms"] or 0
                peer.max_rooms = data["max_rooms"] or 50
                peer.load = data["load"] or 0.0
                peer.status = data["status"] or "offline"
                peer.last_heartbeat = data["last_heartbeat"]
                peer.last_sync = data["last_sync"]
                peer.url = data["url"]
                peer.save()

            return peer

    except json.JSONDecodeError:
        logger.error("Invalid JSON data")
    except IntegrityError as e:
        logger.error(f"IntegrityError: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error in save_meta: {e}")
        return False


@csrf_exempt
def delete_peer(request):
    try:
        data = json.loads(request.body)

        with transaction.atomic():
            peer = PeerNode.objects.filter(id=data["id"], api_key=data["api_key"])
            if not peer.exists():
                return JsonResponse(
                    {"status": "error", "error": "PeerNode not found"}, status=404
                )
            peer.first().delete()

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "error": "Invalid JSON data"}, status=400
        )
    except IntegrityError as e:
        logger.error(f"IntegrityError: {e}")
        return JsonResponse(
            {"status": "error", "error": "Integrity constraint failed"}, status=400
        )
    except Exception as e:
        logger.exception("Unexpected error in save_meta")
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


@csrf_exempt
def is_admin(user):
    """Check if user is admin/staff."""
    return user.is_staff


@login_required
@user_passes_test(is_admin)
def nodes_dashboard(request):
    """Admin dashboard for node management."""
    url = f"{settings.CENTRAL_SERVER_URL}/nodes/dashboard/"
    return redirect(to=url, permanent=True)


@login_required
@user_passes_test(is_admin)
def system_logs(request):
    """View system logs."""
    logs = SystemLog.objects.select_related("user", "node").order_by("-timestamp")[:100]
    return render(request, "nodes/system_logs.html", {"logs": logs})
