from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Ticket
from .serializers import (
    TicketSerializer,
    OperatorTicketSerializer,
)

from .permissions import IsOperator


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
        
class OperatorTicketListView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return (
            Ticket.objects
            .filter(
                department=self.request.user.department,
            )
            .select_related("guest", "department")
        )
        
class OperatorTicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OperatorTicketSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return (
            Ticket.objects
            .filter(
                department=self.request.user.department,
            )
            .select_related("guest", "department")
        )