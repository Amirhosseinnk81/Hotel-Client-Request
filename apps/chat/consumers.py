"""
The WebSocket half — written and tested now, switched on at deployment.

Today `CHAT_TRANSPORT` is "sse" and none of this runs: the server is
WSGI, and the live stream carries chat messages like it carries ticket
events. When the hotel's server moves to ASGI, setting
CHAT_TRANSPORT=websocket turns this on and the panel follows, because it
asks /chat/config/ which transport is live.

What switching it on needs, in one place so it isn't rediscovered later:

  1. `pip install channels channels_redis` (channels is already in
     requirements; the Redis layer is deployment's to add),
  2. CHAT_TRANSPORT=websocket in .env — that alone adds "channels" to
     INSTALLED_APPS and points ASGI_APPLICATION here,
  3. run the server as ASGI (daphne/uvicorn) instead of the current
     WSGI process,
  4. a channel layer: InMemory works only in a single process, so
     anything with more than one worker needs Redis.

Authentication is the ticket from tickets.py, not a token in the URL.
"""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from . import services
from .serializers import message_payload
from .tickets import redeem_ticket


@database_sync_to_async
def _resolve(ticket, conversation_id):
    """The user behind the ticket, and their conversation — or (None, None)."""
    from django.contrib.auth import get_user_model

    user_id = redeem_ticket(ticket)
    if user_id is None:
        return None, None

    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return None, None

    # The same visibility rule as every other surface, so a socket can
    # never reach a thread the REST endpoints would refuse.
    conversation = services.visible_conversations(user).filter(pk=conversation_id).first()
    if conversation is None:
        return user, None
    return user, conversation


@database_sync_to_async
def _post(conversation, user, body):
    return message_payload(services.post_message(conversation, user, body))


@database_sync_to_async
def _mark_read(conversation, user):
    services.mark_read(conversation, user)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    /ws/chat/<conversation_id>/?ticket=…

    One socket per open conversation. Everything it receives is written
    through the same `services.post_message` the REST endpoint uses, so
    the two paths cannot diverge in what they store or who they let in.
    """

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        ticket = _query_param(self.scope.get("query_string", b""), "ticket")

        self.user, self.conversation = await _resolve(ticket, self.conversation_id)
        if self.user is None:
            await self.close(code=4401)  # unauthenticated
            return
        if self.conversation is None:
            await self.close(code=4403)  # not yours
            return

        from .delivery import group_name

        self.group = group_name(self.conversation_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await _mark_read(self.conversation, self.user)

    async def disconnect(self, code):
        group = getattr(self, "group", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            body = (json.loads(text_data or "{}") or {}).get("body", "")
        except json.JSONDecodeError:
            return
        if not str(body).strip():
            return
        # post_message publishes to the group, which sends it back to us
        # too — so the sender sees exactly what everyone else sees.
        await _post(self.conversation, self.user, body)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"], ensure_ascii=False))


def _query_param(query_string: bytes, name: str) -> str:
    from urllib.parse import parse_qs

    values = parse_qs(query_string.decode())
    return (values.get(name) or [""])[0]
