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

    def save(self, *args, **kwargs):
        """
        Stage 2.7 — auto-log every status change (any -> any, not just
        transitions into MAINTENANCE, since a generic "room status
        history" is more useful than a MAINTENANCE-only one and still
        covers that case). Overriding save() rather than using a signal
        keeps this working uniformly for every write path that already
        calls Room.save() under the hood — the Django Admin change form,
        the list_editable formset (which calls obj.save() per changed
        row, not save_model), and RoomSerializer via the API — without
        needing to track "who changed it" or duplicate this in each
        call site.
        """
        is_new = self.pk is None
        previous_status = None
        if not is_new:
            previous_status = (
                Room.objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )

        super().save(*args, **kwargs)

        if not is_new and previous_status is not None and previous_status != self.status:
            RoomStatusLog.objects.create(
                room=self,
                previous_status=previous_status,
                new_status=self.status,
            )


class RoomStatusLog(models.Model):
    """
    One row per room status change (Stage 2.7), written automatically by
    Room.save(). Read-only from the app's point of view — nothing ever
    updates or deletes a log entry; it's an append-only audit trail.
    """

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )

    previous_status = models.CharField(max_length=20, choices=Room.Status.choices)
    new_status = models.CharField(max_length=20, choices=Room.Status.choices)

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.room.number}: {self.previous_status} → {self.new_status}"

