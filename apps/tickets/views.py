from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsAdminRole

from .models import Category, Ticket, TicketHistory, TicketNote
from .permissions import IsOperator
from .serializers import (
    CategorySerializer,
    OperatorColleagueSerializer,
    TicketHistorySerializer,
    TicketNoteSerializer,
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
        old_assigned_to = serializer.instance.assigned_to

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

        # Bug fix (Stage 2.6): reassigning a ticket to a colleague through
        # this PATCH endpoint used to go completely unlogged — only
        # self-assign (OperatorTicketAssignView) and status/priority changes
        # were recorded. The timeline (Stage 2.1) needs this entry too.
        if "assigned_to" in serializer.validated_data and ticket.assigned_to_id != (
            old_assigned_to.id if old_assigned_to else None
        ):
            TicketHistory.objects.create(
                ticket=ticket,
                user=self.request.user,
                action=TicketHistory.Action.ASSIGNED,
                old_value=old_assigned_to.username if old_assigned_to else None,
                new_value=ticket.assigned_to.username if ticket.assigned_to else None,
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

        old_assigned_to = ticket.assigned_to
        old_status = ticket.status

        ticket.assigned_to = request.user
        ticket.status = Ticket.Status.IN_PROGRESS

        ticket.save(
            update_fields=[
                "assigned_to",
                "status",
                "updated_at",
            ]
        )

        # Bug fix (Stage 2.6): self-assign silently changed both
        # assigned_to and status without ever touching TicketHistory.
        TicketHistory.objects.create(
            ticket=ticket,
            user=request.user,
            action=TicketHistory.Action.ASSIGNED,
            old_value=old_assigned_to.username if old_assigned_to else None,
            new_value=request.user.username,
        )

        if old_status != Ticket.Status.IN_PROGRESS:
            TicketHistory.objects.create(
                ticket=ticket,
                user=request.user,
                action=TicketHistory.Action.STATUS_CHANGED,
                old_value=old_status,
                new_value=Ticket.Status.IN_PROGRESS,
            )

        return Response(
            OperatorTicketSerializer(ticket).data,
            status=status.HTTP_200_OK,
        )


class OperatorColleaguesListView(generics.ListAPIView):
    """
    GET /api/v1/operator/colleagues/ — every operator in the current
    user's department, so a ticket can be assigned (or reassigned) to any
    of them, not just to yourself. Deliberately unpaginated: department
    rosters are small, and the frontend just needs the full list to
    populate a dropdown in one shot.
    """

    serializer_class = OperatorColleagueSerializer
    permission_classes = [IsOperator]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return get_user_model().objects.none()

        return (
            get_user_model().objects
            .filter(
                role="OPERATOR",
                department=self.request.user.department,
            )
            .order_by("username")
        )


def _get_department_ticket_or_404(request, pk):
    """
    Shared lookup for the timeline endpoints: an operator may only see the
    history/notes of a ticket that belongs to their own department — same
    scoping rule as every other operator ticket endpoint.
    """
    return get_object_or_404(
        Ticket,
        pk=pk,
        department=request.user.department,
    )


@extend_schema(responses=TicketHistorySerializer(many=True))
class TicketHistoryView(APIView):
    """
    GET /api/v1/operator/tickets/{id}/history/

    Returns the ticket's full timeline: TicketHistory entries (created,
    assigned, status/priority changes) merged with TicketNote entries
    (free-form operator notes), sorted chronologically. Guests never hit
    this endpoint — IsOperator enforces that internal notes stay internal.
    """

    permission_classes = [IsOperator]

    def get(self, request, pk):
        ticket = _get_department_ticket_or_404(request, pk)

        history_qs = ticket.history.select_related("user")
        notes_qs = ticket.notes.select_related("author")

        entries = [
            *TicketHistorySerializer(history_qs, many=True).data,
            *TicketNoteSerializer(notes_qs, many=True).data,
        ]
        entries.sort(key=lambda entry: entry["created_at"])

        return Response(entries)


class TicketNoteCreateView(generics.CreateAPIView):
    """
    POST /api/v1/operator/tickets/{id}/notes/

    Adds an internal note to a ticket. Only operators in the ticket's own
    department can post — same scoping as the rest of the operator API.
    """

    serializer_class = TicketNoteSerializer
    permission_classes = [IsOperator]

    def perform_create(self, serializer):
        ticket = _get_department_ticket_or_404(self.request, self.kwargs["pk"])
        serializer.save(ticket=ticket, author=self.request.user)