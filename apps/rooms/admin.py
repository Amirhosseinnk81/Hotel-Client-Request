from django.contrib import admin

from .models import Room


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