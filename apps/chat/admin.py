from django.contrib import admin

from .models import Conversation, Message, Participant


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    readonly_fields = ("joined_at",)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "body", "created_at")
    can_delete = False
    max_num = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Read-mostly: chats are written by the people in them, not here. The
    one thing an admin does from this page is close a thread.
    """

    list_display = ("__str__", "kind", "department", "last_message_at", "is_closed")
    list_filter = ("kind", "is_closed", "department")
    search_fields = ("subject", "guest__full_name", "messages__body")
    readonly_fields = ("kind", "guest", "created_at", "updated_at", "last_message_at")
    inlines = [ParticipantInline, MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "conversation", "sender", "body")
    list_filter = ("created_at",)
    search_fields = ("body",)
    readonly_fields = ("conversation", "sender", "body", "created_at")

    def has_add_permission(self, request):
        return False
