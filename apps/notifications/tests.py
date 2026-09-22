from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Category, Ticket

from .backends import BaseSmsBackend, SmsSendError
from .models import SmsMessage
from .services import queue_ticket_sms, send_pending_sms


class FlakySmsBackend(BaseSmsBackend):
    """Test double: fails while `down` is True, records what it sent."""

    down = False
    sent = []

    def send(self, phone, body):
        if FlakySmsBackend.down:
            raise SmsSendError("provider is down")
        FlakySmsBackend.sent.append((phone, body))
        return f"id-{len(FlakySmsBackend.sent)}"


FLAKY = "apps.notifications.tests.FlakySmsBackend"


class SmsTestData:
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="خانه‌داری", code="HK_SMS")
        cls.category = Category.objects.create(name="Towels", code="TOWELS_SMS")
        cls.room = Room.objects.create(number="701", status=Room.Status.OCCUPIED)
        cls.guest_user = User.objects.create_user(username="sms_guest", role=User.Role.GUEST)
        cls.guest = Guest.objects.create(
            user=cls.guest_user,
            full_name="Sara",
            national_id="0099988877",
            phone="09121234567",
            room=cls.room,
        )
        cls.operator = User.objects.create_user(
            username="sms_op",
            role=User.Role.OPERATOR,
            department=cls.department,
            is_supervisor=True,
        )

    def setUp(self):
        FlakySmsBackend.down = False
        FlakySmsBackend.sent = []

    def make_ticket(self, **kwargs):
        defaults = {
            "guest": self.guest,
            "department": self.department,
            "category": self.category,
            "room": self.room,
            "title": "Extra towels",
            "description": "Two, please.",
        }
        defaults.update(kwargs)
        return Ticket.objects.create(**defaults)


class TicketEventsQueueSmsTests(SmsTestData, APITestCase):
    def test_creating_a_ticket_queues_a_confirmation(self):
        self.client.force_authenticate(self.guest_user)

        response = self.client.post(
            reverse("tickets:guest-ticket-list-create"),
            {
                "title": "Extra towels",
                "description": "Two, please.",
                "department": self.department.pk,
                "category": self.category.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        sms = SmsMessage.objects.get()
        self.assertEqual(sms.event, SmsMessage.Event.TICKET_CREATED)
        self.assertEqual(sms.phone, "09121234567")
        self.assertEqual(sms.status, SmsMessage.Status.PENDING)
        self.assertIn(str(response.data["id"]), sms.body)

    def test_resolving_queues_a_done_message_naming_the_department(self):
        ticket = self.make_ticket(status=Ticket.Status.IN_PROGRESS, assigned_to=self.operator)
        self.client.force_authenticate(self.operator)

        response = self.client.patch(
            reverse("tickets:operator-ticket-detail", kwargs={"pk": ticket.pk}),
            {"status": "RESOLVED", "resolution": "Delivered."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        sms = SmsMessage.objects.get(event=SmsMessage.Event.TICKET_RESOLVED)
        self.assertIn("خانه‌داری", sms.body)
        self.assertEqual(sms.ticket, ticket)

    def test_other_status_changes_send_nothing(self):
        ticket = self.make_ticket()
        self.client.force_authenticate(self.operator)

        self.client.patch(
            reverse("tickets:operator-ticket-detail", kwargs={"pk": ticket.pk}),
            {"status": "IN_PROGRESS"},
            format="json",
        )

        self.assertFalse(SmsMessage.objects.exists())

    def test_the_ticket_is_created_even_if_queueing_the_sms_blows_up(self):
        self.client.force_authenticate(self.guest_user)

        with mock.patch(
            "apps.notifications.models.SmsMessage.objects.create", side_effect=RuntimeError("boom")
        ), self.assertLogs("apps.notifications.services", level="ERROR"):
            response = self.client.post(
                reverse("tickets:guest-ticket-list-create"),
                {
                    "title": "Extra towels",
                    "description": "Two, please.",
                    "department": self.department.pk,
                    "category": self.category.pk,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Ticket.objects.filter(pk=response.data["id"]).exists())


class QueueRulesTests(SmsTestData, TestCase):
    def test_guest_without_phone_is_skipped(self):
        self.guest.phone = ""
        self.guest.save()

        self.assertIsNone(queue_ticket_sms(self.make_ticket(), SmsMessage.Event.TICKET_CREATED))
        self.assertFalse(SmsMessage.objects.exists())

    @override_settings(SMS_ENABLED=False)
    def test_can_be_switched_off(self):
        queue_ticket_sms(self.make_ticket(), SmsMessage.Event.TICKET_CREATED)

        self.assertFalse(SmsMessage.objects.exists())


@override_settings(SMS_BACKEND=FLAKY, SMS_MAX_ATTEMPTS=3)
class SenderTests(SmsTestData, TestCase):
    def queue(self):
        return queue_ticket_sms(self.make_ticket(), SmsMessage.Event.TICKET_CREATED)

    def test_sends_due_messages(self):
        sms = self.queue()

        self.assertEqual(send_pending_sms(), (1, 0, 0))

        sms.refresh_from_db()
        self.assertEqual(sms.status, SmsMessage.Status.SENT)
        self.assertEqual(sms.provider_message_id, "id-1")
        self.assertIsNotNone(sms.sent_at)
        self.assertEqual(len(FlakySmsBackend.sent), 1)

    def test_a_dead_provider_means_retry_later_with_backoff(self):
        sms = self.queue()
        FlakySmsBackend.down = True

        self.assertEqual(send_pending_sms(), (0, 1, 0))

        sms.refresh_from_db()
        self.assertEqual(sms.status, SmsMessage.Status.PENDING)
        self.assertEqual(sms.attempts, 1)
        self.assertIn("provider is down", sms.last_error)
        self.assertGreater(sms.next_attempt_at, timezone.now())
        # Not due yet, so an immediate re-run doesn't hammer the provider.
        self.assertEqual(send_pending_sms(), (0, 0, 0))

    def test_gives_up_after_max_attempts(self):
        sms = self.queue()
        FlakySmsBackend.down = True

        for _ in range(3):
            SmsMessage.objects.filter(pk=sms.pk).update(next_attempt_at=timezone.now())
            send_pending_sms()

        sms.refresh_from_db()
        self.assertEqual(sms.status, SmsMessage.Status.FAILED)
        self.assertEqual(sms.attempts, 3)

    def test_recovers_when_the_provider_comes_back(self):
        sms = self.queue()
        FlakySmsBackend.down = True
        send_pending_sms()

        FlakySmsBackend.down = False
        SmsMessage.objects.filter(pk=sms.pk).update(next_attempt_at=timezone.now() - timedelta(seconds=1))
        send_pending_sms()

        sms.refresh_from_db()
        self.assertEqual(sms.status, SmsMessage.Status.SENT)
        self.assertEqual(sms.last_error, "")

    def test_management_command(self):
        self.queue()
        out = StringIO()

        call_command("send_pending_sms", stdout=out)

        self.assertIn("1 sent", out.getvalue())


class ConsoleBackendTests(SmsTestData, TestCase):
    def test_default_backend_sends_nothing_but_marks_sent(self):
        sms = queue_ticket_sms(self.make_ticket(), SmsMessage.Event.TICKET_CREATED)

        with self.assertLogs("apps.notifications.backends", level="INFO") as logs:
            send_pending_sms()

        sms.refresh_from_db()
        self.assertEqual(sms.status, SmsMessage.Status.SENT)
        self.assertIn("09121234567", logs.output[0])
