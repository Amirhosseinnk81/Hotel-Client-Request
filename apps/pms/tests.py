"""Stage 3.3 — syncing rooms and guests with the hotel's PMS."""

import hashlib
import hmac
import json
from datetime import date, timedelta
from io import StringIO
import tempfile

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Category, Ticket, TicketNote

from .models import PmsEvent, PmsSyncState
from .services import apply_event

KEY = "test-pms-key"


def check_in(room="305", national_id="0011122233", **extra):
    payload = {
        "event": "check_in",
        "event_id": f"HRS-{room}-{national_id}",
        "room_number": room,
        "occurred_at": timezone.now().isoformat(),
        "guest": {"full_name": "سارا احمدی", "national_id": national_id, "phone": "09121112233"},
    }
    payload.update(extra)
    return payload


class PmsTestData:
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Housekeeping", code="HK_PMS")
        cls.category = Category.objects.create(name="Towels", code="TOWELS_PMS")
        cls.room = Room.objects.create(number="305", status=Room.Status.AVAILABLE)

    def guest_ticket(self, guest, **kwargs):
        defaults = {
            "guest": guest,
            "department": self.department,
            "category": self.category,
            "room": guest.room,
            "title": "Towels",
            "description": "Two, please.",
        }
        defaults.update(kwargs)
        return Ticket.objects.create(**defaults)


class CheckInTests(PmsTestData, TestCase):
    def test_check_in_creates_the_guest_and_occupies_the_room(self):
        event = apply_event(check_in(expected_check_out="2026-09-27", reservation_id="RSV-1"))

        self.assertEqual(event.status, PmsEvent.Status.PROCESSED)
        guest = Guest.objects.get(national_id="0011122233")
        self.assertEqual(guest.full_name, "سارا احمدی")
        self.assertEqual(guest.room, self.room)
        self.assertEqual(guest.reservation_id, "RSV-1")
        self.assertEqual(guest.expected_check_out, date(2026, 9, 27))
        self.assertIsNotNone(guest.checked_in_at)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)
        # The account can't be used to log in with a password.
        self.assertFalse(guest.user.has_usable_password())
        self.assertEqual(guest.user.role, User.Role.GUEST)

    def test_a_returning_guest_reuses_their_record(self):
        apply_event(check_in())
        apply_event(check_in(room="410", event_id="HRS-2", phone=None))

        self.assertEqual(Guest.objects.filter(national_id="0011122233").count(), 1)
        guest = Guest.objects.get(national_id="0011122233")
        self.assertEqual(guest.room.number, "410")
        self.assertIsNone(guest.checked_out_at)

    def test_a_room_the_hotel_has_never_seen_is_created(self):
        apply_event(check_in(room="909"))

        self.assertEqual(Room.objects.get(number="909").status, Room.Status.OCCUPIED)

    def test_the_same_event_twice_is_applied_once(self):
        first = apply_event(check_in())
        second = apply_event(check_in())

        self.assertEqual(first.status, PmsEvent.Status.PROCESSED)
        self.assertEqual(second.status, PmsEvent.Status.IGNORED)
        self.assertEqual(Guest.objects.count(), 1)

    def test_an_event_that_failed_can_be_applied_again(self):
        # What Django Admin's "apply again" does, and what a PMS retry after
        # a failure should do: only a successful event is treated as done.
        payload = check_in(room="555")
        with self.settings(PMS_FIELD_MAP={"room_number": "nowhere"}):
            failed = apply_event(payload)
        self.assertEqual(failed.status, PmsEvent.Status.FAILED)

        retried = apply_event(payload)

        self.assertEqual(retried.status, PmsEvent.Status.PROCESSED)
        self.assertTrue(Guest.objects.filter(national_id="0011122233").exists())
        # A third delivery now that it worked is a duplicate again.
        self.assertEqual(apply_event(payload).status, PmsEvent.Status.IGNORED)

    def test_a_check_in_without_a_national_id_is_recorded_as_failed(self):
        payload = check_in()
        payload["guest"].pop("national_id")

        event = apply_event(payload)

        self.assertEqual(event.status, PmsEvent.Status.FAILED)
        self.assertIn("national ID", event.error)
        self.assertFalse(Guest.objects.exists())

    def test_an_unknown_event_type_is_rejected_not_crashed(self):
        event = apply_event({"event": "fire_alarm", "event_id": "X1"})

        self.assertEqual(event.status, PmsEvent.Status.REJECTED)
        self.assertIn("Unknown event type", event.error)

    @override_settings(
        PMS_FIELD_MAP={"room_number": "RoomNo", "national_id": "Guest.NationalCode", "event": "EventName"},
        PMS_EVENT_MAP={"ورود": PmsEvent.Type.CHECK_IN},
    )
    def test_a_pms_with_different_field_names_needs_only_settings(self):
        event = apply_event({"EventName": "ورود", "RoomNo": "305", "Guest": {"NationalCode": "0099988877"}})

        self.assertEqual(event.status, PmsEvent.Status.PROCESSED)
        self.assertTrue(Guest.objects.filter(national_id="0099988877").exists())


