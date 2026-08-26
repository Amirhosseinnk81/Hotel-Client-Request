from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsAdminRole

from .models import Category, Ticket, TicketHistory
from .permissions import IsOperator
from .serializers import (
    CategorySerializer,
    TicketSerializer,
    OperatorTicketSerializer,
)


class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/categories/  — any authenticated user can browse.
    POST /api/v1/categories/  — admins only.

    Only active categories are exposed here — this is the endpoint the
    guest ticket-creation form reads from, so a category the admin has
    disabled must not remain selectable. Direct admin management (including
    toggling is_active) still happens through Django Admin, which queries
    the model directly and is unaffected by this filter.
    """

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminRole]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminRole]


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
            .select_related("department", "category", "room")
        )

    def perform_create(self, serializer):
        guest_profile = self.request.user.guest_profile
        ticket = serializer.save(
            guest=guest_profile,
            room=guest_profile.room,
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
            .select_related("department", "category", "room")
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
                "category",
                "room",
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
                "category",
                "room",
                "assigned_to",
            )
        )

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        old_priority = serializer.instance.priority

        ticket = serializer.save()

        if "status" in serializer.validated_data and ticket.status != old_status:
            TicketHistory.objects.create(
                ticket=ticket,
                user=self.request.user,
                action=TicketHistory.Action.STATUS_CHANGED,
                old_value=old_status,
                new_value=ticket.status,
            )

        if "priority" in serializer.validated_data and ticket.priority != old_priority:
            TicketHistory.objects.create(
                ticket=ticket,
                user=self.request.user,
                action=TicketHistory.Action.PRIORITY_CHANGED,
                old_value=old_priority,
                new_value=ticket.priority,
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
                    "category",
                    "room",
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