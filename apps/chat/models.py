"""
Live chat — guests asking the hotel something, and staff talking to each
other.

The database is the only source of truth. How a message *reaches* the
other side (the SSE stream today, a WebSocket once the hotel's server
moves to ASGI) is a delivery detail that lives in `delivery.py`; nothing
here knows about it. That is deliberate: it is the same shape as the PMS
app, where the transport is a setting and the domain doesn't care.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """
    One thread. Either a guest asking their hotel for something, or a
    group of staff talking — same table, because the messages, the
    unread counting and the live delivery are identical and two tables
    would mean writing all of that twice.
    """

    class Kind(models.TextChoices):
        GUEST = "GUEST", "Guest support"
        STAFF = "STAFF", "Staff to staff"

    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)

    guest = models.ForeignKey(
        "guests.Guest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conversations",
        help_text="The guest on a GUEST thread; empty on a STAFF one.",
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
        help_text=(
            "Which department answers a guest thread — the same scoping as "
            "tickets, so an operator only ever sees their own department's "
            "guests. Optional on a staff thread."
        ),
    )
    subject = models.CharField(max_length=150, blank=True, help_text="Staff threads only.")

    is_closed = models.BooleanField(default=False, db_index=True)
    # Kept on the row rather than computed, because every list of
    # conversations sorts by it and a subquery per row is the classic way
    # to make an inbox slow.
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        if self.kind == self.Kind.GUEST:
            return f"گفت‌وگو با {self.guest}" if self.guest_id else "گفت‌وگوی مهمان"
        return self.subject or f"گفت‌وگوی کارکنان #{self.pk}"

    @property
    def title(self):
        return str(self)


class Participant(models.Model):
    """
    Who is in a thread, and how far they have read.

    The guest's own user row is a participant too, so unread counting is
    one rule for everybody instead of one for guests and one for staff.
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_participations"
    )
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("conversation", "user")

    def __str__(self):
        return f"{self.user} in {self.conversation_id}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
        help_text="Empty means the system wrote it (e.g. «گفت‌وگو بسته شد»).",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"#{self.pk} in {self.conversation_id}"

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            # The inbox sorts by this; keeping it here means every path
            # that creates a message updates it, not just the happy one.
            Conversation.objects.filter(pk=self.conversation_id).update(
                last_message_at=self.created_at or timezone.now()
            )
