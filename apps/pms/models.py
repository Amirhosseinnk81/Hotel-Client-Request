from django.db import models


class PmsEvent(models.Model):
    """
    Stage 3.3 — one call from (or to) the hotel's PMS, logged whatever the
    outcome. The PMS is a system we don't control: when a room's status
    looks wrong, the first question is always "what did the PMS actually
    send?", and this table is the answer. Nothing here is ever edited by
    the app; failures are re-applied from a copy of the original payload.
    """

    class Source(models.TextChoices):
        WEBHOOK = "WEBHOOK", "Webhook (PMS called us)"
        PULL = "PULL", "Pull (we asked the PMS)"
        SIMULATOR = "SIMULATOR", "Simulator"

    class Status(models.TextChoices):
        PROCESSED = "PROCESSED", "Processed"
        FAILED = "FAILED", "Failed"
        IGNORED = "IGNORED", "Ignored (duplicate)"
        REJECTED = "REJECTED", "Rejected (invalid payload)"

    class Type(models.TextChoices):
        CHECK_IN = "check_in", "Check-in"
        CHECK_OUT = "check_out", "Check-out"
        ROOM_CHANGE = "room_change", "Room change"
        STAY_EXTENDED = "stay_extended", "Stay extended"
        GUEST_UPDATED = "guest_updated", "Guest details updated"

    source = models.CharField(max_length=20, choices=Source.choices)
    event_type = models.CharField(max_length=30, blank=True)
    # The PMS's own id for this event when it sends one; otherwise a hash of
    # the payload. Unique, so a webhook delivered twice is applied once.
    external_id = models.CharField(max_length=120, unique=True)
    payload = models.JSONField(help_text="Exactly what the PMS sent, before any mapping.")
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    error = models.TextField(blank=True)
    room_number = models.CharField(max_length=20, blank=True)
    reservation_id = models.CharField(max_length=120, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [models.Index(fields=["event_type", "received_at"])]

    def __str__(self):
        return f"{self.event_type or 'unknown'} ({self.status}) @ {self.received_at:%Y-%m-%d %H:%M}"


class PmsSyncState(models.Model):
    """
    Where the last pull got to, so `manage.py pull_pms` asks the PMS only
    for what happened since. One row (pk=1); kept in the database rather
    than a file so a restart or a second machine can't lose it.
    """

    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        verbose_name = "PMS sync state"
        verbose_name_plural = "PMS sync state"

    def __str__(self):
        return f"last synced: {self.last_synced_at or 'never'}"

    @classmethod
    def load(cls):
        state, _ = cls.objects.get_or_create(pk=1)
        return state
