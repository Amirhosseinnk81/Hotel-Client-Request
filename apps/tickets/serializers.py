from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Category, Ticket, TicketHistory, TicketNote


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "code", "is_active", "sla_minutes", "created_at", "updated_at"]
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
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "resolution",
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
    just enough to populate a "reassign this ticket to..." dropdown.
    """

    class Meta:
        model = get_user_model()
        fields = ["id", "username", "is_available"]
        read_only_fields = fields


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