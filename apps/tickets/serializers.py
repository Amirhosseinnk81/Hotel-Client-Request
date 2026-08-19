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