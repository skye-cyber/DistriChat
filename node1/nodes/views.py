from django.db import transaction, IntegrityError
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from chat.models import SystemLog
from nodes.models import NodeMetadata
import logging
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json

User = get_user_model()

logger = logging.getLogger(__name__)
# NodeMetadata.objects.all().delete()


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
        room_count = data.get("room_count")
        load = data.get("load")

        if not all([id, api_key, url, name]):
            return JsonResponse(
                {"status": "error", "error": "Missing required fields"}, status=400
            )

        if url != settings.NODE_URL or name != settings.NODE_NAME:
            logger.error("❌ Could not create node metadata: URL or name mismatch")
            return JsonResponse(
                {"status": "error", "error": "URL or name mismatch"}, status=400
            )

        with transaction.atomic():
            print(name, id, api_key, room_count, load)
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

        return JsonResponse(
            {"status": "success", "action": "create" if created else "update"},
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
