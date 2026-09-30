from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.views import APIView

from apps.core.permissions import IsGuest, IsOperatorWithDepartment

from .stream import guest_event_stream, operator_event_stream


class EventStreamRenderer(BaseRenderer):
    """
    Lets a client ask for `Accept: text/event-stream` without DRF answering
    406. The stream itself is a StreamingHttpResponse and bypasses
    renderers; this one only ever renders an error body (401/403) as JSON.
    """

    media_type = "text/event-stream"
    format = "sse"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return JSONRenderer().render(data)


def _cursor_param(request, name):
    value = request.query_params.get(name)
    return int(value) if value and value.isdigit() else None


class OperatorEventStreamView(APIView):
    """
    GET /api/v1/operator/events/ — live notifications for the operator panel
    (Stage 3.2). See apps/notifications/stream.py for the events. Operators
    with a department only; admins have no department and get no stream.
    """

    permission_classes = [IsOperatorWithDepartment]
    renderer_classes = [JSONRenderer, EventStreamRenderer]

    @extend_schema(
        parameters=[
            OpenApiParameter("after_ticket", OpenApiTypes.INT, description="Resume cursor from the last event."),
            OpenApiParameter("after_history", OpenApiTypes.INT, description="Resume cursor from the last event."),
            OpenApiParameter("after_chat", OpenApiTypes.INT, description="Resume cursor from the last event."),
        ],
        responses={(200, "text/event-stream"): OpenApiTypes.STR},
    )
    def get(self, request):
        stream = operator_event_stream(
            request.user,
            after_ticket=_cursor_param(request, "after_ticket"),
            after_history=_cursor_param(request, "after_history"),
            after_chat=_cursor_param(request, "after_chat"),
        )
        return _stream_response(stream)


class GuestEventStreamView(APIView):
    """
    GET /api/v1/guest/events/ — the guest's live chat.

    The same machinery as the operator stream, carrying chat only: a
    guest has nothing else to be told about in real time, and giving
    them the operator stream would hand them their department's tickets.
    """

    permission_classes = [IsGuest]
    renderer_classes = [JSONRenderer, EventStreamRenderer]

    @extend_schema(
        parameters=[
            OpenApiParameter("after_chat", OpenApiTypes.INT, description="Resume cursor from the last event."),
        ],
        responses={(200, "text/event-stream"): OpenApiTypes.STR},
    )
    def get(self, request):
        stream = guest_event_stream(request.user, after_chat=_cursor_param(request, "after_chat"))
        return _stream_response(stream)


def _stream_response(stream):
    response = StreamingHttpResponse(stream, content_type="text/event-stream; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    # Tells nginx (if it ever fronts this) not to buffer the stream.
    response["X-Accel-Buffering"] = "no"
    return response
