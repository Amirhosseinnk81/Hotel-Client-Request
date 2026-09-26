"""
Stage 3.3 — keeping rooms and guests in step with the hotel's PMS (Harris).

One path in, two ways to reach it:
  - the PMS calls POST /api/v1/pms/events/ (webhook), or
  - `manage.py pull_pms` asks the PMS for what changed (polling).

Both end in apply_event(), which logs every call in PmsEvent whatever the
outcome — the PMS is a system we don't control, so "what did it actually
send?" has to be answerable afterwards.

The payload is normalised through settings.PMS_FIELD_MAP (dotted paths into
the PMS's JSON) and settings.PMS_EVENT_MAP (their event names to ours), so
adapting to Harris's real field names is a settings change, not a code
change. What the hotel has to get from Harris: the endpoint, the credential,
and one real sample payload per event.
"""

import hashlib
import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Ticket, TicketNote

from .models import PmsEvent

logger = logging.getLogger(__name__)

# Our canonical field -> dotted path in the PMS payload. Overridable in
# settings for a PMS that names things differently.
DEFAULT_FIELD_MAP = {
    "event": "event",
    "event_id": "event_id",
    "occurred_at": "occurred_at",
    "room_number": "room_number",
    "new_room_number": "new_room_number",
    "reservation_id": "reservation_id",
    "full_name": "guest.full_name",
    "national_id": "guest.national_id",
    "phone": "guest.phone",
    "expected_check_out": "expected_check_out",
}

# Their event names -> ours. Keys are compared lower-cased.
DEFAULT_EVENT_MAP = {
    "check_in": PmsEvent.Type.CHECK_IN,
    "checkin": PmsEvent.Type.CHECK_IN,
    "check_out": PmsEvent.Type.CHECK_OUT,
    "checkout": PmsEvent.Type.CHECK_OUT,
    "room_change": PmsEvent.Type.ROOM_CHANGE,
    "room_move": PmsEvent.Type.ROOM_CHANGE,
    "stay_extended": PmsEvent.Type.STAY_EXTENDED,
    "extend_stay": PmsEvent.Type.STAY_EXTENDED,
    "guest_updated": PmsEvent.Type.GUEST_UPDATED,
}


class PmsEventError(Exception):
    """The payload reached us but can't be applied; the message says why."""


def _setting(name, default):
    return getattr(settings, name, default)


def _dig(payload, path):
    """Read a dotted path out of nested dicts; missing -> None."""
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def normalise(payload):
    """The PMS's JSON as our canonical dict (see DEFAULT_FIELD_MAP)."""
    field_map = {**DEFAULT_FIELD_MAP, **_setting("PMS_FIELD_MAP", {})}
    data = {field: _dig(payload, path) for field, path in field_map.items()}

    event_map = {**DEFAULT_EVENT_MAP, **_setting("PMS_EVENT_MAP", {})}
    raw_event = str(data.get("event") or "").strip().lower()
    data["event"] = event_map.get(raw_event, raw_event)

    for key in ("room_number", "new_room_number", "reservation_id", "national_id", "full_name", "phone"):
        if data.get(key) is not None:
            data[key] = str(data[key]).strip()
    return data


def external_id_for(payload, data):
    """The PMS's own event id, or a hash of the payload when it sends none."""
    own = data.get("event_id")
    if own:
        return str(own)[:120]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"sha256:{digest[:56]}"


# -- the pieces each handler needs ---------------------------------------------


def _room(number):
    if not number:
        raise PmsEventError("The event has no room number.")
    # The PMS is the source of truth for which rooms exist: a room we have
    # never seen is created rather than dropping the event.
    room, created = Room.objects.get_or_create(number=number)
    if created:
        logger.info("PMS: room %s was unknown here and has been created.", number)
    return room


