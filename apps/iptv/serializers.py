"""
The television's view of a room. Read-only throughout — the IPTV screen
never writes anything, so `read_only_fields = fields` is right here.

What is deliberately absent is as important as what is present: no
national ID, no phone number, not even the guest's name, and no staff
names. A television is a screen in a room, not an account, and anyone
standing in the room sees whatever it shows.
"""

from rest_framework import serializers

from apps.guests.models import HotelInfo
from apps.news.models import NewsItem
from apps.tickets.labels import STATUS_LABELS_FA
from apps.tickets.models import Ticket


class IptvTicketSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()
    category = serializers.CharField(source="category.name", default="")
    department = serializers.CharField(source="department.name", default="")
    estimated_minutes = serializers.IntegerField(source="category.sla_minutes", default=None)

    class Meta:
        model = Ticket
        fields = (
            "id",
            "title",
            "status",
            "status_label",
            "category",
            "department",
            "estimated_minutes",
            "created_at",
        )
        read_only_fields = fields

    def get_status_label(self, ticket) -> str:
        return STATUS_LABELS_FA.get(ticket.status, ticket.status)


class IptvHotelInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelInfo
        fields = ("id", "title", "body", "icon")
        read_only_fields = fields


class IptvNewsSerializer(serializers.ModelSerializer):
    """Only what a screen in a public room should carry."""

    class Meta:
        model = NewsItem
        fields = ("id", "title", "body", "kind", "event_at", "location", "icon")
        read_only_fields = fields


class IptvRoomScreenSerializer(serializers.Serializer):
    room_number = serializers.CharField()
    has_active_stay = serializers.BooleanField()
    requests = IptvTicketSerializer(many=True)
    hotel_info = IptvHotelInfoSerializer(many=True)
    news = IptvNewsSerializer(many=True)
