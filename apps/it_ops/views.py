"""
IT Ops API (/api/v1/it-ops/). ViewSets rather than the generics the rest of
the project uses, because every resource here is plain CRUD with the same
filters/permissions shape — the router keeps six of them to one urls.py.

Access (apps.core.permissions.IsITStaff + CanWorkOnITItem):
  - only IT operators and admins, for reading too;
  - the IT supervisor (and admins) may do anything;
  - a regular IT operator may create tasks and department requests for
    themselves and work on what is assigned to them, but not assign,
    re-prioritise, reject, or delete.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import (
    CanWorkOnITItem,
    IsITStaff,
    IsOperatorWithDepartment,
    is_it_supervisor,
    it_department_code,
)

from .filters import (
    DepartmentRequestFilter,
    GoalFilter,
    ProcessFilter,
    ProjectFilter,
    RoomDailyStatFilter,
    TaskFilter,
)
from .models import (
    DepartmentRequest,
    Goal,
    Process,
    Project,
    RoomDailyStat,
    Task,
    priority_rank,
)
from .serializers import (
    DepartmentRequestSerializer,
    GoalSerializer,
    ITStaffMemberSerializer,
    OutgoingITRequestSerializer,
    ProcessSerializer,
    ProjectSerializer,
    RoomDailyStatSerializer,
    RoomStatsSnapshotRequestSerializer,
    TaskSerializer,
    TodayDashboardSerializer,
)
from .services import compute_today_dashboard, mark_process_done, snapshot_room_stats

IT_PERMISSIONS = [IsITStaff, CanWorkOnITItem]


class ProcessViewSet(viewsets.ModelViewSet):
    serializer_class = ProcessSerializer
    permission_classes = IT_PERMISSIONS
    filterset_class = ProcessFilter
    search_fields = ["title", "description"]

    # The responsible person may mark their process done; changing the
    # process itself (schedule, owner, status) is the supervisor's call.
    it_assignee_field = "responsible"
    it_assignee_actions = {"mark_done"}

    def get_queryset(self):
        return Process.objects.select_related("department", "responsible")

    @extend_schema(request=None, responses=ProcessSerializer)
    @action(detail=True, methods=["post"], url_path="mark-done")
    def mark_done(self, request, pk=None):
        """
        POST /it-ops/processes/{id}/mark-done/ — the process was just carried
        out. Sets last_done_at to now; for a recurring process next_due_at
        moves one period on (Process.save()).
        """
        process = self.get_object()
        mark_process_done(process)
        return Response(self.get_serializer(process).data)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = IT_PERMISSIONS
    filterset_class = ProjectFilter
    search_fields = ["title", "description"]

    def get_queryset(self):
        return (
            Project.objects.select_related("owner")
            .annotate(priority_rank=priority_rank())
            .order_by("-priority_rank", "due_date", "title")
        )


class DepartmentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentRequestSerializer
    permission_classes = IT_PERMISSIONS
    filterset_class = DepartmentRequestFilter
    search_fields = ["title", "description", "requested_by_name"]

    # Any IT operator can log a request another department called in, and
    # the assignee works it through to COMPLETED. Assigning, re-prioritising
    # and turning a request down are triage — the supervisor's.
    it_staff_can_create = True
    it_assignee_field = "assigned_to"
    it_supervisor_only_fields = ("assigned_to", "priority")
    it_supervisor_only_values = {"status": {DepartmentRequest.Status.REJECTED}}

    def get_queryset(self):
        return (
            DepartmentRequest.objects.select_related(
                "requesting_department", "requested_by", "assigned_to"
            )
            .annotate(priority_rank=priority_rank())
            .order_by("-priority_rank", "created_at")
        )


class OutgoingITRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    /it-ops/outgoing-requests/ — how every other department asks IT for
    something, from its own operator panel. Open to any operator with a
    department, supervisor or not, and deliberately narrow:

    - they see only their own department's requests (never another
      department's, and none of IT's internal tasks or projects);
    - the department and requester are always taken from request.user,
      never from the body;
    - they can file and follow a request, not change it afterwards —
      status and assignment are IT's.
    """

    serializer_class = OutgoingITRequestSerializer
    permission_classes = [IsOperatorWithDepartment]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # Schema generation runs without a real user.
            return DepartmentRequest.objects.none()
        return (
            DepartmentRequest.objects.filter(requesting_department=self.request.user.department)
            .select_related("requesting_department", "requested_by", "assigned_to")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(
            requesting_department=user.department,
            requested_by=user,
            requested_by_name=user.get_full_name() or user.username,
        )


class ITStaffListView(APIView):
    """
    GET /it-ops/staff/ — the IT operators, for the assignee dropdowns in
    the IT forms. Not paginated: one department's roster.
    """

    permission_classes = [IsITStaff]

    @extend_schema(responses=ITStaffMemberSerializer(many=True))
    def get(self, request):
        staff = (
            get_user_model()
            .objects.filter(
                role="OPERATOR",
                is_active=True,
                department__code=it_department_code(),
            )
            .order_by("-is_supervisor", "username")
        )
        return Response(ITStaffMemberSerializer(staff, many=True).data)


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = IT_PERMISSIONS
    filterset_class = GoalFilter
    search_fields = ["title", "description"]

    def get_queryset(self):
        return Goal.objects.select_related("owner", "related_project")


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = IT_PERMISSIONS
    filterset_class = TaskFilter
    search_fields = ["title", "description"]

    it_staff_can_create = True
    it_assignee_field = "assigned_to"
    it_supervisor_only_fields = ("assigned_to", "priority")

    def get_queryset(self):
        return (
            Task.objects.select_related("assigned_to", "assigned_by")
            .annotate(priority_rank=priority_rank())
            .order_by("due_date", "-priority_rank", "created_at")
        )

    def perform_create(self, serializer):
        # A regular IT operator's own task is theirs even when they leave
        # assigned_to out; the supervisor may create unassigned tasks.
        extra = {"assigned_by": self.request.user}
        if not is_it_supervisor(self.request.user):
            extra["assigned_to"] = self.request.user
        serializer.save(**extra)


class RoomDailyStatViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Daily occupancy snapshots. Read-only: the figures are computed from the
    real Room data, never entered by hand (the old manual create/edit is
    gone). New rows come from the nightly `snapshot_room_stats` command or
    from the snapshot action below.
    """

    serializer_class = RoomDailyStatSerializer
    permission_classes = IT_PERMISSIONS
    filterset_class = RoomDailyStatFilter

    def get_queryset(self):
        return RoomDailyStat.objects.all()

    @extend_schema(request=RoomStatsSnapshotRequestSerializer, responses=RoomDailyStatSerializer)
    @action(detail=False, methods=["post"])
    def snapshot(self, request):
        """
        POST /it-ops/room-stats/snapshot/ — (re)compute one day's row now.
        Supervisor only. `date` defaults to today; a past day is rebuilt
        from the room status log. A future day is refused.
        """
        params = RoomStatsSnapshotRequestSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        day = params.validated_data.get("date") or timezone.localdate()
        if day > timezone.localdate():
            raise ValidationError({"date": "Cannot snapshot a day that has not happened yet."})
        return Response(RoomDailyStatSerializer(snapshot_room_stats(day)).data)


class TodayDashboardView(APIView):
    """GET /api/v1/it-ops/today/ — see it_ops.services.compute_today_dashboard."""

    permission_classes = [IsITStaff]

    @extend_schema(responses=TodayDashboardSerializer)
    def get(self, request):
        return Response(TodayDashboardSerializer(compute_today_dashboard(request.user)).data)