def _guest_for(data, *, create):
    national_id = data.get("national_id")
    reservation_id = data.get("reservation_id")
    room_number = data.get("room_number")

    guest = None
    if national_id:
        guest = Guest.objects.filter(national_id=national_id).first()
    if guest is None and reservation_id:
        guest = Guest.objects.filter(reservation_id=reservation_id, checked_out_at__isnull=True).first()
    if guest is None and room_number:
        guest = Guest.objects.filter(room__number=room_number, checked_out_at__isnull=True).first()

    if guest is not None or not create:
        return guest

    if not national_id:
        raise PmsEventError("A check-in needs the guest's national ID (or passport number).")
    # Guests authenticate with national_id + room number, never a password
    # (see GuestLoginSerializer), so the account gets an unusable one.
    user = get_user_model().objects.create(
        username=f"guest_{national_id}", role=get_user_model().Role.GUEST
    )
    user.set_unusable_password()
    user.save()
    return Guest(user=user, national_id=national_id, full_name=data.get("full_name") or national_id)


def _free_room(room):
    """A departed guest's room goes back to AVAILABLE — unless it's out of order."""
    if room is not None and room.status == Room.Status.OCCUPIED:
        room.status = Room.Status.AVAILABLE
        room.save(update_fields=["status"])


def _note_open_tickets(guest, text):
    """
    Leave an internal note on the guest's still-open tickets. Deliberately
    does NOT close them: a request can outlive the stay (a forgotten charger,
    a repair the guest already paid for), and closing it silently would lose
    work the department still has to do.
    """
    open_tickets = Ticket.objects.filter(
        guest=guest, status__in=(Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS)
    )
    TicketNote.objects.bulk_create(
        [TicketNote(ticket=ticket, author=None, text=text) for ticket in open_tickets]
    )
    return len(open_tickets)


# -- handlers -------------------------------------------------------------------


def _check_in(data):
    room = _room(data.get("room_number"))
    guest = _guest_for(data, create=True)

    guest.full_name = data.get("full_name") or guest.full_name
    if data.get("phone"):
        guest.phone = data["phone"]
    guest.room = room
    guest.reservation_id = data.get("reservation_id") or ""
    guest.checked_in_at = data.get("occurred_at") or timezone.now()
    guest.checked_out_at = None
    guest.expected_check_out = data.get("expected_check_out")
    guest.save()

    if room.status != Room.Status.OCCUPIED:
        room.status = Room.Status.OCCUPIED
        room.save(update_fields=["status"])
    return f"{guest.full_name} checked in to room {room.number}."


def _check_out(data):
    guest = _guest_for(data, create=False)
    if guest is None:
        raise PmsEventError("No current guest found for this check-out.")

    room = guest.room
    guest.checked_out_at = data.get("occurred_at") or timezone.now()
    # Clearing the room is what ends their access: login needs a matching
    # room number and an OCCUPIED room. Their tickets keep their own room.
    guest.room = None
    guest.save(update_fields=["checked_out_at", "room"])
    _free_room(room)

    noted = _note_open_tickets(guest, "مهمان اتاق را تحویل داد (از سیستم هتلداری). درخواست همچنان باز است.")
    return f"{guest.full_name} checked out; {noted} open ticket(s) noted."


def _room_change(data):
    guest = _guest_for(data, create=False)
    if guest is None:
        raise PmsEventError("No current guest found for this room change.")

    new_room = _room(data.get("new_room_number") or data.get("room_number"))
    old_room = guest.room
    if old_room is not None and old_room.pk == new_room.pk:
        return f"{guest.full_name} is already in room {new_room.number}."

    guest.room = new_room
    guest.save(update_fields=["room"])
    if new_room.status != Room.Status.OCCUPIED:
        new_room.status = Room.Status.OCCUPIED
        new_room.save(update_fields=["status"])
    _free_room(old_room)

    _note_open_tickets(
        guest,
        f"مهمان از اتاق {old_room.number if old_room else '—'} به اتاق {new_room.number} منتقل شد (از سیستم هتلداری).",
    )
    return f"{guest.full_name} moved to room {new_room.number}."


