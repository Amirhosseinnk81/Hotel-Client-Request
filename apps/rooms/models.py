from django.db import models


class Room(models.Model):
    """
    A hotel room. Minimal fields for now — full room management
    (status transitions, floor management, etc.) is fleshed out in
    the dedicated Rooms phase. Built early here only because Guest
    login (Phase 5) authenticates against a room number.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    number = models.CharField(max_length=20, unique=True)
    floor = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return self.number
