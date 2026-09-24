import string

from django.core.exceptions import ValidationError
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
        TICKET_IN_PROGRESS = "TICKET_IN_PROGRESS", "Work started"
        TICKET_RESOLVED = "TICKET_RESOLVED", "Ticket resolved"
        TICKET_CANCELLED = "TICKET_CANCELLED", "Ticket cancelled"

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


class MessageTemplate(models.Model):
    """
    The text of the guest SMS for one ticket event, editable in Django Admin
    (inspired by Odoo Helpdesk's per-stage email/SMS templates). One row per
    event; `is_active` off means "send nothing for this event". With no row
    at all the built-in default text in services.py is used.

    Placeholders, filled in per ticket: {title} {ticket_id} {department}
    {room} {hotel}. Anything else in braces is refused on save, so a typo
    can't reach a guest as a raw "{titel}".
    """

    PLACEHOLDERS = ("title", "ticket_id", "department", "room", "hotel")

    event = models.CharField(max_length=30, choices=SmsMessage.Event.choices, unique=True)
    body = models.TextField(
        help_text="Placeholders: {title} {ticket_id} {department} {room} {hotel}"
    )
    is_active = models.BooleanField(default=True, help_text="Off = no SMS for this event.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event"]

    def __str__(self):
        return self.get_event_display()

    def clean(self):
        used = {name for _, name, _, _ in string.Formatter().parse(self.body) if name is not None}
        unknown = used - set(self.PLACEHOLDERS)
        if unknown:
            raise ValidationError(
                {"body": f"Unknown placeholder(s): {', '.join(sorted(unknown))}. "
                         f"Allowed: {', '.join(self.PLACEHOLDERS)}."}
            )

    def render(self, values):
        return self.body.format_map(values)
