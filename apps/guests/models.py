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

    # --- Stay, kept in step with the PMS (Stage 3.3, apps/pms) ------------
    reservation_id = models.CharField(
        max_length=120,
        blank=True,
        help_text="The PMS's reservation number for the current stay, when it sends one.",
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Set when the PMS reports the check-out. The room is freed and "
            "`room` is cleared, which is what blocks the guest from logging "
            "in again; their past tickets are untouched."
        ),
    )
    expected_check_out = models.DateField(
        null=True,
        blank=True,
        help_text="Departure date as the PMS last reported it (moves when a stay is extended).",
    )

    def __str__(self):
        return f"{self.full_name} ({self.national_id})"


class HotelInfo(models.Model):
    """
    A short piece of hotel information for the guest portal's help page —
    Wi-Fi password, breakfast hours, check-out time — so a guest finds the
    answer instead of filing a ticket (inspired by Odoo Helpdesk's help
    center). Managed in Django Admin; shown only to logged-in guests,
    because some of it (the Wi-Fi password) is for guests only.

    Bilingual like the guest portal: the English fields are optional and
    fall back to the Persian ones.
    """

    title = models.CharField(max_length=120)
    body = models.TextField()
    title_en = models.CharField(max_length=120, blank=True)
    body_en = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50,
        default="Info",
        help_text="A lucide-react icon name, e.g. Wifi, Coffee, Clock, Phone.",
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Hotel info"
        verbose_name_plural = "Hotel info"

    def __str__(self):
        return self.title
