from rest_framework import generics

from apps.core.permissions import IsAdminRole

from .models import Room
from .serializers import RoomSerializer


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
