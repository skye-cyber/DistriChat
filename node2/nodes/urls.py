from django.urls import path
from . import views

app_name = "nodes"

urlpatterns = [
    # Dashboard and views
    path("dashboard/", views.nodes_dashboard, name="dashboard"),
    path("logs/", views.system_logs, name="system_logs"),
]
