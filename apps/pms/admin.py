from django.contrib import admin, messages

from .models import PmsEvent, PmsSyncState
from .services import apply_event


@admin.register(PmsEvent)
class PmsEventAdmin(admin.ModelAdmin):
    """
    The PMS call log (Stage 3.3). Read-only history: when a room looks
    wrong, this shows exactly what the PMS sent and what we did with it.
    A failed event can be replayed from its stored payload.
    """

    list_display = ("received_at", "event_type", "status", "room_number", "reservation_id", "error")
    list_filter = ("status", "event_type", "source")
    search_fields = ("room_number", "reservation_id", "external_id", "error")
    readonly_fields = [field.name for field in PmsEvent._meta.fields]
    actions = ["retry"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Apply the selected events again")
    def retry(self, request, queryset):
        applied = [apply_event(event.payload, source=event.source) for event in queryset]
        ok = sum(1 for event in applied if event.status == PmsEvent.Status.PROCESSED)
        self.message_user(request, f"{ok} of {len(applied)} applied.", messages.SUCCESS)


@admin.register(PmsSyncState)
class PmsSyncStateAdmin(admin.ModelAdmin):
    """Where `pull_pms` got to. Editable only to re-run a window by hand."""

    list_display = ("last_synced_at", "last_run_at", "last_error")

    def has_add_permission(self, request):
        return not PmsSyncState.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
