from django.urls import path

from .views import RoomDetailView, RoomListCreateView

app_name = "rooms"

urlpatterns = [
    path("rooms/", RoomListCreateView.as_view(), name="room-list"),
    path("rooms/<int:pk>/", RoomDetailView.as_view(), name="room-detail"),
]
