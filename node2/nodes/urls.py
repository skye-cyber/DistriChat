from django.urls import path
from . import views, views_sync

app_name = "nodes"

urlpatterns = [
    # Dashboard and views
    path("dashboard/", views.nodes_dashboard, name="dashboard"),
    path("logs/", views.system_logs, name="system_logs"),
    # Save node metadata
    path("api/meta/set/", views.save_meta, name="save_meta_peers"),
    path("api/peer/init/", views.create_peers, name="set_peer_nodes"),
    path("api/peer/delete/", views.delete_peer, name="delete_peer_node"),
    path(
        "api/sync/receive/",
        views_sync.SyncViaCentralReceiverAPI.as_view(),
        name="sync_from_central",
    ),
]