class CheckOutTests(PmsTestData, TestCase):
    def setUp(self):
        apply_event(check_in())
        self.guest = Guest.objects.get(national_id="0011122233")

    def test_check_out_frees_the_room_and_ends_access(self):
        open_ticket = self.guest_ticket(self.guest)

        event = apply_event({"event": "check_out", "event_id": "OUT-1", "room_number": "305"})

        self.assertEqual(event.status, PmsEvent.Status.PROCESSED)
        self.guest.refresh_from_db()
        self.assertIsNotNone(self.guest.checked_out_at)
        self.assertIsNone(self.guest.room)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.AVAILABLE)
        # The ticket is left open, with a note for the department.
        open_ticket.refresh_from_db()
        self.assertEqual(open_ticket.status, Ticket.Status.OPEN)
        self.assertIn("تحویل داد", TicketNote.objects.get(ticket=open_ticket).text)
        # And the ticket keeps the room it was raised for.
        self.assertEqual(open_ticket.room, self.room)

    def test_a_departed_guest_cannot_log_in_again(self):
        apply_event({"event": "check_out", "event_id": "OUT-2", "room_number": "305"})

        response = self.client.post(
            reverse("guests:guest-login"),
            {"national_id": "0011122233", "room_number": "305"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_room_out_of_order_stays_out_of_order(self):
        Room.objects.filter(pk=self.room.pk).update(status=Room.Status.MAINTENANCE)

        apply_event({"event": "check_out", "event_id": "OUT-3", "room_number": "305"})

        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.MAINTENANCE)

    def test_check_out_for_nobody_is_recorded_as_failed(self):
        event = apply_event({"event": "check_out", "event_id": "OUT-4", "room_number": "888"})

        self.assertEqual(event.status, PmsEvent.Status.FAILED)


class RoomChangeAndStayTests(PmsTestData, TestCase):
    def setUp(self):
        apply_event(check_in())
        self.guest = Guest.objects.get(national_id="0011122233")

    def test_room_change_moves_the_guest_and_both_rooms_follow(self):
        ticket = self.guest_ticket(self.guest)

        event = apply_event(
            {"event": "room_change", "event_id": "MOVE-1", "room_number": "305", "new_room_number": "410"}
        )

        self.assertEqual(event.status, PmsEvent.Status.PROCESSED)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.room.number, "410")
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.AVAILABLE)
        self.assertEqual(Room.objects.get(number="410").status, Room.Status.OCCUPIED)
        self.assertIn("منتقل شد", TicketNote.objects.get(ticket=ticket).text)

    def test_stay_extension_moves_the_departure_date(self):
        apply_event(
            {
                "event": "stay_extended",
                "event_id": "EXT-1",
                "room_number": "305",
                "expected_check_out": "2026-10-02",
            }
        )

        self.guest.refresh_from_db()
        self.assertEqual(self.guest.expected_check_out, date(2026, 10, 2))

    def test_guest_details_can_be_corrected(self):
        apply_event(
            {
                "event": "guest_updated",
                "event_id": "UPD-1",
                "room_number": "305",
                "guest": {"full_name": "سارا احمدی‌زاده", "phone": "09350000000"},
            }
        )

        self.guest.refresh_from_db()
        self.assertEqual(self.guest.full_name, "سارا احمدی‌زاده")
        self.assertEqual(self.guest.phone, "09350000000")


@override_settings(PMS_SHARED_KEY=KEY, PMS_HMAC_SECRET="")
class WebhookTests(PmsTestData, APITestCase):
    url = reverse("pms:webhook")

    def post(self, payload, **headers):
        return self.client.post(self.url, payload, format="json", **headers)

    def test_a_valid_call_is_applied(self):
        response = self.post(check_in(), HTTP_X_PMS_KEY=KEY)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], PmsEvent.Status.PROCESSED)
        self.assertTrue(Guest.objects.exists())

    def test_without_the_key_nothing_happens(self):
        response = self.post(check_in())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Guest.objects.exists())
        self.assertFalse(PmsEvent.objects.exists())

    def test_a_wrong_key_is_refused(self):
        self.assertEqual(self.post(check_in(), HTTP_X_PMS_KEY="nope").status_code, 403)

    @override_settings(PMS_SHARED_KEY="")
    def test_an_unconfigured_integration_is_closed(self):
        self.assertEqual(self.post(check_in(), HTTP_X_PMS_KEY=KEY).status_code, 403)

    @override_settings(PMS_HMAC_SECRET="s3cret")
    def test_signing_is_enforced_once_a_secret_is_set(self):
        payload = check_in()
        body = json.dumps(payload)
        signature = hmac.new(b"s3cret", body.encode(), hashlib.sha256).hexdigest()

        refused = self.client.post(
            self.url, body, content_type="application/json", HTTP_X_PMS_KEY=KEY, HTTP_X_PMS_SIGNATURE="sha256=bad"
        )
        accepted = self.client.post(
            self.url,
            body,
            content_type="application/json",
            HTTP_X_PMS_KEY=KEY,
            HTTP_X_PMS_SIGNATURE=f"sha256={signature}",
        )

        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)

    def test_bad_data_is_logged_and_answered_200_not_500(self):
        # A PMS must not be pushed into retrying forever over its own payload.
        response = self.post({"event": "check_in", "event_id": "BAD-1"}, HTTP_X_PMS_KEY=KEY)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], PmsEvent.Status.FAILED)
        self.assertEqual(PmsEvent.objects.get().source, PmsEvent.Source.WEBHOOK)


