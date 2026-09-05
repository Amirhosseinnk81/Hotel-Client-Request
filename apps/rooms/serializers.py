from rest_framework import serializers

from .models import Room, RoomStatusLog


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "number", "floor", "status"]
        read_only_fields = ["id"]


class RoomStatusLogSerializer(serializers.ModelSerializer):
    """Stage 2.7 — read-only, entries are only ever written by
    Room.save(); there's no create/update endpoint for this model."""

    class Meta:
        model = RoomStatusLog
        fields = ["id", "room", "previous_status", "new_status", "changed_at"]
        read_only_fields = fields