def _stay_extended(data):
    guest = _guest_for(data, create=False)
    if guest is None:
        raise PmsEventError("No current guest found for this stay extension.")
    guest.expected_check_out = data.get("expected_check_out")
    guest.save(update_fields=["expected_check_out"])
    return f"{guest.full_name} now leaves on {guest.expected_check_out}."


def _guest_updated(data):
    guest = _guest_for(data, create=False)
    if guest is None:
        raise PmsEventError("No guest found to update.")
    if data.get("full_name"):
        guest.full_name = data["full_name"]
    if data.get("phone"):
        guest.phone = data["phone"]
    guest.save(update_fields=["full_name", "phone"])
    return f"{guest.full_name} updated."


HANDLERS = {
    PmsEvent.Type.CHECK_IN: _check_in,
    PmsEvent.Type.CHECK_OUT: _check_out,
    PmsEvent.Type.ROOM_CHANGE: _room_change,
    PmsEvent.Type.STAY_EXTENDED: _stay_extended,
    PmsEvent.Type.GUEST_UPDATED: _guest_updated,
}


def apply_event(payload, source=PmsEvent.Source.WEBHOOK):
    """
    Apply one PMS event and log it. Never raises: a malformed or failing
    event is recorded with its reason (the PMS mustn't get a 500 for its
    own bad data, and a failed event can be retried from the log).
    """
    data = normalise(payload if isinstance(payload, dict) else {})
    external_id = external_id_for(payload, data)

    # Every attempt at this PMS event: the first one keeps the id itself,
    # later ones get a suffix, so the log stays append-only and unique.
    attempts = PmsEvent.objects.filter(
        Q(external_id=external_id) | Q(external_id__startswith=f"{external_id}:")
    )
    already_done = attempts.filter(status=PmsEvent.Status.PROCESSED).first()
    if already_done is not None:
        # The same event delivered twice (a PMS retry): logged, not applied.
        return PmsEvent.objects.create(
            source=source,
            event_type=data.get("event") or "",
            external_id=f"{external_id}:dup:{timezone.now().timestamp()}",
            payload=payload,
            status=PmsEvent.Status.IGNORED,
            error=f"Duplicate of event #{already_done.pk}.",
            room_number=data.get("room_number") or "",
            reservation_id=data.get("reservation_id") or "",
            processed_at=timezone.now(),
        )

    # An earlier attempt that failed (or was rejected) is worth trying
    # again — that is what a PMS retry and the admin's "apply again" are
    # for; only a successful one is skipped above.
    tried = attempts.count()
    event = PmsEvent(
        source=source,
        event_type=data.get("event") or "",
        external_id=external_id if not tried else f"{external_id}:retry:{tried}",
        payload=payload,
        room_number=data.get("room_number") or "",
        reservation_id=data.get("reservation_id") or "",
    )

    handler = HANDLERS.get(data.get("event"))
    if handler is None:
        event.status = PmsEvent.Status.REJECTED
        event.error = f"Unknown event type: {data.get('event') or '(none)'}."
        event.processed_at = timezone.now()
        event.save()
        return event

    data = _with_parsed_dates(data)
    try:
        with transaction.atomic():
            event.error = handler(data)
            event.status = PmsEvent.Status.PROCESSED
    except Exception as exc:  # noqa: BLE001 — logged on the event, never raised on
        event.status = PmsEvent.Status.FAILED
        event.error = str(exc)[:2000]
        logger.exception("PMS event failed: %s", data.get("event"))

    event.processed_at = timezone.now()
    event.save()
    return event


def _with_parsed_dates(data):
    occurred = data.get("occurred_at")
    if isinstance(occurred, str):
        parsed = parse_datetime(occurred)
        data["occurred_at"] = timezone.make_aware(parsed) if parsed and timezone.is_naive(parsed) else parsed
    expected = data.get("expected_check_out")
    if isinstance(expected, str):
        data["expected_check_out"] = parse_date(expected[:10])
    return data
