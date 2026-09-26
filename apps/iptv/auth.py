"""
Who may read the in-room television screens (Stage 3.4).

Two surfaces, because the two halves of an IPTV system can do different
things:

* The **API** (`/api/v1/iptv/rooms/<room>/`) is called by the IPTV
  middleware's own server, which can set headers: it proves itself with
  `X-IPTV-Key`.
* The **page** (`/tv/<room>/`) is opened by the television's browser,
  which cannot set a header. It is protected by where the request comes
  from (`IPTV_ALLOWED_NETWORKS`) and/or a signature the middleware puts
  in the URL once per room (`IPTV_PAGE_SECRET`). When both are
  configured, both must pass.

None of this is a user login: there is no person behind a television,
only a room — which is exactly why the screens carry no personal data.

An unconfigured integration is closed, the same rule as the PMS webhook:
with no key (API), and with neither a network nor a secret (page), every
request is refused rather than left open to the internet.

**Behind a reverse proxy**, `REMOTE_ADDR` is the proxy, so the network
check needs the real client address from the proxy itself (nginx's
`real_ip` module). `X-Forwarded-For` is deliberately not trusted here —
anyone can send that header, which would turn the allowlist into
decoration.
"""

import hashlib
import hmac
from ipaddress import ip_address, ip_network

from django.conf import settings
from rest_framework.permissions import BasePermission


def _equal(a, b):
    return hmac.compare_digest(str(a or ""), str(b or ""))


def allowed_networks():
    """The configured IPTV networks; unparsable entries are ignored."""
    raw = getattr(settings, "IPTV_ALLOWED_NETWORKS", "") or ""
    networks = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            networks.append(ip_network(entry, strict=False))
        except ValueError:
            continue
    return networks


def from_allowed_network(request):
    networks = allowed_networks()
    if not networks:
        return True  # no allowlist configured: this check isn't in use
    try:
        client = ip_address((request.META.get("REMOTE_ADDR") or "").strip())
    except ValueError:
        return False
    return any(client in network for network in networks)


def signature_for(room_number):
    """
    The `?t=` value for one room's TV URL. Provisioned once per set, so
    it deliberately doesn't expire — a television stays in its room.
    """
    secret = getattr(settings, "IPTV_PAGE_SECRET", "")
    if not secret:
        return ""
    return hmac.new(secret.encode(), str(room_number).encode(), hashlib.sha256).hexdigest()


def page_allowed(request, room_number):
    """Whether this request may see the TV page for `room_number`."""
    networks = allowed_networks()
    secret = getattr(settings, "IPTV_PAGE_SECRET", "")
    if not networks and not secret:
        return False  # not configured: closed, not open
    if networks and not from_allowed_network(request):
        return False
    if secret and not _equal(signature_for(room_number), request.GET.get("t")):
        return False
    return True


class IsIptvClient(BasePermission):
    """The shared key (and the network allowlist, when one is set)."""

    message = "Invalid IPTV credentials."

    def has_permission(self, request, view):
        key = getattr(settings, "IPTV_SHARED_KEY", "")
        if not key:
            self.message = "The IPTV integration is not configured (IPTV_SHARED_KEY)."
            return False
        if not _equal(key, request.headers.get("X-IPTV-Key")):
            return False
        if not from_allowed_network(request):
            self.message = "This address is not on the IPTV network."
            return False
        return True
