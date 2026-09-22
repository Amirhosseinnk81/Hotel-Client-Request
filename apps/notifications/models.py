from django.db import models


class SmsMessage(models.Model):
    """
    Stage 3.1 — one SMS in the outbox.

    Writing a row here is ALL the ticket flow does; the actual sending
    happens later, outside the request, in `send_pending_sms` (Windows Task
    Scheduler, every minute). So a slow or dead SMS provider can never slow
    down, fail, or roll back creating or resolving a ticket — the Stage 3.1
    requirement — and nothing is lost while it is down: the row just waits
    and is retried.

    A queue table in the same PostgreSQL rather than Celery + Redis: no new
    services on the Windows host, and the row is written in the same
    transaction as the ticket, so there's never an SMS for a ticket that
    was rolled back.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    class Event(models.TextChoices):
        TICKET_CREATED = "TICKET_CREATED", "Ticket created"
        TICKET_RESOLVED = "TICKET_RESOLVED", "Ticket resolved"

    phone = models.CharField(max_length=20)
    body = models.TextField()
    event = models.CharField(max_length=30, choices=Event.choices)
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_messages",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(
        help_text="Not retried before this moment (grows after each failure)."
    )
    last_error = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]

    def __str__(self):
        return f"{self.get_event_display()} → {self.phone} ({self.status})"
