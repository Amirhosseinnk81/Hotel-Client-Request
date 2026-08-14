from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Guest


class GuestLoginSerializer(serializers.Serializer):
    """
    Guest login by national_id + room number (no password).
    """

    national_id = serializers.CharField()
    room_number = serializers.CharField()

    def validate(self, attrs):
        national_id = attrs["national_id"]
        room_number = attrs["room_number"]

        try:
            guest = Guest.objects.select_related("user", "room").get(
                national_id=national_id,
                room__number=room_number,
            )
        except Guest.DoesNotExist:
            raise serializers.ValidationError(
                "No guest found matching that national ID and room number."
            )

        # Make sure this account is actually a guest account.
        if guest.user.role != guest.user.Role.GUEST:
            raise serializers.ValidationError(
                "This account is not a guest account."
            )

        # Guest can only log in when their room is currently occupied.
        if guest.room.status != guest.room.Status.OCCUPIED:
            raise serializers.ValidationError(
                "The guest's room is not currently occupied."
            )

        attrs["guest"] = guest
        return attrs

    def get_tokens(self):
        guest = self.validated_data["guest"]

        refresh = RefreshToken.for_user(guest.user)
        refresh["role"] = guest.user.role

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": guest.user.role,
        }


class GuestProfileSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(
        source="room.number",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Guest
        fields = [
            "id",
            "full_name",
            "national_id",
            "phone",
            "room_number",
        ]
        read_only_fields = fields