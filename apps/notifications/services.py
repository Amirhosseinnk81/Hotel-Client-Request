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
from .models import SmsMessage

logger = logging.getLogger(__name__)


def _hotel_name():
    return getattr(settings, "SMS_HOTEL_NAME", "هتل")


def _body_for(ticket, event):
    if event == SmsMessage.Event.TICKET_CREATED:
        return (
            f"مهمان گرامی، درخواست «{ticket.title}» شما ثبت شد "
            f"(شمارهٔ پیگیری {ticket.pk}) و به واحد {ticket.department.name} سپرده شد. "
            f"{_hotel_name()}"
        )
    return (
        f"مهمان گرامی، درخواست «{ticket.title}» شما توسط واحد "
        f"{ticket.department.name} انجام شد. {_hotel_name()}"
    )


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
        with transaction.atomic():
            return SmsMessage.objects.create(
                phone=phone,
                body=_body_for(ticket, event),
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
