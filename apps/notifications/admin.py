from django.contrib import admin, messages
from django.utils import timezone

from .models import MessageTemplate, SmsMessage


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    """The guest SMS text for each ticket event — edit, or switch an event off."""

    list_display = ("event", "is_active", "body", "updated_at")
    list_editable = ("is_active",)
    readonly_fields = ("updated_at",)


@admin.register(SmsMessage)
class SmsMessageAdmin(admin.ModelAdmin):
    """The SMS outbox — read-only history, plus a retry for given-up messages."""

    list_display = ("created_at", "event", "phone", "status", "attempts", "sent_at", "ticket")
    list_filter = ("status", "event")
    search_fields = ("phone", "body", "ticket__id")
    readonly_fields = [field.name for field in SmsMessage._meta.fields]
    actions = ["retry"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Retry selected messages now")
    def retry(self, request, queryset):
        count = queryset.exclude(status=SmsMessage.Status.SENT).update(
            status=SmsMessage.Status.PENDING, attempts=0, next_attempt_at=timezone.now()
        )
        self.message_user(request, f"{count} message(s) queued again.", messages.SUCCESS)
