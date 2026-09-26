from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.core.permissions import is_it_operator, is_it_staff

from .models import (
    DepartmentRequest,
    DepartmentRequestAttachment,
    Goal,
    ITRequestTemplate,
    Process,
    Project,
    RoomDailyStat,
    Task,
)


def validate_it_assignee(user, allow_admin=False):
    """
    Work can only be handed to IT operators — never to a housekeeping
    operator, a guest, or (for day-to-day work) an admin. Project and goal
    owners may also be admins, since hotel management can own those.
    """
    if user is None:
        return user
    allowed = is_it_staff(user) if allow_admin else is_it_operator(user)
    if not allowed:
        raise serializers.ValidationError(
            "Can only be assigned to IT staff." if allow_admin
            else "Can only be assigned to an IT operator."
        )
    return user


class ProcessSerializer(serializers.ModelSerializer):
    process_type_display = serializers.CharField(
        source="get_process_type_display", read_only=True
    )
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )
    frequency_display = serializers.CharField(
        source="get_frequency_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    responsible_username = serializers.CharField(
        source="responsible.username", read_only=True, default=None
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Process
        fields = [
            "id",
            "title",
            "description",
            "process_type",
            "process_type_display",
            "department",
            "department_name",
            "frequency",
            "frequency_display",
            "status",
            "status_display",
            "responsible",
            "responsible_username",
            "last_done_at",
            "next_due_at",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_responsible(self, value):
        return validate_it_assignee(value)


class ProjectSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    owner_username = serializers.CharField(
        source="owner.username", read_only=True, default=None
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "owner",
            "owner_username",
            "start_date",
            "due_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_owner(self, value):
        return validate_it_assignee(value, allow_admin=True)

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        due = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if start and due and due < start:
            raise serializers.ValidationError({"due_date": "Due date cannot be before the start date."})
        return attrs


# Named explicitly: with COMPONENT_SPLIT_REQUEST the departments app's
# DepartmentSerializer already produces a "DepartmentRequest" component.
class ITRequestAttachmentSerializer(serializers.ModelSerializer):
    """
    One photo on a request to IT. `image` is the only writable field: the
    upload endpoint sets the request and the uploader itself, so neither
    ever comes from the body.
    """

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )

    class Meta:
        model = DepartmentRequestAttachment
        fields = ["id", "image", "uploaded_by_username", "created_at"]
        read_only_fields = ["id", "uploaded_by_username", "created_at"]


class ITRequestTemplateSerializer(serializers.ModelSerializer):
    """The one-click shortcuts on the "ask IT" form. Read-only: Django Admin owns them."""

    class Meta:
        model = ITRequestTemplate
        fields = ["id", "title", "description", "icon", "priority", "order"]
        read_only_fields = fields


class ITRequestRateSerializer(serializers.Serializer):
    """What the asking department sends back once the work is done."""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


@extend_schema_serializer(component_name="ITDepartmentRequest")
class DepartmentRequestSerializer(serializers.ModelSerializer):
    requesting_department_name = serializers.CharField(
        source="requesting_department.name", read_only=True, default=None
    )
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, default=None
    )
    requested_by_username = serializers.CharField(
        source="requested_by.username", read_only=True, default=None
    )
    # What the asking department attached and, once the work is done, what
    # they thought of it. Read-only: IT sees the feedback, never writes it.
    attachments = ITRequestAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = DepartmentRequest
        fields = [
            "id",
            "title",
            "description",
            "attachments",
            "rating",
            "feedback",
            "rated_at",
            "requesting_department",
            "requesting_department_name",
            "requested_by",
            "requested_by_username",
            "requested_by_name",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "assigned_to",
            "assigned_to_username",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        # resolved_at follows the status (DepartmentRequest.save());
        # requested_by is only ever set by OutgoingITRequestViewSet.
        read_only_fields = [
            "id",
            "requested_by",
            "attachments",
            "rating",
            "feedback",
            "rated_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            # Nullable in the DB only for legacy rows; new requests need one.
            "requesting_department": {"required": True, "allow_null": False},
        }

    def validate_assigned_to(self, value):
        return validate_it_assignee(value)


class OutgoingITRequestSerializer(serializers.ModelSerializer):
    """
    A department's own request to IT, as its operators see it: they write
    the title, description and urgency; everything else (department,
    requester, status, assignee) is IT's or the server's to set.
    """

    requesting_department_name = serializers.CharField(
        source="requesting_department.name", read_only=True, default=None
    )
    requested_by_username = serializers.CharField(
        source="requested_by.username", read_only=True, default=None
    )
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, default=None
    )
    attachments = ITRequestAttachmentSerializer(many=True, read_only=True)
    # Whether the "how did it go?" box should be offered — computed on the
    # model so the panel can't disagree with what the endpoint will accept.
    can_be_rated = serializers.BooleanField(read_only=True)

    class Meta:
        model = DepartmentRequest
        fields = [
            "id",
            "title",
            "description",
            "priority",
            "status",
            "requesting_department_name",
            "requested_by_username",
            "assigned_to_username",
            "attachments",
            "rating",
            "feedback",
            "rated_at",
            "can_be_rated",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "requesting_department_name",
            "requested_by_username",
            "assigned_to_username",
            "attachments",
            # Set through the dedicated rate endpoint, never by PATCHing.
            "rating",
            "feedback",
            "rated_at",
            "can_be_rated",
            "resolved_at",
            "created_at",
            "updated_at",
        ]


class ITStaffMemberSerializer(serializers.Serializer):
    """One IT operator, for the assignee dropdowns of the IT forms."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    is_supervisor = serializers.BooleanField()


class GoalSerializer(serializers.ModelSerializer):
    goal_type_display = serializers.CharField(
        source="get_goal_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    owner_username = serializers.CharField(
        source="owner.username", read_only=True, default=None
    )
    related_project_title = serializers.CharField(
        source="related_project.title", read_only=True, default=None
    )

    class Meta:
        model = Goal
        fields = [
            "id",
            "title",
            "description",
            "goal_type",
            "goal_type_display",
            "status",
            "status_display",
            "target_date",
            "owner",
            "owner_username",
            "related_project",
            "related_project_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_owner(self, value):
        return validate_it_assignee(value, allow_admin=True)


class TaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, default=None
    )
    assigned_by_username = serializers.CharField(
        source="assigned_by.username", read_only=True, default=None
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "assigned_to",
            "assigned_to_username",
            "assigned_by",
            "assigned_by_username",
            "due_date",
            "related_process",
            "related_project",
            "related_request",
            "created_at",
            "updated_at",
        ]
        # assigned_by is whoever created the task (set by TaskViewSet).
        read_only_fields = ["id", "assigned_by", "created_at", "updated_at"]

    def validate_assigned_to(self, value):
        return validate_it_assignee(value)


class RoomDailyStatSerializer(serializers.ModelSerializer):
    """Read-only: every figure is computed from Room data (it_ops.services)."""

    occupancy_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = RoomDailyStat
        fields = [
            "id",
            "date",
            "total_rooms",
            "occupied_rooms",
            "vacant_rooms",
            "out_of_order_rooms",
            "occupancy_rate",
            "notes",
            "recorded_at",
        ]
        read_only_fields = fields


class RoomStatsSnapshotRequestSerializer(serializers.Serializer):
    """POST /it-ops/room-stats/snapshot/ — which day to (re)compute; default today."""

    date = serializers.DateField(required=False)


class RoomStatsTodaySerializer(serializers.Serializer):
    date = serializers.DateField()
    total_rooms = serializers.IntegerField()
    occupied_rooms = serializers.IntegerField()
    vacant_rooms = serializers.IntegerField()
    out_of_order_rooms = serializers.IntegerField()
    occupancy_rate = serializers.SerializerMethodField()

    def get_occupancy_rate(self, obj) -> float:
        total = obj["total_rooms"]
        return round(obj["occupied_rooms"] / total * 100, 1) if total else 0


class TodayDashboardSerializer(serializers.Serializer):
    date = serializers.DateField()
    generated_at = serializers.DateTimeField()
    tasks_due_or_overdue = TaskSerializer(many=True)
    processes_due_or_overdue = ProcessSerializer(many=True)
    open_department_requests = DepartmentRequestSerializer(many=True)
    room_stats_today = RoomStatsTodaySerializer()
    my_open_tasks_count = serializers.IntegerField()
