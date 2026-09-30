"""
Tests for live chat.

The ones that matter most are the scoping ones: a guest must never reach
another guest's thread and an operator must never reach another
department's. Because a single rule (`services.visible_conversations`)
feeds the REST endpoints, the live stream and the WebSocket consumer,
these tests pin that rule from all three directions.
"""

from datetime import timedelta
from unittest import skipUnless
from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room

from . import delivery, services
from .models import Conversation, Message, Participant
from .serializers import sender_label
from .tickets import issue_ticket, redeem_ticket

User = get_user_model()


def make_guest(national_id, room_number, full_name="مهمان نمونه"):
    room = Room.objects.create(number=room_number, status=Room.Status.OCCUPIED)
    user = User.objects.create_user(
        username=f"guest_{national_id}", password="x", role="GUEST"
    )
    return Guest.objects.create(
        user=user, full_name=full_name, national_id=national_id, room=room
    )


class ChatVisibilityTests(TestCase):
    """The one rule everything else is built on."""

    @classmethod
    def setUpTestData(cls):
        cls.housekeeping = Department.objects.create(name="خانه‌داری", code="HK")
        cls.room_service = Department.objects.create(name="روم سرویس", code="RS")

        cls.guest_a = make_guest("1111111111", "101", "الف")
        cls.guest_b = make_guest("2222222222", "102", "ب")

        cls.hk_operator = User.objects.create_user(
            username="op_hk", password="x", role="OPERATOR", department=cls.housekeeping
        )
        cls.rs_operator = User.objects.create_user(
            username="op_rs", password="x", role="OPERATOR", department=cls.room_service
        )
        cls.admin = User.objects.create_user(username="boss", password="x", role="ADMIN")

        cls.thread_a = services.guest_conversation(cls.guest_a, cls.housekeeping)
        cls.thread_b = services.guest_conversation(cls.guest_b, cls.room_service)

    def test_a_guest_sees_only_their_own_threads(self):
        visible = services.visible_conversations(self.guest_a.user)
        self.assertEqual(list(visible), [self.thread_a])

    def test_an_operator_sees_their_own_departments_guest_threads(self):
        self.assertEqual(
            list(services.visible_conversations(self.hk_operator)), [self.thread_a]
        )
        self.assertEqual(
            list(services.visible_conversations(self.rs_operator)), [self.thread_b]
        )

    def test_an_operator_without_a_department_sees_no_guest_threads(self):
        stray = User.objects.create_user(username="op_none", password="x", role="OPERATOR")
        self.assertEqual(list(services.visible_conversations(stray)), [])

    def test_an_admin_sees_no_guest_support_threads(self):
        """Guest support belongs to the departments, not to management."""
        self.assertEqual(list(services.visible_conversations(self.admin)), [])

    def test_a_staff_thread_is_visible_only_to_the_people_in_it(self):
        thread = services.start_staff_conversation(
            self.hk_operator, [self.admin], subject="هماهنگی شیفت"
        )
        self.assertIn(thread, services.visible_conversations(self.hk_operator))
        self.assertIn(thread, services.visible_conversations(self.admin))
        self.assertNotIn(thread, services.visible_conversations(self.rs_operator))
        self.assertNotIn(thread, services.visible_conversations(self.guest_a.user))


class ConversationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.housekeeping = Department.objects.create(name="خانه‌داری", code="HK")
        cls.guest = make_guest("3333333333", "201")
        cls.operator = User.objects.create_user(
            username="op", password="x", role="OPERATOR", department=cls.housekeeping
        )
        cls.colleague = User.objects.create_user(
            username="op2", password="x", role="OPERATOR", department=cls.housekeeping
        )

    def test_a_guest_asking_the_same_department_twice_gets_one_thread(self):
        first = services.guest_conversation(self.guest, self.housekeeping)
        second = services.guest_conversation(self.guest, self.housekeeping)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_a_closed_thread_is_not_reused(self):
        first = services.guest_conversation(self.guest, self.housekeeping)
        first.is_closed = True
        first.save(update_fields=["is_closed"])

        second = services.guest_conversation(self.guest, self.housekeeping)
        self.assertNotEqual(first.pk, second.pk)

    def test_the_guest_is_a_participant_of_their_own_thread(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        self.assertTrue(
            conversation.participants.filter(user=self.guest.user).exists()
        )

    def test_messaging_the_same_colleague_twice_reuses_the_empty_thread(self):
        first = services.start_staff_conversation(self.operator, [self.colleague])
        found = services.find_staff_conversation(self.operator, [self.colleague])
        self.assertEqual(found, first)

    def test_a_thread_with_a_subject_is_never_silently_reused(self):
        services.start_staff_conversation(self.operator, [self.colleague], subject="نشت آب")
        self.assertIsNone(services.find_staff_conversation(self.operator, [self.colleague]))

    def test_posting_updates_the_threads_sort_key(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        self.assertIsNone(conversation.last_message_at)

        services.post_message(conversation, self.guest.user, "سلام")
        conversation.refresh_from_db()
        self.assertIsNotNone(conversation.last_message_at)

    def test_an_empty_message_is_refused(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        with self.assertRaises(ValueError):
            services.post_message(conversation, self.guest.user, "   ")

    def test_the_sender_is_joined_and_their_own_message_is_never_unread(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(conversation, self.operator, "بله در خدمتم")

        self.assertTrue(conversation.participants.filter(user=self.operator).exists())
        self.assertEqual(services.unread_count(conversation, self.operator), 0)
        self.assertEqual(services.unread_count(conversation, self.guest.user), 1)

    def test_reading_clears_the_unread_count(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(conversation, self.operator, "سلام")
        self.assertEqual(services.unread_count(conversation, self.guest.user), 1)

        services.mark_read(conversation, self.guest.user)
        self.assertEqual(services.unread_count(conversation, self.guest.user), 0)

    def test_someone_who_is_not_in_the_thread_has_nothing_unread(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(conversation, self.guest.user, "سلام")
        self.assertEqual(services.unread_count(conversation, self.colleague), 0)

    def test_a_thread_joined_later_does_not_count_older_messages(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        message = services.post_message(conversation, self.guest.user, "قبل از پیوستن")
        # Windows' clock ticks about every 15ms, so push the old message
        # clearly into the past instead of trusting "now" to differ.
        Message.objects.filter(pk=message.pk).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )

        services.join(conversation, self.colleague)
        self.assertEqual(services.unread_count(conversation, self.colleague), 0)

    def test_the_badge_adds_up_every_thread(self):
        first = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(first, self.guest.user, "یک")
        services.post_message(first, self.guest.user, "دو")
        self.assertEqual(services.total_unread(self.operator), 0)

        services.join(first, self.operator)
        Participant.objects.filter(conversation=first, user=self.operator).update(
            joined_at=timezone.now() - timedelta(minutes=5)
        )
        self.assertEqual(services.total_unread(self.operator), 2)

    def test_a_message_arriving_in_the_same_clock_tick_as_the_join_still_counts(self):
        """
        Windows' clock ticks about every 15ms, so joined_at and a message
        written straight after it can be identical. The join cutoff is
        inclusive for exactly that reason — this pins it.
        """
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        message = services.post_message(conversation, self.operator, "سلام")
        joined = conversation.participants.get(user=self.guest.user)
        Message.objects.filter(pk=message.pk).update(created_at=joined.joined_at)

        self.assertEqual(services.unread_count(conversation, self.guest.user), 1)


class SenderIdentityTests(TestCase):
    """
    The backlog rule in CLAUDE.md: a guest must always be told who they
    are talking to — «اپراتور رضا», never an anonymous bubble.
    """

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="خانه‌داری", code="HK")
        cls.guest = make_guest("4444444444", "301")
        cls.operator = User.objects.create_user(
            username="reza",
            password="x",
            role="OPERATOR",
            department=cls.department,
            first_name="رضا",
        )

    def test_an_operators_message_says_operator_and_their_name(self):
        conversation = services.guest_conversation(self.guest, self.department)
        message = services.post_message(conversation, self.operator, "سلام")
        self.assertEqual(sender_label(message), "اپراتور رضا")

    def test_an_operator_without_a_full_name_falls_back_to_the_username(self):
        nameless = User.objects.create_user(
            username="op_x", password="x", role="OPERATOR", department=self.department
        )
        conversation = services.guest_conversation(self.guest, self.department)
        message = services.post_message(conversation, nameless, "سلام")
        self.assertEqual(sender_label(message), "اپراتور op_x")

    def test_a_message_with_no_sender_is_labelled_as_the_system(self):
        conversation = services.guest_conversation(self.guest, self.department)
        message = Message.objects.create(conversation=conversation, body="گفت‌وگو بسته شد")
        self.assertEqual(sender_label(message), "سیستم")


class ChatAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.housekeeping = Department.objects.create(name="خانه‌داری", code="HK")
        cls.room_service = Department.objects.create(name="روم سرویس", code="RS")
        cls.guest = make_guest("5555555555", "401")
        cls.other_guest = make_guest("6666666666", "402")
        cls.operator = User.objects.create_user(
            username="op", password="x", role="OPERATOR", department=cls.housekeeping
        )
        cls.other_operator = User.objects.create_user(
            username="op_rs", password="x", role="OPERATOR", department=cls.room_service
        )

    def start_url(self):
        return reverse("chat:start")

    def test_a_guest_opens_a_thread_with_a_department(self):
        self.client.force_authenticate(self.guest.user)
        response = self.client.post(
            self.start_url(), {"department": self.housekeeping.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["kind"], "GUEST")
        self.assertEqual(Conversation.objects.count(), 1)

    def test_opening_twice_does_not_make_a_second_thread(self):
        self.client.force_authenticate(self.guest.user)
        for _ in range(2):
            self.client.post(
                self.start_url(), {"department": self.housekeeping.pk}, format="json"
            )
        self.assertEqual(Conversation.objects.count(), 1)

    def test_a_guest_cannot_open_a_thread_with_an_inactive_department(self):
        self.housekeeping.is_active = False
        self.housekeeping.save(update_fields=["is_active"])

        self.client.force_authenticate(self.guest.user)
        response = self.client.post(
            self.start_url(), {"department": self.housekeeping.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_cannot_open_a_thread_with_a_guest_account(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            self.start_url(), {"users": [self.guest.user.pk]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_the_inbox_only_lists_what_the_caller_may_open(self):
        mine = services.guest_conversation(self.guest, self.housekeeping)
        services.guest_conversation(self.other_guest, self.room_service)

        self.client.force_authenticate(self.operator)
        response = self.client.get(reverse("chat:conversations"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [mine.pk])

    def test_a_guest_sending_a_message_is_stored_and_returned(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        self.client.force_authenticate(self.guest.user)
        response = self.client.post(
            reverse("chat:messages", args=[conversation.pk]),
            {"body": "یک حوله لطفاً"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "یک حوله لطفاً")
        self.assertEqual(response.data["sender_label"], "مهمان مهمان نمونه")
        self.assertEqual(conversation.messages.count(), 1)

    def test_an_empty_message_is_a_400_not_a_500(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        self.client.force_authenticate(self.guest.user)
        response = self.client.post(
            reverse("chat:messages", args=[conversation.pk]), {"body": "   "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_another_guests_thread_is_a_404_not_a_403(self):
        """Same reason as the ticket endpoints: don't confirm it exists."""
        theirs = services.guest_conversation(self.other_guest, self.room_service)
        self.client.force_authenticate(self.guest.user)

        response = self.client.get(reverse("chat:messages", args=[theirs.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(
            reverse("chat:messages", args=[theirs.pk]), {"body": "سلام"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_another_departments_thread_is_a_404_for_an_operator(self):
        theirs = services.guest_conversation(self.other_guest, self.room_service)
        self.client.force_authenticate(self.operator)
        response = self.client.get(reverse("chat:messages", args=[theirs.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nobody_can_write_in_a_closed_thread(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        conversation.is_closed = True
        conversation.save(update_fields=["is_closed"])

        self.client.force_authenticate(self.guest.user)
        response = self.client.post(
            reverse("chat:messages", args=[conversation.pk]), {"body": "سلام"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(conversation.messages.count(), 0)

    def test_reading_the_thread_clears_the_unread_count(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(conversation, self.operator, "سلام")

        self.client.force_authenticate(self.guest.user)
        self.client.get(reverse("chat:messages", args=[conversation.pk]))
        self.assertEqual(services.unread_count(conversation, self.guest.user), 0)

    def test_the_read_endpoint_clears_it_too(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(conversation, self.operator, "سلام")

        self.client.force_authenticate(self.guest.user)
        response = self.client.post(reverse("chat:read", args=[conversation.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(services.unread_count(conversation, self.guest.user), 0)

    def test_the_unread_endpoint_answers_for_the_caller_only(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        services.post_message(conversation, self.guest.user, "سلام")

        self.client.force_authenticate(self.other_operator)
        self.assertEqual(self.client.get(reverse("chat:unread")).data["unread"], 0)

    def test_an_anonymous_caller_is_refused_everywhere(self):
        conversation = services.guest_conversation(self.guest, self.housekeeping)
        for url in (
            reverse("chat:conversations"),
            reverse("chat:unread"),
            reverse("chat:config"),
            reverse("chat:messages", args=[conversation.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED
                )


class ChatConfigTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(username="op", password="x", role="OPERATOR")

    def test_the_default_transport_is_the_existing_stream(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get(reverse("chat:config"))
        self.assertEqual(response.data["transport"], delivery.SSE)
        self.assertEqual(response.data["websocket_path"], "")

    @override_settings(CHAT_TRANSPORT="websocket")
    def test_switching_the_setting_tells_the_panel_where_the_socket_is(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get(reverse("chat:config"))
        self.assertEqual(response.data["transport"], delivery.WEBSOCKET)
        self.assertEqual(response.data["websocket_path"], "/ws/chat/")


class SocketTicketTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(username="op", password="x", role="OPERATOR")

    def setUp(self):
        cache.clear()

    def test_a_ticket_works_exactly_once(self):
        ticket, _ = issue_ticket(self.operator)
        self.assertEqual(redeem_ticket(ticket), self.operator.pk)
        self.assertIsNone(redeem_ticket(ticket))

    def test_a_made_up_ticket_is_worth_nothing(self):
        self.assertIsNone(redeem_ticket("not-a-ticket"))
        self.assertIsNone(redeem_ticket(""))
        self.assertIsNone(redeem_ticket(None))

    def test_the_endpoint_hands_out_a_ticket_and_never_the_token(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(reverse("chat:socket-ticket"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(redeem_ticket(response.data["ticket"]), self.operator.pk)
        self.assertGreater(response.data["expires_in"], 0)

    def test_an_anonymous_caller_gets_no_ticket(self):
        response = self.client.post(reverse("chat:socket-ticket"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="خانه‌داری", code="HK")
        cls.guest = make_guest("7777777777", "501")

    def test_on_sse_nothing_is_pushed_and_the_stream_finds_it(self):
        conversation = services.guest_conversation(self.guest, self.department)
        message = services.post_message(conversation, self.guest.user, "سلام")
        self.assertFalse(delivery.publish(message))

    @override_settings(CHAT_TRANSPORT="websocket")
    def test_on_websockets_the_message_goes_to_the_conversations_group(self):
        conversation = services.guest_conversation(self.guest, self.department)
        layer = MagicMock()
        layer.group_send = AsyncMock()
        with patch("channels.layers.get_channel_layer", return_value=layer):
            message = services.post_message(conversation, self.guest.user, "سلام")

        layer.group_send.assert_awaited_once()
        group, event = layer.group_send.await_args.args
        self.assertEqual(group, delivery.group_name(conversation.pk))
        self.assertEqual(event["message"]["id"], message.pk)

    @override_settings(CHAT_TRANSPORT="websocket")
    def test_a_broken_push_never_loses_the_message(self):
        """
        Delivery is best-effort on purpose: the row is already committed
        and the stream is the backstop, so a failing channel layer must
        not turn into a 500 for the person who just typed.
        """
        conversation = services.guest_conversation(self.guest, self.department)
        with patch(
            "channels.layers.get_channel_layer", side_effect=RuntimeError("no layer")
        ):
            with self.assertLogs("apps.chat.delivery", level="ERROR"):
                message = services.post_message(conversation, self.guest.user, "سلام")
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())


# ---------------------------------------------------------------------------
# The WebSocket half — exercised now so switching CHAT_TRANSPORT at
# deployment is a setting change and not a first run in production.
# ---------------------------------------------------------------------------

try:  # pragma: no cover - channels is only needed for this transport
    from channels.testing import WebsocketCommunicator

    CHANNELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHANNELS_AVAILABLE = False


def chat_socket_app():
    """The consumer wired up on its own, without needing the ASGI stack."""
    from channels.routing import URLRouter

    from .routing import websocket_urlpatterns

    return URLRouter(websocket_urlpatterns())


IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@skipUnless(CHANNELS_AVAILABLE, "channels is not installed")
@override_settings(CHAT_TRANSPORT="websocket", CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ChatConsumerTests(TransactionTestCase):
    """
    TransactionTestCase, not TestCase: the consumer talks to the database
    from another thread, which an open test transaction would hide.
    """

    def setUp(self):
        cache.clear()
        self.department = Department.objects.create(name="خانه‌داری", code="HK")
        self.guest = make_guest("8888888888", "601")
        self.operator = User.objects.create_user(
            username="op", password="x", role="OPERATOR", department=self.department
        )
        self.conversation = services.guest_conversation(self.guest, self.department)

    async def connect_as(self, user, conversation_id):
        ticket, _ = await sync_to_async(issue_ticket)(user)
        communicator = WebsocketCommunicator(
            chat_socket_app(), f"/ws/chat/{conversation_id}/?ticket={ticket}"
        )
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_a_ticket_gets_the_right_person_in(self):
        communicator, connected = await self.connect_as(
            self.guest.user, self.conversation.pk
        )
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_no_ticket_is_refused(self):
        communicator = WebsocketCommunicator(
            chat_socket_app(), f"/ws/chat/{self.conversation.pk}/"
        )
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)

    async def test_a_ticket_cannot_be_used_twice(self):
        ticket, _ = await sync_to_async(issue_ticket)(self.guest.user)
        url = f"/ws/chat/{self.conversation.pk}/?ticket={ticket}"

        first = WebsocketCommunicator(chat_socket_app(), url)
        connected, _ = await first.connect()
        self.assertTrue(connected)
        await first.disconnect()

        second = WebsocketCommunicator(chat_socket_app(), url)
        connected, code = await second.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)

    async def test_somebody_elses_thread_is_refused(self):
        other_guest = await sync_to_async(make_guest)("9999999999", "602")
        other = await sync_to_async(services.guest_conversation)(
            other_guest, self.department
        )
        communicator, connected = await self.connect_as(self.guest.user, other.pk)
        self.assertFalse(connected)

    async def test_what_one_side_sends_reaches_the_other(self):
        guest_side, _ = await self.connect_as(self.guest.user, self.conversation.pk)
        operator_side, _ = await self.connect_as(self.operator, self.conversation.pk)

        await guest_side.send_json_to({"body": "یک حوله لطفاً"})
        received = await operator_side.receive_json_from(timeout=5)

        self.assertEqual(received["body"], "یک حوله لطفاً")
        # The identity rule again: the socket payload is the same shape.
        self.assertTrue(received["sender_label"].startswith("مهمان"))

        await guest_side.disconnect()
        await operator_side.disconnect()

    async def test_an_empty_frame_writes_nothing(self):
        communicator, _ = await self.connect_as(self.guest.user, self.conversation.pk)
        await communicator.send_json_to({"body": "   "})
        await communicator.send_to(text_data="not json")
        await communicator.disconnect()

        count = await sync_to_async(
            Message.objects.filter(conversation=self.conversation).count
        )()
        self.assertEqual(count, 0)
