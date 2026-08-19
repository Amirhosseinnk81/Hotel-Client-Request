from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Ticket
from .serializers import TicketSerializer


class GuestTicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.filter(
            guest__user=self.request.user
        ).select_related("department")

    def perform_create(self, serializer):
        serializer.save(
            guest=self.request.user.guest_profile
        )


class GuestTicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.filter(
            guest__user=self.request.user
        ).select_related("department")