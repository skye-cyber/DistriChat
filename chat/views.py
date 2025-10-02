from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib import messages
from .models import ChatRoom, RoomMembership, Message, Node, MessageReadStatus
from users.models import UserActivity
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """Main dashboard showing chat rooms and nodes."""
    # Get all active public rooms and rooms user is member of
    user_rooms = (
        ChatRoom.objects.filter(Q(room_type="public") | Q(members=request.user))
        .distinct()
        .select_related("node", "created_by")
        .prefetch_related("members")
    )

    # Get online nodes
    nodes = (
        Node.objects.filter(status="online")
        .annotate(room_count=Count("chat_rooms"))
        .order_by("load")
    )

    # User stats
    user_room_count = request.user.chat_rooms.count()
    user_message_count = request.user.sent_messages.count()

    context = {
        "chat_rooms": user_rooms,
        "nodes": nodes,
        "user_room_count": user_room_count,
        "user_message_count": user_message_count,
    }
    return render(request, "dashboard.html", context)


@login_required
@csrf_protect
def create_room_view(request):
    """Create a new chat room."""
    if request.method == "POST":
        room_name = request.POST.get("room_name")
        room_description = request.POST.get("room_description", "")

        if not room_name:
            messages.error(request, "Room name is required.")
            return redirect("chat:dashboard")

        # Find the best node (least loaded)
        best_node = Node.objects.filter(status="online").order_by("load").first()
        if not best_node:
            messages.error(request, "No available nodes. Please try again later.")
            return redirect("chat:dashboard")

        # Create the room
        room = ChatRoom.objects.create(
            name=room_name,
            description=room_description,
            node=best_node,
            created_by=request.user,
        )

        # Add creator as owner
        RoomMembership.objects.create(room=room, user=request.user, role="owner")

        # Update node room count
        best_node.current_rooms += 1
        best_node.update_load()

        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type="room_created",
            description=f'Created room "{room_name}" on node {best_node.name}',
            ip_address=get_client_ip(request),
        )

        messages.success(request, f'Room "{room_name}" created successfully!')
        return redirect("chat_room", room_id=room.id)

    return redirect("chat:dashboard")


@login_required
def chat_room_view(request, room_id):
    """Chat room view with messages."""
    room = get_object_or_404(
        ChatRoom.objects.select_related("node").prefetch_related("members"), id=room_id
    )

    # Check if user is member (for private rooms)
    if (
        room.room_type == "private"
        and not room.members.filter(id=request.user.id).exists()
    ):
        return HttpResponseForbidden("You don't have access to this room.")

    # Get messages with sender info
    messages = (
        room.messages.select_related("sender")
        .filter(is_deleted=False)
        .order_by("created_at")[:100]
    )  # Last 100 messages

    # Get online members
    online_members = room.members.filter(is_online=True)

    # Add user to room if not already member (for public rooms)
    if not room.members.filter(id=request.user.id).exists():
        RoomMembership.objects.create(room=room, user=request.user)
        request.user.rooms_joined += 1
        request.user.save()

        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type="room_joined",
            description=f'Joined room "{room.name}"',
            ip_address=get_client_ip(request),
        )

    context = {
        "room": room,
        "messages": messages,
        "online_members": online_members,
    }
    return render(request, "chat_room.html", context)


@login_required
@require_http_methods(["POST"])
def send_message_view(request, room_id):
    """API endpoint to send a message."""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user is member
    if not room.members.filter(id=request.user.id).exists():
        return JsonResponse({"error": "Not a member of this room"}, status=403)

    data = json.loads(request.body)
    content = data.get("content", "").strip()

    if not content:
        return JsonResponse({"error": "Message content is required"}, status=400)

    # Create message
    message = Message.objects.create(room=room, sender=request.user, content=content)

    # Update user message count
    request.user.total_messages_sent += 1
    request.user.save()

    # Log activity
    UserActivity.objects.create(
        user=request.user,
        activity_type="message_sent",
        description=f'Sent message in room "{room.name}"',
        ip_address=get_client_ip(request),
        metadata={"room_id": str(room.id), "message_length": len(content)},
    )

    return JsonResponse(
        {
            "success": True,
            "message_id": str(message.id),
            "timestamp": message.created_at.isoformat(),
        }
    )


@login_required
def get_room_messages(request, room_id):
    """Get messages for a room."""
    room = get_object_or_404(ChatRoom, id=room_id)

    if not room.members.filter(id=request.user.id).exists():
        return JsonResponse({"error": "Not a member"}, status=403)

    # Get messages with pagination
    before = request.GET.get("before")
    limit = int(request.GET.get("limit", 50))

    messages_query = (
        room.messages.select_related("sender")
        .filter(is_deleted=False)
        .order_by("-created_at")
    )

    if before:
        try:
            before_date = timezone.datetime.fromisoformat(before)
            messages_query = messages_query.filter(created_at__lt=before_date)
        except ValueError:
            pass

    messages = list(messages_query[:limit])
    messages.reverse()  # Return in chronological order

    messages_data = []
    for msg in messages:
        messages_data.append(
            {
                "id": str(msg.id),
                "sender": {
                    "username": msg.sender.username,
                    "color": msg.sender.color_scheme,
                },
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "type": msg.message_type,
            }
        )

    return JsonResponse({"messages": messages_data, "has_more": len(messages) == limit})


@login_required
def leave_room_view(request, room_id):
    """Leave a chat room."""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Remove user from room
    RoomMembership.objects.filter(room=room, user=request.user).delete()

    # Update node room count if room becomes empty
    if room.members.count() == 0:
        room.node.current_rooms -= 1
        room.node.update_load()

    messages.success(request, f"You have left {room.name}")
    return redirect("chat:dashboard")


@login_required
def delete_room_view(request, room_id):
    """Delete a room (owners only)."""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user is owner
    membership = RoomMembership.objects.filter(room=room, user=request.user).first()
    if not membership or membership.role != "owner":
        return HttpResponseForbidden("Only room owners can delete rooms.")

    # Update node room count
    room.node.current_rooms -= 1
    room.node.update_load()

    room_name = room.name
    room.delete()

    messages.success(request, f'Room "{room_name}" has been deleted.')
    return redirect("chat:dashboard")


def get_client_ip(request):
    """Get client IP address."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
