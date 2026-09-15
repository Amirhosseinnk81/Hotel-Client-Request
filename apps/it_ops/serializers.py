from rest_framework import serializers

from .models import (
    DepartmentRequest,
    Goal,
    Process,
    Project,
    RoomDailyStat,
    Task,
)


class ProcessSerializer(serializers.ModelSerializer):
    process_type_display = serializers.CharField(
        source="get_process_type_display", read_only=True
    )
    department_display = serializers.CharField(
        source="get_department_display", read_only=True
    )
    frequency_display = serializers.CharField(
        source="get_frequency_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    responsible_name = serializers.SerializerMethodField()

    class Meta:
        model = Process
        fields = [
            "id",
            "title",
            "description",
            "process_type",
            "process_type_display",
            "department",
            "department_display",
            "frequency",
            "frequency_display",
            "status",
            "status_display",
            "responsible",
            "responsible_name",
            "last_done_at",
            "next_due_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_responsible_name(self, obj):
        return str(obj.responsible) if obj.responsible_id else None


class ProjectSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    owner_name = serializers.SerializerMethodField()

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
            "owner_name",
            "start_date",
            "due_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_owner_name(self, obj):
        return str(obj.owner) if obj.owner_id else None


class DepartmentRequestSerializer(serializers.ModelSerializer):
    requesting_department_display = serializers.CharField(
        source="get_requesting_department_display", read_only=True
    )
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentRequest
        fields = [
            "id",
            "title",
            "description",
            "requesting_department",
            "requesting_department_display",
            "requested_by_name",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "assigned_to",
            "assigned_to_name",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_assigned_to_name(self, obj):
        return str(obj.assigned_to) if obj.assigned_to_id else None


class GoalSerializer(serializers.ModelSerializer):
    goal_type_display = serializers.CharField(
        source="get_goal_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    owner_name = serializers.SerializerMethodField()
    related_project_title = serializers.SerializerMethodField()

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
            "owner_name",
            "related_project",
            "related_project_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_owner_name(self, obj):
        return str(obj.owner) if obj.owner_id else None

    def get_related_project_title(self, obj):
        return obj.related_project.title if obj.related_project_id else None


class TaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    assigned_to_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()

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
            "assigned_to_name",
            "assigned_by",
            "assigned_by_name",
            "due_date",
            "related_process",
            "related_project",
            "related_request",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_assigned_to_name(self, obj):
        return str(obj.assigned_to) if obj.assigned_to_id else None

    def get_assigned_by_name(self, obj):
        return str(obj.assigned_by) if obj.assigned_by_id else None


class RoomDailyStatSerializer(serializers.ModelSerializer):
    occupancy_rate = serializers.ReadOnlyField()

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
        read_only_fields = ["recorded_at"]
