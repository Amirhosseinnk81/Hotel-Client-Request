"""
Stage 3.4 — the in-room television.

Two ways in, one answer (see services.room_screen):

* `GET /api/v1/iptv/rooms/<room>/` for an IPTV middleware that renders
  its own menu, and
* `GET /tv/<room>/` for one that simply opens a URL on the television.

The page is plain server-rendered HTML with no JavaScript and no build
step: hotel set-top boxes run old browsers, and a screen that fails to
render is worse than a plain one. It refreshes itself with a meta tag.
"""

import jdatetime
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.tickets.labels import STATUS_LABELS_FA, fa_digits

from .auth import IsIptvClient, page_allowed
from .serializers import IptvRoomScreenSerializer
from .services import room_screen


class IptvRoomScreenView(APIView):
    """
    What room <room_number>'s television shows: the guest's open
    requests and the hotel's information.

    Authenticated with the `X-IPTV-Key` header, not a user's JWT — see
    apps/iptv/auth.py. An empty, unknown or idle room all answer the
    same shape, so this can't be used to find out which rooms are sold.
    """

    permission_classes = [IsIptvClient]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "iptv"

    @extend_schema(responses=IptvRoomScreenSerializer, operation_id="iptv_room_screen")
    def get(self, request, room_number):
        return Response(IptvRoomScreenSerializer(room_screen(room_number)).data)


def _since(created_at):
    """'۲۰ دقیقه پیش' — short enough to read from across a room."""
    minutes = int((timezone.now() - created_at).total_seconds() // 60)
    if minutes < 1:
        return "همین حالا"
    if minutes < 60:
        return f"{fa_digits(minutes)} دقیقه پیش"
    hours = minutes // 60
    if hours < 24:
        return f"{fa_digits(hours)} ساعت پیش"
    return f"{fa_digits(hours // 24)} روز پیش"


def _event_when(event_at):
    """'امروز ۲۱:۳۰' — a time a guest can act on, not a full date."""
    if event_at is None:
        return ""
    local = timezone.localtime(event_at)
    clock = fa_digits(local.strftime("%H:%M"))
    today = timezone.localdate()
    if local.date() == today:
        return f"امروز {clock}"
    if (local.date() - today).days == 1:
        return f"فردا {clock}"
    return f"{fa_digits(jdatetime.date.fromgregorian(date=local.date()).strftime('%Y/%m/%d'))} {clock}"


class TvRoomPageView(View):
    """
    The page a television opens. Refused rather than shown when the
    IPTV integration isn't configured — see auth.page_allowed.
    """

    def get(self, request, room_number):
        if not page_allowed(request, room_number):
            return HttpResponseForbidden("این صفحه فقط از تلویزیون اتاق در دسترس است.")

        screen = room_screen(room_number)
        requests = [
            {
                "title": ticket.title,
                "status": ticket.status,
                "status_label": STATUS_LABELS_FA.get(ticket.status, ticket.status),
                "category": ticket.category.name if ticket.category_id else "",
                "since": _since(ticket.created_at),
                "estimated": (
                    f"زمان تخمینی: {fa_digits(ticket.category.sla_minutes)} دقیقه"
                    if ticket.category_id and ticket.category.sla_minutes
                    else ""
                ),
            }
            for ticket in screen["requests"]
        ]
        return render(
            request,
            "iptv/room.html",
            {
                "room_number": fa_digits(screen["room_number"]),
                "has_active_stay": screen["has_active_stay"],
                "requests": requests,
                "hotel_info": screen["hotel_info"],
                "news": [
                    {
                        "title": item.title,
                        "body": item.body,
                        "when": _event_when(item.event_at),
                        "location": item.location,
                    }
                    for item in screen["news"]
                ],
                "refresh_seconds": getattr(settings, "IPTV_PAGE_REFRESH_SECONDS", 30),
            },
        )
