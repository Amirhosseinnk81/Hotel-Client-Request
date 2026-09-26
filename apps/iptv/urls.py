from django.urls import path

from .views import IptvRoomScreenView

app_name = "iptv"

urlpatterns = [
    path("iptv/rooms/<str:room_number>/", IptvRoomScreenView.as_view(), name="room-screen"),
]
