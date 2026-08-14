from django.conf import settings
from django.db import models


class Guest(models.Model):
    """
    Guest-specific profile, linked one-to-one to a User (role=GUEST).

    Authentication is by national_id + the room's number (not a
    password) — see apps.guests.serializers.GuestLoginSerializer.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="guest_profile"
    )
    full_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="guests"
    )

    def __str__(self):
        return f"{self.full_name} ({self.national_id})"
