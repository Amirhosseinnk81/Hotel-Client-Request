"""
The television's own URL, kept out of `/api/v1/` on purpose: it is a
page a set-top box opens, not an API call — see apps/iptv/views.py.
"""

from django.urls import path

from .views import TvRoomPageView

app_name = "tv"

urlpatterns = [
    path("<str:room_number>/", TvRoomPageView.as_view(), name="room"),
]
