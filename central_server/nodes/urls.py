from django.urls import path
from . import views, views_sync

app_name = "nodes"

urlpatterns = [
    # Dashboard and views
    path("dashboard/", views.nodes_dashboard, name="dashboard"),
    path("logs/", views.system_logs, name="system_logs"),
    # Node CRUD operations
    path("create/", views.create_node, name="create_node"),
    path("delete/<uuid:node_id>/", views.delete_node, name="delete_node"),
    path("detail/<uuid:node_id>/", views.node_detail, name="node_detail"),
    # Registration management
    path("register/", views.register_node, name="register_node"),
    path("approve/<uuid:registration_id>/", views.approve_node, name="approve_node"),
    path("reject/<uuid:registration_id>/", views.reject_node, name="reject_node"),
    # API endpoints
    path("heartbeat/<uuid:node_id>/", views.node_heartbeat, name="node_heartbeat"),
    path("status/", views.node_status_api, name="node_status"),
    # Sync API endpoints
    path(
        "api/sync/receive/", views_sync.SyncReceiverAPI.as_view(), name="sync_receive"
    ),
    # Manual sync endpoints (for backup)
    path(
        "api/sync/trigger-full/",
        views_sync.NodeSyncAPI.as_view(),
        name="sync_trigger_full",
    ),
    path("api/sync/status/", views_sync.sync_status, name="sync_status"),
    path("api/node/status/", views_sync.SyncStatsAPI.as_view(), name="node_status"),
]
