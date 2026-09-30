"""
What a chat message looks like on the wire.

One rule here is not cosmetic. The product research in CLAUDE.md's
backlog says: if live chat is ever added, a guest must always be told
who they are talking to — «اپراتور رضا», never an anonymous bubble,
because in five-star hotel usability testing people could not tell
whether there was a person on the other end. So every message carries
`sender_name` and `sender_role`, the payload the SSE stream sends is the
same one the WebSocket sends, and the guest UI is built on them.
"""

from rest_framework import serializers

from .models import Conversation, Message

ROLE_LABELS = {
    "OPERATOR": "اپراتور",
    "ADMIN": "مدیریت",
    "GUEST": "مهمان",
}


def sender_name(message) -> str:
    if message.sender_id is None:
        return "سیستم"
    full = (message.sender.get_full_name() or "").strip()
    if not full and message.sender.role == "GUEST":
        # A guest account has no first/last name — the name the hotel
        # knows them by lives on the Guest profile, and "مهمان
        # guest_1234567890" is not a name anybody should be shown.
        profile = getattr(message.sender, "guest_profile", None)
        full = (getattr(profile, "full_name", "") or "").strip()
    return full or message.sender.username


def sender_label(message) -> str:
    """«اپراتور رضا» — the role first, so it is never in doubt."""
    if message.sender_id is None:
        return "سیستم"
    role = ROLE_LABELS.get(message.sender.role, "")
    name = sender_name(message)
    return f"{role} {name}".strip()


def message_payload(message) -> dict:
    """The one shape, shared by REST, SSE and the WebSocket consumer."""
    return {
        "id": message.id,
        "conversation": message.conversation_id,
        "body": message.body,
        "sender": message.sender_id,
        "sender_name": sender_name(message),
        "sender_role": message.sender.role if message.sender_id else None,
        "sender_label": sender_label(message),
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    sender_label = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("id", "conversation", "body", "sender", "sender_name", "sender_role", "sender_label", "created_at")
        read_only_fields = ("id", "conversation", "sender", "sender_name", "sender_role", "sender_label", "created_at")

    def get_sender_name(self, message) -> str:
        return sender_name(message)

    def get_sender_role(self, message) -> str | None:
        return message.sender.role if message.sender_id else None

    def get_sender_label(self, message) -> str:
        return sender_label(message)


class ConversationSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    guest_name = serializers.CharField(source="guest.full_name", read_only=True, default="")
    room_number = serializers.CharField(source="guest.room.number", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    participant_labels = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "kind",
            "title",
            "subject",
            "guest_name",
            "room_number",
            "department",
            "department_name",
            "participant_labels",
            "unread",
            "last_message",
            "last_message_at",
            "is_closed",
            "created_at",
        )
        read_only_fields = fields

    def get_participant_labels(self, conversation) -> list:
        return [
            f"{ROLE_LABELS.get(p.user.role, '')} {p.user.get_full_name() or p.user.username}".strip()
            for p in conversation.participants.all()
        ]

    def get_unread(self, conversation) -> int:
        from .services import unread_count

        user = self.context["request"].user
        return unread_count(conversation, user)

    def get_last_message(self, conversation) -> str:
        last = conversation.messages.order_by("-created_at", "-id").first()
        return last.body[:120] if last else ""


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000, trim_whitespace=True)

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError("پیام خالی است.")
        return value


class StartGuestConversationSerializer(serializers.Serializer):
    department = serializers.IntegerField()


class StartStaffConversationSerializer(serializers.Serializer):
    users = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    subject = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")


class ChatConfigSerializer(serializers.Serializer):
    transport = serializers.CharField()
    websocket_path = serializers.CharField(allow_blank=True)
    poll_seconds = serializers.IntegerField()
