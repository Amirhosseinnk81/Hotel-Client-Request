"""
Stage 3.2 — live operator notifications, as a Server-Sent Events stream.

GET /api/v1/operator/events/ stays open and pushes, for the caller's own
department:

  ticket.created   a new guest ticket landed in the department
  ticket.assigned  a ticket was just assigned to the caller (by the
                   supervisor, or by auto-assignment)
  chat.message     somebody wrote in a conversation the caller is in
  heartbeat        every SSE_HEARTBEAT_SECONDS: the caller's live status
                   (so the panel needs no polling at all) and the resume
                   cursors; also marks the operator as present
  reconnect        the stream is ending after SSE_MAX_SECONDS; reconnect

It replaces the Stage 2.2 polling bell rather than running beside it.

Why SSE and not Django Channels/WebSockets: it's one-way (server to
operator), works over the existing WSGI server with no Redis and no ASGI
switch, and the browser side is a plain fetch() — which, unlike
EventSource, can send the Authorization header, so the access token stays
in memory like everywhere else. Why polling the database inside the
stream: there is a single process and no message broker; a cheap
id-cursor query every SSE_POLL_SECONDS is simple and survives restarts.

Every event carries `cursor` ({ticket, history, chat}): the client passes
them back on reconnect (?after_ticket=&after_history=&after_chat=) so
nothing that happened in between is missed.

Chat rides this stream rather than opening a second one, because every
open stream holds a server thread for SSE_MAX_SECONDS — giving each
operator two would double the cost of the panel being open. Guests get
`guest_event_stream`, which is the same machinery carrying chat only.
"""

import json
import time

from django.conf import settings
from django.db.models import Max

from apps.chat.models import Message as ChatMessage
from apps.chat.serializers import message_payload
from apps.chat.services import visible_conversations
from apps.tickets.models import Ticket, TicketHistory
from apps.tickets.services import active_ticket_count, mark_operator_seen


def _event(name, data):
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _max_id(queryset):
    return queryset.aggregate(top=Max("id"))["top"] or 0


def _new_chat_messages(user, after_chat):
    """
    Messages the caller should see since `after_chat` — anything in a
    conversation they can open, except their own.

    Scoped through chat.services.visible_conversations, the same rule the
    REST endpoints and the WebSocket consumer use, so the stream can't
    become the one place that leaks somebody else's thread.
    """
    return (
        ChatMessage.objects.filter(
            id__gt=after_chat,
            conversation__in=visible_conversations(user).values("pk"),
        )
        .exclude(sender=user)
        .select_related("sender", "conversation")
        .order_by("id")
    )


def operator_event_stream(
    user,
    *,
    after_ticket=None,
    after_history=None,
    after_chat=None,
    poll_seconds=None,
    heartbeat_seconds=None,
    max_seconds=None,
    sleep=time.sleep,
    clock=time.monotonic,
):
    """
    Yield SSE-formatted strings for `user` (an OPERATOR with a department)
    until max_seconds have passed. `sleep` and `clock` are injectable so
    tests can drive it without real waiting.
    """
    poll_seconds = settings.SSE_POLL_SECONDS if poll_seconds is None else poll_seconds
    heartbeat_seconds = settings.SSE_HEARTBEAT_SECONDS if heartbeat_seconds is None else heartbeat_seconds
    max_seconds = settings.SSE_MAX_SECONDS if max_seconds is None else max_seconds

    department_id = user.department_id
    # A fresh connection starts from "now"; a reconnect resumes where it left off.
    if after_ticket is None:
        after_ticket = _max_id(Ticket.objects.all())
    if after_history is None:
        after_history = _max_id(TicketHistory.objects.all())
    if after_chat is None:
        after_chat = _max_id(ChatMessage.objects.all())

    def cursor():
        return {"ticket": after_ticket, "history": after_history, "chat": after_chat}

    # Tell the browser how long to wait before reconnecting after a drop.
    yield "retry: 3000\n\n"

    started = clock()
    last_beat = None
    while True:
        new_tickets = (
            Ticket.objects.filter(department_id=department_id, id__gt=after_ticket)
            .select_related("category", "room")
            .order_by("id")
        )
        for ticket in new_tickets:
            after_ticket = ticket.id
            yield _event(
                "ticket.created",
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "priority": ticket.priority,
                    "category_name": ticket.category.name,
                    "room_number": ticket.room.number,
                    "assigned_to": ticket.assigned_to_id,
                    "cursor": cursor(),
                },
            )

        newest_history = _max_id(TicketHistory.objects.filter(id__gt=after_history))
        if newest_history:
            assigned_to_me = (
                TicketHistory.objects.filter(
                    id__gt=after_history,
                    id__lte=newest_history,
                    action=TicketHistory.Action.ASSIGNED,
                    new_value=user.username,
                    ticket__department_id=department_id,
                )
                .select_related("ticket", "user")
                .order_by("id")
            )
            for entry in assigned_to_me:
                after_history = entry.id
                yield _event(
                    "ticket.assigned",
                    {
                        "id": entry.ticket_id,
                        "title": entry.ticket.title,
                        "by": entry.user.username if entry.user_id else None,
                        "cursor": cursor(),
                    },
                )
            # Skip past everything else too, so it isn't scanned again.
            after_history = newest_history

        for message in _new_chat_messages(user, after_chat):
            after_chat = message.id
            yield _event("chat.message", {**message_payload(message), "cursor": cursor()})

        now = clock()
        if last_beat is None or now - last_beat >= heartbeat_seconds:
            last_beat = now
            mark_operator_seen(user)
            active = active_ticket_count(user)
            yield _event(
                "heartbeat",
                {"active_tickets": active, "is_available": active == 0, "cursor": cursor()},
            )

        if now - started >= max_seconds:
            yield _event("reconnect", {"cursor": cursor()})
            return

        sleep(poll_seconds)


def guest_event_stream(
    user,
    *,
    after_chat=None,
    poll_seconds=None,
    heartbeat_seconds=None,
    max_seconds=None,
    sleep=time.sleep,
    clock=time.monotonic,
):
    """
    The guest's half of the live chat: the same cursor-polling machinery,
    carrying chat messages only. A guest has no tickets to be notified
    about beyond their own, and no presence to record.
    """
    poll_seconds = settings.SSE_POLL_SECONDS if poll_seconds is None else poll_seconds
    heartbeat_seconds = settings.SSE_HEARTBEAT_SECONDS if heartbeat_seconds is None else heartbeat_seconds
    max_seconds = settings.SSE_MAX_SECONDS if max_seconds is None else max_seconds

    if after_chat is None:
        after_chat = _max_id(ChatMessage.objects.all())

    def cursor():
        return {"chat": after_chat}

    yield "retry: 3000\n\n"

    started = clock()
    last_beat = None
    while True:
        for message in _new_chat_messages(user, after_chat):
            after_chat = message.id
            yield _event("chat.message", {**message_payload(message), "cursor": cursor()})

        now = clock()
        if last_beat is None or now - last_beat >= heartbeat_seconds:
            last_beat = now
            yield _event("heartbeat", {"cursor": cursor()})

        if now - started >= max_seconds:
            yield _event("reconnect", {"cursor": cursor()})
            return

        sleep(poll_seconds)
