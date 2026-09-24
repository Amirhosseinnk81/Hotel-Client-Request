"""
Stage 3.1 — guest SMS: queue on ticket events, send later.

queue_ticket_sms()  called by the ticket views; only writes an outbox row.
send_pending_sms()  run by `manage.py send_pending_sms` (Task Scheduler);
                    talks to the provider, retries with backoff.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .backends import SmsSendError, get_backend
from .models import MessageTemplate, SmsMessage

logger = logging.getLogger(__name__)


def _hotel_name():
    return getattr(settings, "SMS_HOTEL_NAME", "هتل")


# Used when an event has no MessageTemplate row (e.g. a fresh database).
# Migration 0003 copies these into editable templates.
DEFAULT_BODIES = {
    SmsMessage.Event.TICKET_CREATED: (
        "مهمان گرامی، درخواست «{title}» شما ثبت شد (شمارهٔ پیگیری {ticket_id}) "
        "و به واحد {department} سپرده شد. {hotel}"
    ),
    SmsMessage.Event.TICKET_IN_PROGRESS: (
        "مهمان گرامی، همکار ما در واحد {department} رسیدگی به درخواست «{title}» را شروع کرد. {hotel}"
    ),
    SmsMessage.Event.TICKET_RESOLVED: (
        "مهمان گرامی، درخواست «{title}» شما توسط واحد {department} انجام شد. {hotel}"
    ),
    SmsMessage.Event.TICKET_CANCELLED: (
        "مهمان گرامی، درخواست «{title}» (شمارهٔ {ticket_id}) لغو شد. "
        "در صورت نیاز با پذیرش تماس بگیرید. {hotel}"
    ),
}


def _body_for(ticket, event):
    """The SMS text for `event`, or None when the admin switched that event off."""
    values = {
        "title": ticket.title,
        "ticket_id": ticket.pk,
        "department": ticket.department.name,
        "room": ticket.room.number if ticket.room_id else "",
        "hotel": _hotel_name(),
    }
    template = MessageTemplate.objects.filter(event=event).first()
    if template is not None:
        return template.render(values) if template.is_active else None
    return DEFAULT_BODIES[event].format_map(values)


def queue_ticket_sms(ticket, event):
    """
    Put the guest's SMS for `event` in the outbox. Never raises: an SMS is
    a courtesy, and no failure here may stop or roll back the ticket
    operation that called it (Stage 3.1). Guests without a phone number, or
    with SMS turned off in settings, are silently skipped.

    Runs inside its own savepoint, so even a database error writing the
    row can't poison a surrounding transaction.
    """
    if not getattr(settings, "SMS_ENABLED", True):
        return None
    try:
        phone = (ticket.guest.phone or "").strip() if ticket.guest_id else ""
        if not phone:
            return None
        body = _body_for(ticket, event)
        if body is None:
            return None
        with transaction.atomic():
            return SmsMessage.objects.create(
                phone=phone,
                body=body,
                event=event,
                ticket=ticket,
                next_attempt_at=timezone.now(),
            )
    except Exception:  # noqa: BLE001 — deliberately swallow; see docstring
        logger.exception("Could not queue %s SMS for ticket %s", event, getattr(ticket, "pk", None))
        return None


def _retry_delay(attempts):
    """1, 2, 4, 8 ... minutes after each failure, capped at an hour."""
    return timedelta(minutes=min(2 ** (attempts - 1), 60))


def send_pending_sms(limit=100):
    """
    Send up to `limit` due messages. Returns (sent, failed_for_now, gave_up).

    Rows are claimed with SELECT ... FOR UPDATE SKIP LOCKED, so two runs
    that overlap (a slow provider, Task Scheduler firing again) never send
    the same SMS twice.
    """
    backend = get_backend()
    max_attempts = getattr(settings, "SMS_MAX_ATTEMPTS", 5)
    sent = retried = gave_up = 0

    with transaction.atomic():
        due = list(
            SmsMessage.objects.select_for_update(skip_locked=True)
            .filter(status=SmsMessage.Status.PENDING, next_attempt_at__lte=timezone.now())
            .order_by("next_attempt_at")[:limit]
        )
        for message in due:
            message.attempts += 1
            try:
                message.provider_message_id = backend.send(message.phone, message.body) or ""
            except SmsSendError as exc:
                message.last_error = str(exc)[:1000]
                if message.attempts >= max_attempts:
                    message.status = SmsMessage.Status.FAILED
                    gave_up += 1
                else:
                    message.next_attempt_at = timezone.now() + _retry_delay(message.attempts)
                    retried += 1
            else:
                message.status = SmsMessage.Status.SENT
                message.sent_at = timezone.now()
                message.last_error = ""
                sent += 1
            message.save()

    return sent, retried, gave_up
