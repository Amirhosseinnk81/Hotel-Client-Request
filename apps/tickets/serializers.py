from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    CannedResponse,
    Category,
    QuickRequestTemplate,
    Ticket,
    TicketAttachment,
    TicketHistory,
    TicketNote,
)


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """
    A single image attached to a ticket (Stage 2.8). `image` is the one
    writable field — the dedicated upload endpoints (guest/operator) set
    `ticket`/`uploaded_by` themselves via serializer.save(), so those two
    never need to come from the request body.
    """

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )

    class Meta:
        model = TicketAttachment
        fields = ["id", "image", "uploaded_by_username", "created_at"]
        read_only_fields = ["id", "uploaded_by_username", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "code",
            "is_active",
            "sla_minutes",
            "response_sla_minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TicketSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    room_number = serializers.CharField(
        source="room.number",
        read_only=True,
    )

    can_reopen = serializers.BooleanField(source="can_guest_reopen", read_only=True)

    attachments = TicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "department",
            "department_name",
            "category",
            "category_name",
            "room_number",
            "resolution",
            "guest_rating",
            "guest_feedback",
            "reopened_at",
            "can_reopen",
            "merged_into",
            "attachments",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "resolution",
            "guest_rating",
            "guest_feedback",
            "reopened_at",
            "can_reopen",
            "merged_into",
            "created_at",
            "updated_at",
            "resolved_at",
        ]

    def validate(self, attrs):
        if self.instance and "status" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "status": "You cannot change the ticket status."
                }
            )

        return attrs


class OperatorTicketSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    room_number = serializers.CharField(
        source="room.number",
        read_only=True,
    )

    assigned_to_username = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
    )

    is_overdue = serializers.BooleanField(read_only=True)
    overdue_since = serializers.DateTimeField(read_only=True)
    response_deadline = serializers.DateTimeField(read_only=True)
    is_response_overdue = serializers.BooleanField(read_only=True)

    attachments = TicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "department",
            "department_name",
            "category",
            "category_name",
            "room_number",
            "assigned_to",
            "assigned_to_username",
            "resolution",
            "is_overdue",
            "overdue_since",
            "first_response_at",
            "response_deadline",
            "is_response_overdue",
            "merged_into",
            "attachments",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "department",
            "department_name",
            "category",
            "category_name",
            "room_number",
            "is_overdue",
            "overdue_since",
            "first_response_at",
            "response_deadline",
            "is_response_overdue",
            "merged_into",
            "created_at",
            "updated_at",
            "resolved_at",
        ]

    def validate_status(self, value):
        if not self.instance:
            return value

        if value == self.instance.status:
            return value

        if not self.instance.can_transition_to(value):
            raise serializers.ValidationError(
                f"Invalid status transition: "
                f"{self.instance.status} -> {value}."
            )

        return value

    def validate_assigned_to(self, value):
        # RESOLVED/CANCELLED are terminal. Reassigning one is meaningless
        # at best, and it's the same hole the assign endpoint used to have
        # (it would pull a closed ticket back to IN_PROGRESS). Resending
        # the current assignee is a harmless no-op, so only a change is
        # refused.
        if (
            self.instance is not None
            and self.instance.status in (Ticket.Status.RESOLVED, Ticket.Status.CANCELLED)
            and value != self.instance.assigned_to
        ):
            raise serializers.ValidationError("A closed ticket cannot be reassigned.")

        if value is not None and value.role != "OPERATOR":
            raise serializers.ValidationError(
                "Ticket can only be assigned to an operator."
            )

        if (
            value is not None
            and self.instance is not None
            and value.department_id != self.instance.department_id
        ):
            raise serializers.ValidationError(
                "Ticket can only be assigned to an operator from the same department."
            )

        return value

    def validate(self, attrs):
        new_status = attrs.get("status")

        if new_status == Ticket.Status.RESOLVED:
            resolution = attrs.get(
                "resolution",
                getattr(self.instance, "resolution", None),
            )
            if not resolution:
                raise serializers.ValidationError(
                    {
                        "resolution": "A resolution is required before marking a ticket as resolved."
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        if validated_data.get("status") == Ticket.Status.RESOLVED and instance.status != Ticket.Status.RESOLVED:
            validated_data["resolved_at"] = timezone.now()

        return super().update(instance, validated_data)


class OperatorColleagueSerializer(serializers.ModelSerializer):
    """
    Minimal representation of a fellow operator in the same department —
    just enough to populate a "reassign this ticket to..." dropdown, with
    each person's current workload.

    `active_tickets` comes from a queryset annotation
    (services.active_tickets_count), so this serializer must be given a
    queryset annotated with it; OperatorColleaguesListView does that.
    """

    active_tickets = serializers.IntegerField(read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "username", "active_tickets", "is_available"]
        read_only_fields = fields

    def get_is_available(self, obj) -> bool:
        # Derived, never stored: available only while holding no active ticket.
        return obj.active_tickets == 0


class TicketHistorySerializer(serializers.ModelSerializer):
    """
    A single system-generated audit entry (assignment, status/priority
    change). Rendered as one kind of row in the merged ticket timeline.
    """

    entry_type = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    user_username = serializers.CharField(
        source="user.username", read_only=True, default=None
    )

    class Meta:
        model = TicketHistory
        fields = [
            "entry_type",
            "id",
            "action",
            "action_display",
            "old_value",
            "new_value",
            "user_username",
            "created_at",
        ]
        read_only_fields = fields

    def get_entry_type(self, obj) -> str:
        return "history"


class TicketNoteSerializer(serializers.ModelSerializer):
    """
    An internal note authored by an operator/admin. Rendered as the other
    kind of row in the merged ticket timeline. `text` is the only
    writable field on create — `ticket`/`author` are set by the view.
    """

    entry_type = serializers.SerializerMethodField()
    author_username = serializers.CharField(
        source="author.username", read_only=True, default=None
    )

    class Meta:
        model = TicketNote
        fields = [
            "entry_type",
            "id",
            "text",
            "author_username",
            "created_at",
        ]
        read_only_fields = [
            "entry_type",
            "id",
            "author_username",
            "created_at",
        ]

    def get_entry_type(self, obj) -> str:
        return "note"

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Note text cannot be empty.")
        return value

class TicketRateSerializer(serializers.Serializer):
    """POST /tickets/{id}/rate/ — write-only input, the view returns a TicketSerializer."""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class CannedResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CannedResponse
        fields = ["id", "title", "body", "department"]
        read_only_fields = fields


class TicketMergeSerializer(serializers.Serializer):
    """POST /operator/tickets/{id}/merge/ — the ticket to fold this duplicate into."""

    into = serializers.IntegerField()


class QuickRequestTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickRequestTemplate
        fields = ["id", "title", "icon", "department", "category", "order"]
        read_only_fields = fields


class AdminStatsByStatusSerializer(serializers.Serializer):
    """Ticket count per Ticket.Status value, system-wide (Stage 2.4)."""

    OPEN = serializers.IntegerField()
    IN_PROGRESS = serializers.IntegerField()
    RESOLVED = serializers.IntegerField()
    CANCELLED = serializers.IntegerField()


class AdminStatsByDepartmentSerializer(serializers.Serializer):
    """One row of the by-department breakdown (Stage 2.4)."""

    department_id = serializers.IntegerField()
    department_name = serializers.CharField()
    open = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    resolved = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    total = serializers.IntegerField()
    rating_avg = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()


class RecentFeedbackSerializer(serializers.Serializer):
    """One recent written guest comment, for the ratings report."""

    ticket_id = serializers.IntegerField()
    title = serializers.CharField()
    rating = serializers.IntegerField()
    feedback = serializers.CharField()
    operator = serializers.CharField(allow_null=True)
    department_name = serializers.CharField()
    resolved_at = serializers.DateTimeField()


class AdminStatsSummarySerializer(serializers.Serializer):
    """
    GET /admin/stats/summary/ (Stage 2.4) — read-only aggregate view for
    admins: ticket counts by status/department, average resolution time
    over the last `resolution_window_days`, and the current system-wide
    overdue count (Stage 2.9 SLA).
    """

    by_status = AdminStatsByStatusSerializer()
    by_department = AdminStatsByDepartmentSerializer(many=True)
    avg_resolution_minutes = serializers.FloatField(allow_null=True)
    overdue_count = serializers.IntegerField()
    response_overdue_count = serializers.IntegerField(
        help_text="Tickets still waiting for anyone to start on them, past their first-response target."
    )
    avg_first_response_minutes = serializers.FloatField(allow_null=True)
    response_sla_met_percent = serializers.FloatField(
        allow_null=True, help_text="Share of due tickets started within the first-response target."
    )
    resolution_sla_met_percent = serializers.FloatField(
        allow_null=True, help_text="Share of due tickets resolved within the resolution target."
    )
    rating_avg = serializers.FloatField(allow_null=True, help_text="Average guest rating (1-5) in the window.")
    rating_count = serializers.IntegerField()
    rating_distribution = serializers.DictField(
        child=serializers.IntegerField(), help_text='Ratings per star, keys "1".."5".'
    )
    recent_feedback = RecentFeedbackSerializer(many=True)
    resolution_window_days = serializers.IntegerField()
    generated_at = serializers.DateTimeField()


class DepartmentStatsByOperatorSerializer(serializers.Serializer):
    """One operator's workload in the department summary."""

    operator_id = serializers.IntegerField()
    username = serializers.CharField()
    is_supervisor = serializers.BooleanField()
    active = serializers.IntegerField(
        help_text="Assigned tickets still OPEN or IN_PROGRESS."
    )
    resolved_recent = serializers.IntegerField(
        help_text="Assigned tickets resolved within resolution_window_days."
    )
    rating_avg = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()


class DepartmentStatsSummarySerializer(serializers.Serializer):
    """
    GET /operator/stats/summary/ — the admin Stats Summary, scoped to the
    caller's own department. Same by_status / average resolution / overdue
    figures; by_department is replaced by by_operator, since a
    one-department report broken down by department would be a single row.
    """

    department_id = serializers.IntegerField()
    department_name = serializers.CharField()
    by_status = AdminStatsByStatusSerializer()
    by_operator = DepartmentStatsByOperatorSerializer(many=True)
    avg_resolution_minutes = serializers.FloatField(allow_null=True)
    overdue_count = serializers.IntegerField()
    response_overdue_count = serializers.IntegerField(
        help_text="Tickets still waiting for anyone to start on them, past their first-response target."
    )
    avg_first_response_minutes = serializers.FloatField(allow_null=True)
    response_sla_met_percent = serializers.FloatField(
        allow_null=True, help_text="Share of due tickets started within the first-response target."
    )
    resolution_sla_met_percent = serializers.FloatField(
        allow_null=True, help_text="Share of due tickets resolved within the resolution target."
    )
    rating_avg = serializers.FloatField(allow_null=True, help_text="Average guest rating (1-5) in the window.")
    rating_count = serializers.IntegerField()
    rating_distribution = serializers.DictField(
        child=serializers.IntegerField(), help_text='Ratings per star, keys "1".."5".'
    )
    recent_feedback = RecentFeedbackSerializer(many=True)
    resolution_window_days = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
