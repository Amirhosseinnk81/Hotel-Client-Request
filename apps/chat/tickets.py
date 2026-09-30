"""
Single-use tickets for opening a chat WebSocket.

A WebSocket handshake from a browser can't carry an Authorization
header, and this project's security rules are explicit that the access
token never goes into a URL or a JS-readable cookie. So the panel makes
one ordinary authenticated request for a ticket and connects with that
instead:

  * random, so it can't be guessed;
  * short-lived (CHAT_TICKET_SECONDS, default 30s) — long enough to
    open a socket, useless if it leaks into a log or a proxy;
  * single use — redeeming it deletes it, so a replay finds nothing.

Kept in the cache rather than a table: these live for seconds, and a
table would need sweeping.
"""

import secrets

from django.conf import settings
from django.core.cache import cache

PREFIX = "chat-socket-ticket:"


def lifetime() -> int:
    return int(getattr(settings, "CHAT_TICKET_SECONDS", 30))


def issue_ticket(user):
    ticket = secrets.token_urlsafe(32)
    cache.set(f"{PREFIX}{ticket}", user.pk, timeout=lifetime())
    return ticket, lifetime()


def redeem_ticket(ticket):
    """The user id this ticket was for, or None. Works exactly once."""
    if not ticket:
        return None
    key = f"{PREFIX}{ticket}"
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    return user_id
