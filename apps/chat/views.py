"""
Chat over HTTP. Sending and reading are ordinary REST calls; only the
*arrival* of someone else's message is live, and that goes through the
stream (or the socket) — see delivery.py.

Everything is scoped through `services.visible_conversations`, so a
guest can only ever reach their own thread and an operator only their
own department's, whichever endpoint they call.
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.departments.models import Department
from apps.guests.models import Guest

from . import delivery, services
from .models import Conversation
from .serializers import (
    ChatConfigSerializer,
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartGuestConversationSerializer,
    StartStaffConversationSerializer,
)
from .tickets import issue_ticket


class ConversationListView(generics.ListAPIView):
    """GET /chat/conversations/ — my inbox, newest activity first."""

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        return services.visible_conversations(self.request.user).prefetch_related(
            "participants__user", "messages"
        )


class StartConversationView(APIView):
    """
    POST /chat/conversations/ — open (or reuse) a thread.

    A guest names the department they want; staff name the people. Both
    reuse an existing open thread rather than piling up empty ones.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=StartStaffConversationSerializer,
        responses={200: ConversationSerializer, 201: ConversationSerializer},
    )
    def post(self, request):
        user = request.user

        if user.role == "GUEST":
            payload = StartGuestConversationSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            guest = get_object_or_404(Guest, user=user)
            department = get_object_or_404(
                Department, pk=payload.validated_data["department"], is_active=True
            )
            conversation = services.guest_conversation(guest, department)
        elif services.is_staff_user(user):
            payload = StartStaffConversationSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            others = list(
                get_user_model()
                .objects.filter(pk__in=payload.validated_data["users"], is_active=True)
                .exclude(role="GUEST")
                .exclude(pk=user.pk)
            )
            if not others:
                return Response(
                    {"detail": "دست‌کم یک همکار را انتخاب کنید."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            subject = payload.validated_data.get("subject", "")
            conversation = None
            if not subject:
                conversation = services.find_staff_conversation(user, others)
            if conversation is None:
                conversation = services.start_staff_conversation(user, others, subject)
        else:
            return Response({"detail": "اجازه ندارید."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ConversationSerializer(conversation, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessageListCreateView(generics.ListCreateAPIView):
    """
    GET  /chat/conversations/{id}/messages/ — the thread, oldest first.
    POST the same path — say something.
    """

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_conversation(self):
        return get_object_or_404(
            services.visible_conversations(self.request.user), pk=self.kwargs["pk"]
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none().values("id")
        conversation = self.get_conversation()
        return conversation.messages.select_related("sender").order_by("created_at", "id")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Opening a thread is reading it.
        services.mark_read(self.get_conversation(), request.user)
        return response

    @extend_schema(request=SendMessageSerializer, responses={201: MessageSerializer})
    def create(self, request, *args, **kwargs):
        conversation = self.get_conversation()
        if conversation.is_closed:
            return Response(
                {"detail": "این گفت‌وگو بسته شده است."}, status=status.HTTP_400_BAD_REQUEST
            )

        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        message = services.post_message(conversation, request.user, payload.validated_data["body"])
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class MarkReadView(APIView):
    """POST /chat/conversations/{id}/read/ — clear my unread count."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses=inline_serializer("ChatRead", {"unread": serializers.IntegerField()}),
    )
    def post(self, request, pk):
        conversation = get_object_or_404(services.visible_conversations(request.user), pk=pk)
        services.mark_read(conversation, request.user)
        return Response({"unread": 0})


class UnreadCountView(APIView):
    """GET /chat/unread/ — one number for the badge in the header."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=inline_serializer("ChatUnread", {"unread": serializers.IntegerField()})
    )
    def get(self, request):
        return Response({"unread": services.total_unread(request.user)})


class ChatConfigView(APIView):
    """
    GET /chat/config/ — which transport is live.

    The panel asks instead of being built for one, so moving the hotel
    from SSE to WebSockets is a settings change at deployment and not a
    frontend release.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ChatConfigSerializer)
    def get(self, request):
        from django.conf import settings

        using_ws = delivery.transport() == delivery.WEBSOCKET
        return Response(
            {
                "transport": delivery.transport(),
                "websocket_path": "/ws/chat/" if using_ws else "",
                "poll_seconds": settings.SSE_POLL_SECONDS,
            }
        )


class SocketTicketView(APIView):
    """
    POST /chat/socket-ticket/ — a short-lived, single-use ticket for
    opening the WebSocket.

    A browser cannot put an Authorization header on a WebSocket, and the
    access token must not travel in a URL or a readable cookie (the
    security rules in CLAUDE.md). So the panel spends its token here,
    over an ordinary authenticated request, and connects with a ticket
    that is worth nothing afterwards.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses=inline_serializer(
            "ChatSocketTicket",
            {"ticket": serializers.CharField(), "expires_in": serializers.IntegerField()},
        ),
    )
    def post(self, request):
        ticket, lifetime = issue_ticket(request.user)
        return Response({"ticket": ticket, "expires_in": lifetime})
