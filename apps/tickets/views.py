from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .models import Ticket, TicketHistory
from .permissions import IsOperator
from .serializers import (
    TicketSerializer,
    OperatorTicketSerializer,
)


class GuestTicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()

        return (
            Ticket.objects
            .filter(
                guest__user=self.request.user
            )
            .select_related("department")
        )

    def perform_create(self, serializer):
        ticket = serializer.save(
            guest=self.request.user.guest_profile
        )

        TicketHistory.objects.create(
            ticket=ticket,
            user=self.request.user,
            action=TicketHistory.Action.CREATED,
            new_value=Ticket.Status.OPEN,
        )


class GuestTicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()

        return (
            Ticket.objects
            .filter(
                guest__user=self.request.user
            )
            .select_related("department")
        )


class OperatorTicketListView(generics.ListAPIView):
    serializer_class = OperatorTicketSerializer
    permission_classes = [IsOperator]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "status",
        "priority",
        "assigned_to",
    ]

    search_fields = [
        "title",
        "description",
    ]

    ordering_fields = [
        "created_at",
        "updated_at",
        "priority",
        "status",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()

        return (
            Ticket.objects
            .filter(
                department=self.request.user.department,
            )
            .select_related(
                "guest",
                "department",
                "assigned_to",
            )
        )


class OperatorTicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OperatorTicketSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()

        return (
            Ticket.objects
            .filter(
                department=self.request.user.department,
            )
            .select_related(
                "guest",
                "department",
                "assigned_to",
            )
        )


@extend_schema(
    request=None,
    responses=OperatorTicketSerializer,
)
class OperatorTicketAssignView(APIView):
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            ticket = (
                Ticket.objects
                .select_related(
                    "department",
                    "assigned_to",
                )
                .get(
                    pk=pk,
                    department=request.user.department,
                )
            )

        except Ticket.DoesNotExist:
            return Response(
                {"detail": "Ticket not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ticket.assigned_to = request.user
        ticket.status = Ticket.Status.IN_PROGRESS

        ticket.save(
            update_fields=[
                "assigned_to",
                "status",
                "updated_at",
            ]
        )

        return Response(
            OperatorTicketSerializer(ticket).data,
            status=status.HTTP_200_OK,
        )