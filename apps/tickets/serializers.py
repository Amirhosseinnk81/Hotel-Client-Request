from rest_framework import serializers

from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
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

    assigned_to_username = serializers.CharField(
        source="assigned_to.username",
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
            "assigned_to",
            "assigned_to_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "department",
            "department_name",
            "created_at",
            "updated_at",
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