"""
How a chat message reaches the other side.

Two transports, one domain. The database is always written first and is
always the truth; this module only decides how the other end finds out
sooner than its next page load:

  sse        (default) nothing to push — the live stream in
             apps/notifications/stream.py already polls by id cursor and
             will pick the message up within SSE_POLL_SECONDS. Works on
             the hotel's current WSGI server with no Redis and no ASGI,
             which is the same reason Stage 3.2 chose SSE over Channels.

  websocket  hand the message to a Channels group so every open socket
             on that conversation gets it immediately. Needs the server
             run as ASGI and a channel layer (Redis in anything but a
             single process) — the user's plan is to switch to this at
             deployment time, so the code is written and tested now and
             turned on with one setting.

Switching is `CHAT_TRANSPORT` in settings; nothing else changes, and the
panel asks the server which one is live (GET /chat/config/) rather than
being built for one of them.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

SSE = "sse"
WEBSOCKET = "websocket"


def transport() -> str:
    return getattr(settings, "CHAT_TRANSPORT", SSE) or SSE


def group_name(conversation_id) -> str:
    return f"chat.{conversation_id}"


def publish(message) -> bool:
    """
    Tell the other side about `message`. Returns whether anything was
    actually pushed — False on SSE, where the stream finds it by itself.

    Never raises: a message that is safely in the database must not be
    undone because a socket was unhappy. The stream is the backstop, so
    a failed push costs at most SSE_POLL_SECONDS of latency.
    """
    if transport() != WEBSOCKET:
        return False

    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        from .serializers import message_payload

        layer = get_channel_layer()
        if layer is None:
            logger.warning("CHAT_TRANSPORT=websocket but no channel layer is configured.")
            return False

        async_to_sync(layer.group_send)(
            group_name(message.conversation_id),
            {"type": "chat.message", "message": message_payload(message)},
        )
        return True
    except Exception:  # noqa: BLE001 — delivery is best-effort by design
        logger.exception("Could not push a chat message over the channel layer.")
        return False
