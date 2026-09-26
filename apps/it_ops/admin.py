from django.contrib import admin, messages

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
from .services import mark_process_done, snapshot_room_stats


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "process_type",
        "department",
        "frequency",
        "status",
        "responsible",
        "last_done_at",
        "next_due_at",
    )
    list_filter = ("process_type", "department", "frequency", "status")
    search_fields = ("title", "description")
    ordering = ("next_due_at",)
    actions = ["mark_done"]

    @admin.action(description="Mark selected processes as done now")
    def mark_done(self, request, queryset):
        for process in queryset:
            mark_process_done(process)
        self.message_user(request, f"{queryset.count()} process(es) marked done.", messages.SUCCESS)


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
        "resolved_at",
    )
    list_filter = ("requesting_department", "priority", "status")
    search_fields = ("title", "description", "requested_by_name")
    readonly_fields = ("resolved_at",)


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
    """
    The counts are computed from Room data (it_ops.services), so they are
    read-only here; only the free-text notes can be edited. New rows come
    from the `snapshot_room_stats` command or the action below.
    """

    list_display = (
        "date",
        "total_rooms",
        "occupied_rooms",
        "vacant_rooms",
        "out_of_order_rooms",
        "occupancy_rate",
        "recorded_at",
    )
    ordering = ("-date",)
    readonly_fields = (
        "date",
        "total_rooms",
        "occupied_rooms",
        "vacant_rooms",
        "out_of_order_rooms",
        "recorded_at",
    )
    actions = ["recompute"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Recompute selected days from room data")
    def recompute(self, request, queryset):
        for stat in queryset:
            snapshot_room_stats(stat.date)
        self.message_user(request, f"{queryset.count()} day(s) recomputed.", messages.SUCCESS)


@admin.register(ITRequestTemplate)
class ITRequestTemplateAdmin(admin.ModelAdmin):
    """
    The one-click shortcuts on the "ask IT" form. Managed only here, the
    same as the guest form's quick templates.
    """

    list_display = ("order", "title", "priority", "icon", "is_active")
    list_editable = ("title", "priority", "icon", "is_active")
    list_filter = ("is_active", "priority")
    search_fields = ("title", "description")


@admin.register(DepartmentRequestAttachment)
class DepartmentRequestAttachmentAdmin(admin.ModelAdmin):
    """Photos attached to requests; uploaded from the panel, not here."""

    list_display = ("request", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