class PullCommandTests(PmsTestData, TestCase):
    def run_pull(self, events, **extra_settings):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump(events, file, ensure_ascii=False)
            path = file.name
        out = StringIO()
        with self.settings(PMS_CLIENT="apps.pms.client.FilePmsClient", PMS_EVENTS_FILE=path, **extra_settings):
            call_command("pull_pms", stdout=out)
        return out.getvalue()

    def test_pull_applies_events_and_moves_the_cursor(self):
        output = self.run_pull([check_in()])

        self.assertIn("PROCESSED", output)
        self.assertTrue(Guest.objects.exists())
        self.assertEqual(PmsEvent.objects.get().source, PmsEvent.Source.PULL)
        self.assertIsNotNone(PmsSyncState.load().last_synced_at)

    def test_running_it_again_does_not_reapply(self):
        self.run_pull([check_in()])
        self.run_pull([check_in()])

        self.assertEqual(PmsEvent.objects.filter(status=PmsEvent.Status.PROCESSED).count(), 1)
        self.assertEqual(Guest.objects.count(), 1)

    def test_a_pms_that_is_down_is_reported_not_crashed(self):
        out = StringIO()
        with self.settings(
            PMS_CLIENT="apps.pms.client.FilePmsClient", PMS_EVENTS_FILE="C:/nope/missing.json"
        ):
            call_command("pull_pms", stdout=out)

        self.assertIn("PMS unavailable", out.getvalue())
        state = PmsSyncState.load()
        self.assertIn("not found", state.last_error)
        self.assertIsNone(state.last_synced_at)


class SimulatorTests(PmsTestData, TestCase):
    def test_the_simulator_stands_in_for_the_pms(self):
        out = StringIO()

        call_command(
            "simulate_pms", "check_in", "--room", "305", "--national-id", "0044455566", "--name", "علی", stdout=out
        )

        self.assertIn(PmsEvent.Status.PROCESSED, out.getvalue())
        self.assertTrue(Guest.objects.filter(national_id="0044455566").exists())
        self.assertEqual(PmsEvent.objects.get().source, PmsEvent.Source.SIMULATOR)

    def test_a_failing_simulation_exits_with_an_error(self):
        with self.assertRaises(CommandError):
            call_command("simulate_pms", "check_out", "--room", "999", stdout=StringIO())


class PurgeCommandTests(PmsTestData, TestCase):
    def departed_guest(self, days_ago):
        apply_event(check_in())
        guest = Guest.objects.get(national_id="0011122233")
        Guest.objects.filter(pk=guest.pk).update(checked_out_at=timezone.now() - timedelta(days=days_ago))
        return guest

    def test_it_lists_but_changes_nothing_without_confirm(self):
        guest = self.departed_guest(400)
        out = StringIO()

        call_command("purge_departed_guests", "--days", "365", stdout=out)

        self.assertIn("Nothing changed", out.getvalue())
        guest.refresh_from_db()
        self.assertEqual(guest.national_id, "0011122233")

    def test_with_confirm_it_anonymises_but_keeps_the_tickets(self):
        guest = self.departed_guest(400)
        ticket = self.guest_ticket(guest, room=self.room)

        call_command("purge_departed_guests", "--days", "365", "--confirm", stdout=StringIO())

        guest.refresh_from_db()
        self.assertEqual(guest.full_name, "مهمان پیشین")
        self.assertTrue(guest.national_id.startswith("erased-"))
        self.assertFalse(guest.user.is_active)
        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    def test_a_guest_still_staying_is_never_touched(self):
        apply_event(check_in(national_id="0055566677", room="410"))

        call_command("purge_departed_guests", "--days", "0", "--confirm", stdout=StringIO())

        self.assertTrue(Guest.objects.filter(national_id="0055566677").exists())
