from django.contrib import admin

from .models import DepartmentRequest, Goal, Process, Project, RoomDailyStat, Task


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "process_type",
        "department",
        "frequency",
        "status",
        "responsible",
        "next_due_at",
    )
    list_filter = ("process_type", "department", "frequency", "status")
    search_fields = ("title", "description")
    ordering = ("next_due_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "owner", "start_date", "due_date")
    list_filter = ("status", "priority")
    search_fields = ("title", "description")


@admin.register(DepartmentRequest)
class DepartmentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "requesting_department",
        "priority",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("requesting_department", "priority", "status")
    search_fields = ("title", "description", "requested_by_name")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "goal_type", "status", "target_date", "owner")
    list_filter = ("goal_type", "status")
    search_fields = ("title", "description")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "assigned_to",
        "due_date",
        "related_process",
        "related_project",
        "related_request",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "description")


@admin.register(RoomDailyStat)
class RoomDailyStatAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "total_rooms",
        "occupied_rooms",
        "vacant_rooms",
        "out_of_order_rooms",
        "occupancy_rate",
    )
    ordering = ("-date",)
