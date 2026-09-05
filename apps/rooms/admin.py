from django.contrib import admin

from .models import Room, RoomStatusLog


class RoomStatusLogInline(admin.TabularInline):
    """Read-only — entries are only ever created by Room.save(), never
    edited or added by hand from the admin."""

    model = RoomStatusLog
    fields = ("previous_status", "new_status", "changed_at")
    readonly_fields = ("previous_status", "new_status", "changed_at")
    ordering = ("-changed_at",)
    extra = 0
    can_delete = False
    verbose_name = "تغییر وضعیت"
    verbose_name_plural = "تاریخچهٔ وضعیت اتاق"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "floor", "status")
    list_display_links = ("number",)
    # Unlike Ticket, Room has no state machine and RoomSerializer lets an
    # admin write status/floor freely (confirmed by
    # test_admin_can_update_room_status) — so there's no business rule for
    # Admin to bypass here, and list_editable is safe: it just saves a click
    # for the very common "mark this room MAINTENANCE / AVAILABLE" action.
    list_editable = ("floor", "status")
    list_filter = ("status", "floor")
    search_fields = ("number",)
    ordering = ("number",)
    # Stage 2.7 — the log itself is written by Room.save(), this inline
    # just surfaces it on the room's own admin page.
    inlines = [RoomStatusLogInline]