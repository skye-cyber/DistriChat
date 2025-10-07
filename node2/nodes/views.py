from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test

# from django.http import JsonResponse
from chat.models import SystemLog
import logging
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

logger = logging.getLogger(__name__)


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
