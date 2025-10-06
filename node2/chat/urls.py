from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("room/create/", views.create_room_view, name="create_room"),
    path("room/<uuid:room_id>/", views.chat_room_view, name="chat_room"),
    path("room/<uuid:room_id>/send/", views.send_message_view, name="send_message"),
    path("room/<uuid:room_id>/messages/", views.get_room_messages, name="get_messages"),
    path("room/<uuid:room_id>/leave/", views.leave_room_view, name="leave_room"),
    path("room/<uuid:room_id>/delete/", views.delete_room_view, name="delete_room"),
]
