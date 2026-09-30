"""
What an in-room television shows (Stage 3.4).

One function feeds both surfaces — the read-only API the IPTV middleware
calls, and the `/tv/<room>/` page a television's browser opens — so the
two can't answer differently for the same room.

Read-only by decision: a guest cannot file a request or rate one from
the remote control. What the screen answers is the question people ring
reception for — "where are my towels?" — plus the hotel's own
information.
"""

from apps.guests.models import Guest, HotelInfo
from apps.news.services import guest_news
from apps.rooms.models import Room
from apps.tickets.models import Ticket

OPEN_STATUSES = (Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS)


def current_guest(room_number):
    """
    The guest currently staying in this room, or None.

    Mirrors guest login: the room must be OCCUPIED. After the PMS
    reports a check-out the room is freed and `room` is cleared, so the
    television stops showing the previous guest's requests by itself —
    nothing here has to remember to clear anything.
    """
    return (
        Guest.objects.select_related("room")
        .filter(
            room__number=room_number,
            room__status=Room.Status.OCCUPIED,
            checked_out_at__isnull=True,
        )
        .first()
    )


def room_screen(room_number):
    """
    Everything one room's television shows.

    An empty room, an unknown room number and an occupied room with
    nothing pending all answer the same shape: a television in an empty
    room should show the hotel's information rather than an error, and
    answering identically means the screen can't be used to work out
    which rooms exist or which are sold.
    """
    guest = current_guest(room_number)
    tickets = (
        Ticket.objects.select_related("category", "department")
        .filter(guest=guest, status__in=OPEN_STATUSES)
        .order_by("-created_at")
        if guest is not None
        else Ticket.objects.none()
    )

    return {
        "room_number": str(room_number),
        "has_active_stay": guest is not None,
        "requests": tickets,
        "hotel_info": HotelInfo.objects.filter(is_active=True),
        # Straight from apps/news, through the same helper the guest
        # portal uses — so tonight's event is never on the portal and
        # missing from the television, or still up on one after the
        # publish window closed. Guest-audience only; a staff briefing
        # must not reach a room.
        "news": guest_news(),
    }
