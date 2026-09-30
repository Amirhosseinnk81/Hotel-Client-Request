"""Stage 3.2 — the live operator event stream (apps/notifications/stream.py)."""

import json
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Category, Ticket, TicketHistory

from .stream import operator_event_stream


def parse(chunks):
    """SSE text -> [(event, data)] (retry/comment lines skipped)."""
    events = []
    for block in "".join(chunks).split("\n\n"):
        name = data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if name:
            events.append((name, data))
    return events


class FakeTime:
    """Drives the stream's loop: each sleep() advances the clock and runs a hook."""

    def __init__(self, on_sleep=None):
        self.now = 0.0
        self.on_sleep = on_sleep or (lambda tick: None)
        self.ticks = 0

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        self.ticks += 1
        self.on_sleep(self.ticks)


class StreamTestData:
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Housekeeping", code="HK_SSE")
        cls.other_department = Department.objects.create(name="Front desk", code="FD_SSE")
        cls.category = Category.objects.create(name="Towels", code="TOWELS_SSE")
        cls.room = Room.objects.create(number="S1", status=Room.Status.OCCUPIED)
        guest_user = User.objects.create_user(username="sse_guest", role=User.Role.GUEST)
        cls.guest_user = guest_user
        cls.guest = Guest.objects.create(
            user=guest_user, full_name="Guest", national_id="0066655544", room=cls.room
        )
        cls.operator = User.objects.create_user(
            username="sse_op", role=User.Role.OPERATOR, department=cls.department
        )

    def ticket(self, **kwargs):
        defaults = {
            "guest": self.guest,
            "department": self.department,
            "category": self.category,
            "room": self.room,
            "title": "Towels",
            "description": "Two, please.",
        }
        defaults.update(kwargs)
        return Ticket.objects.create(**defaults)

    def run_stream(self, on_sleep=None, max_seconds=10, **kwargs):
        fake = FakeTime(on_sleep)
        chunks = list(
            operator_event_stream(
                self.operator,
                poll_seconds=2,
                heartbeat_seconds=25,
                max_seconds=max_seconds,
                sleep=fake.sleep,
                clock=fake.clock,
                **kwargs,
            )
        )
        return parse(chunks)


class OperatorEventStreamTests(StreamTestData, TestCase):
    def test_pushes_new_tickets_of_the_operators_department_only(self):
        def during(tick):
            if tick == 1:
                self.ticket(title="Mine")
                self.ticket(title="Theirs", department=self.other_department)

        events = self.run_stream(during)

        created = [data["title"] for name, data in events if name == "ticket.created"]
        self.assertEqual(created, ["Mine"])

    def test_tickets_from_before_the_connection_are_not_replayed(self):
        self.ticket(title="Old news")

        events = self.run_stream()

        self.assertNotIn("ticket.created", [name for name, _ in events])

    def test_pushes_tickets_assigned_to_the_operator(self):
        ticket = self.ticket()

        def during(tick):
            if tick == 1:
                TicketHistory.objects.create(
                    ticket=ticket, action=TicketHistory.Action.ASSIGNED, new_value="sse_op"
                )
                TicketHistory.objects.create(
                    ticket=ticket, action=TicketHistory.Action.ASSIGNED, new_value="someone_else"
                )

        events = self.run_stream(during)

        assigned = [data for name, data in events if name == "ticket.assigned"]
        self.assertEqual(len(assigned), 1)
        self.assertEqual(assigned[0]["id"], ticket.id)
        self.assertIsNone(assigned[0]["by"])  # auto-assignment: nobody in particular

    def test_heartbeat_carries_status_and_marks_the_operator_present(self):
        self.ticket(assigned_to=self.operator, status=Ticket.Status.IN_PROGRESS)

        events = self.run_stream(max_seconds=0)

        beat = next(data for name, data in events if name == "heartbeat")
        self.assertEqual(beat["active_tickets"], 1)
        self.assertFalse(beat["is_available"])
        self.operator.refresh_from_db()
        self.assertGreater(self.operator.last_seen_at, timezone.now() - timedelta(seconds=5))

    def test_ends_with_a_reconnect_event_carrying_the_cursor(self):
        events = self.run_stream(max_seconds=4)

        name, data = events[-1]
        self.assertEqual(name, "reconnect")
        self.assertEqual(set(data["cursor"]), {"ticket", "history", "chat"})

    def test_resuming_from_a_cursor_delivers_what_happened_in_between(self):
        # The client was disconnected when this arrived...
        cursor = self.run_stream(max_seconds=0)[-1][1]["cursor"]
        self.ticket(title="Arrived while reconnecting")

        # ...and reconnects with the cursor from its last event.
        events = self.run_stream(max_seconds=0, after_ticket=cursor["ticket"], after_history=cursor["history"])

        self.assertIn(
            "Arrived while reconnecting",
            [data["title"] for name, data in events if name == "ticket.created"],
        )


@override_settings(SSE_MAX_SECONDS=0, SSE_POLL_SECONDS=0)
class OperatorEventStreamViewTests(StreamTestData, APITestCase):
    url = reverse("notifications:operator-events")

    def test_operator_gets_an_event_stream(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(self.url, HTTP_ACCEPT="text/event-stream")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response["Content-Type"].startswith("text/event-stream"))
        self.assertEqual(response["Cache-Control"], "no-cache")
        body = b"".join(response.streaming_content).decode()
        self.assertIn("event: heartbeat", body)
        self.assertIn("event: reconnect", body)

    def test_anonymous_guest_and_admin_are_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

        admin = User.objects.create_user(username="sse_admin", role=User.Role.ADMIN)
        for user in (self.guest_user, admin):
            self.client.force_authenticate(user)
            with self.subTest(user=user.username):
                response = self.client.get(self.url, HTTP_ACCEPT="text/event-stream")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
