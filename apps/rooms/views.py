from rest_framework import generics

from apps.core.permissions import IsAdminOnly, IsAdminRole

from .models import Room, RoomStatusLog
from .serializers import RoomSerializer, RoomStatusLogSerializer


class RoomListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/rooms/  — any authenticated user can browse.
    POST /api/v1/rooms/  — admins only.
    """

    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAdminRole]


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET               — read for anyone authenticated.
    PATCH/PUT/DELETE  — admins only (e.g. marking a room under MAINTENANCE).
    """

    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAdminRole]


class RoomStatusLogListView(generics.ListAPIView):
    """
    GET /api/v1/rooms/{id}/status-logs/

    Stage 2.7 — the audit trail written automatically by Room.save().
    IsAdminOnly (not IsAdminRole) — IsAdminRole leaves GET open to any
    authenticated user, but this internal operational history should
    stay admin-only for reads too, unlike plain Room data.
    """

    serializer_class = RoomStatusLogSerializer
    permission_classes = [IsAdminOnly]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RoomStatusLog.objects.none()

        return RoomStatusLog.objects.filter(room_id=self.kwargs["pk"])
