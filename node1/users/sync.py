import json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction, IntegrityError

from users.models import CustomUser
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@csrf_exempt
@require_http_methods(["POST"])
def create_users(request):
    try:
        data = json.loads(request.body)
        users = data["users"]

        for node in users:
            if not node["name"] == settings.NODE_NAME:
                print("CREATING PEER", node["name"])
                create_update_peer(node)
        return JsonResponse({"status": "success", "peers": len(users) - 1}, status=200)
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
            peer, created = CustomUser.objects.get_or_create(
                username=data["name"],
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
