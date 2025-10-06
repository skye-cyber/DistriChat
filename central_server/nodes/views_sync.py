# nodes/views_sync.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import hashlib
import json
from nodes.models import Node
from django.utils import timezone


@method_decorator(csrf_exempt, name="dispatch")
class NodeSyncAPI(View):
    def post(self, request, node_id):
        """Receive sync data from nodes"""
        try:
            data = json.loads(request.body)
            sync_type = data.get("sync_type", "incremental")

            # Validate node authentication
            if not self.authenticate_node(request, node_id):
                return JsonResponse({"error": "Authentication failed"}, status=401)

            # Process sync data
            result = self.process_sync_data(node_id, data)

            return JsonResponse(
                {
                    "status": "success",
                    "sync_id": str(result["sync_id"]),
                    "processed_messages": result["processed_count"],
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request, node_id):
        """Provide sync data to requesting nodes"""
        since = request.GET.get("since")
        room_id = request.GET.get("room_id")

        sync_data = self.get_sync_data(node_id, since, room_id)

        return JsonResponse(
            {"sync_data": sync_data, "server_timestamp": timezone.now().isoformat()}
        )

    def authenticate_node(self, request, node_id):
        """Authenticate node using API keys or tokens"""
        api_key = request.headers.get("X-Node-API-Key")
        node = Node.objects.filter(id=node_id, api_key=api_key).first()
        return node is not None

    def process_sync_data(self, node_id, data):
        """Process incoming sync data from nodes"""
        # Implementation for processing sync data
        pass
