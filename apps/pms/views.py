from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import IsPmsClient
from .models import PmsEvent
from .services import apply_event


class PmsWebhookView(APIView):
    """
    POST /api/v1/pms/events/ — the hotel's PMS tells us a guest checked in,
    checked out, changed room, extended their stay, or had their details
    corrected. Authenticated with a shared key (and optionally an HMAC
    signature), never a user's JWT — see apps/pms/auth.py.

    Always answers 200 once the caller is authenticated, even for a payload
    we can't apply: the event is stored with its reason in PmsEvent, and a
    PMS must not be made to retry forever over its own bad data. The body
    says what happened, so the integration can be watched from their side.
    """

    permission_classes = [IsPmsClient]
    authentication_classes = []

    @extend_schema(
        request=inline_serializer(
            "PmsEventPayload",
            {
                "event": serializers.CharField(),
                "event_id": serializers.CharField(required=False),
                "room_number": serializers.CharField(required=False),
                "new_room_number": serializers.CharField(required=False),
                "reservation_id": serializers.CharField(required=False),
                "occurred_at": serializers.DateTimeField(required=False),
                "expected_check_out": serializers.DateField(required=False),
                "guest": inline_serializer(
                    "PmsEventGuest",
                    {
                        "full_name": serializers.CharField(required=False),
                        "national_id": serializers.CharField(required=False),
                        "phone": serializers.CharField(required=False),
                    },
                    required=False,
                ),
            },
        ),
        responses=inline_serializer(
            "PmsEventResult",
            {
                "event_id": serializers.IntegerField(),
                "status": serializers.CharField(),
                "detail": serializers.CharField(),
            },
        ),
        examples=[
            OpenApiExample(
                "Check-in",
                value={
                    "event": "check_in",
                    "event_id": "HRS-99123",
                    "room_number": "305",
                    "reservation_id": "RSV-5512",
                    "occurred_at": "2026-09-24T12:05:00Z",
                    "expected_check_out": "2026-09-27",
                    "guest": {"full_name": "سارا احمدی", "national_id": "0011122233", "phone": "09121112233"},
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        event = apply_event(request.data, source=PmsEvent.Source.WEBHOOK)
        return Response(
            {"event_id": event.pk, "status": event.status, "detail": event.error},
            status=status.HTTP_200_OK,
        )
